"""
Power management and low-end mode behaviors for Step 21.

This module provides:
- Battery status detection
- Automatic Ultra-Lite switching on DC power or low battery
- Process priority management
- I/O priority control
- Performance monitoring and enforcement
"""

import os
import sys
import time
import logging
import psutil
from typing import Optional, Dict, Any, Callable
from enum import Enum
from pathlib import Path

try:
    from PySide6.QtCore import QObject, QTimer, Signal
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QObject = object
    Signal = lambda *args, **kwargs: None
    QTimer = None


class ProcessPriority(Enum):
    """Process priority levels."""
    IDLE = "idle"
    BELOW_NORMAL = "below_normal"
    NORMAL = "normal"
    ABOVE_NORMAL = "above_normal"
    HIGH = "high"


class IOPriority(Enum):
    """I/O priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class PowerSource(Enum):
    """Power source types."""
    AC = "ac"
    DC = "dc"  # Battery
    UNKNOWN = "unknown"


class PowerManager(QObject):
    """Manages power-aware performance optimization and system priorities."""
    
    # Signals for power state changes
    power_source_changed = Signal(str)  # "ac" or "dc"
    battery_level_changed = Signal(int)  # 0-100
    ultra_lite_activated = Signal(bool, str)  # activated, reason
    
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Power monitoring
        self.current_power_source = PowerSource.UNKNOWN
        self.current_battery_level = 100
        self.low_battery_threshold = 20  # Below 20% triggers Ultra-Lite
        
        # Ultra-Lite enforcement tracking
        self.ultra_lite_enforced = False
        self.original_preset = None
        self.ultra_lite_reason = None
        
        # Performance monitoring
        self.performance_timer = None
        self.check_interval = 30000  # 30 seconds
        
        # Initialize power monitoring
        self._setup_power_monitoring()
        self._setup_system_priorities()
    
    def _setup_power_monitoring(self):
        """Setup power source and battery monitoring."""
        if QT_AVAILABLE and QTimer:
            self.performance_timer = QTimer()
            self.performance_timer.timeout.connect(self._check_power_status)
            self.performance_timer.start(self.check_interval)
        
        # Initial power status check
        self._check_power_status()
    
    def _setup_system_priorities(self):
        """Setup initial system process and I/O priorities."""
        try:
            process = psutil.Process()
            
            # Get current performance preset
            performance_config = self.settings._data.get("Performance", {})
            current_preset = performance_config.get("current_preset", "Balanced")
            
            if current_preset == "Ultra-Lite":
                self._apply_ultra_lite_priorities()
            else:
                self._apply_normal_priorities()
                
        except Exception as e:
            self.logger.warning(f"Failed to set initial priorities: {e}")
    
    def _check_power_status(self):
        """Check current power source and battery level."""
        try:
            battery_info = self._get_battery_info()
            
            if battery_info:
                power_source = PowerSource.AC if battery_info['power_plugged'] else PowerSource.DC
                battery_level = battery_info['percent']
                
                # Check for power source changes
                if power_source != self.current_power_source:
                    self.current_power_source = power_source
                    self.power_source_changed.emit(power_source.value)
                    self.logger.info(f"Power source changed to: {power_source.value}")
                
                # Check for battery level changes
                if abs(battery_level - self.current_battery_level) > 1:
                    self.current_battery_level = battery_level
                    self.battery_level_changed.emit(battery_level)
                
                # Auto-switch logic
                self._check_auto_switch_conditions()
                
        except Exception as e:
            self.logger.debug(f"Power status check failed: {e}")
    
    def _get_battery_info(self) -> Optional[Dict[str, Any]]:
        """Get battery information using psutil."""
        try:
            battery = psutil.sensors_battery()
            if battery:
                return {
                    'percent': int(battery.percent),
                    'power_plugged': battery.power_plugged,
                    'secsleft': battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
                }
        except AttributeError:
            # sensors_battery not available on this platform
            pass
        except Exception as e:
            self.logger.debug(f"Battery info unavailable: {e}")
        
        return None
    
    def _check_auto_switch_conditions(self):
        """Check if Ultra-Lite mode should be automatically activated."""
        general_settings = self.settings._data.get("General", {})
        auto_switch = general_settings.get("battery_saver_auto_switch", True)
        
        if not auto_switch:
            return
        
        performance_config = self.settings._data.get("Performance", {})
        current_preset = performance_config.get("current_preset", "Balanced")
        
        should_activate = False
        reason = None
        
        # Check DC power condition
        if self.current_power_source == PowerSource.DC:
            should_activate = True
            reason = "running on battery power"
        
        # Check low battery condition
        elif self.current_battery_level < self.low_battery_threshold:
            should_activate = True
            reason = f"battery level below {self.low_battery_threshold}%"
        
        # Apply or remove Ultra-Lite enforcement
        if should_activate and not self.ultra_lite_enforced:
            self._enforce_ultra_lite(reason)
        elif not should_activate and self.ultra_lite_enforced:
            self._restore_original_preset()
    
    def _enforce_ultra_lite(self, reason: str):
        """Enforce Ultra-Lite mode due to power conditions."""
        performance_config = self.settings._data.get("Performance", {})
        current_preset = performance_config.get("current_preset", "Balanced")
        
        if current_preset != "Ultra-Lite":
            self.original_preset = current_preset
            self.ultra_lite_reason = reason
            self.ultra_lite_enforced = True
            
            # Switch to Ultra-Lite
            self.settings.set("Performance", "current_preset", "Ultra-Lite")
            self.settings.save()
            
            # Apply system priorities
            self._apply_ultra_lite_priorities()
            
            self.ultra_lite_activated.emit(True, reason)
            self.logger.info(f"Ultra-Lite mode activated: {reason}")
    
    def _restore_original_preset(self):
        """Restore original performance preset when power conditions improve."""
        if self.ultra_lite_enforced and self.original_preset:
            self.settings.set("Performance", "current_preset", self.original_preset)
            self.settings.save()
            
            # Restore normal priorities
            self._apply_normal_priorities()
            
            self.ultra_lite_activated.emit(False, "power conditions improved")
            self.logger.info(f"Restored preset: {self.original_preset}")
            
            self.ultra_lite_enforced = False
            self.original_preset = None
            self.ultra_lite_reason = None
    
    def _apply_ultra_lite_priorities(self):
        """Apply low-end system priorities."""
        try:
            process = psutil.Process()
            
            # Set below normal process priority
            if sys.platform.startswith('win'):
                process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            else:
                process.nice(10)  # Lower priority on Unix systems
            
            # Set low I/O priority if available
            try:
                if hasattr(process, 'ionice'):
                    if sys.platform.startswith('win'):
                        process.ionice(psutil.IOPRIO_LOW)
                    else:
                        process.ionice(psutil.IOPRIO_CLASS_IDLE)
            except (AttributeError, OSError):
                self.logger.debug("I/O priority setting not supported")
            
            self.logger.info("Applied Ultra-Lite system priorities")
            
        except Exception as e:
            self.logger.warning(f"Failed to apply Ultra-Lite priorities: {e}")
    
    def _apply_normal_priorities(self):
        """Apply normal system priorities."""
        try:
            process = psutil.Process()
            
            # Set normal process priority
            if sys.platform.startswith('win'):
                process.nice(psutil.NORMAL_PRIORITY_CLASS)
            else:
                process.nice(0)  # Normal priority on Unix systems
            
            # Set normal I/O priority if available
            try:
                if hasattr(process, 'ionice'):
                    if sys.platform.startswith('win'):
                        process.ionice(psutil.IOPRIO_NORMAL)
                    else:
                        process.ionice(psutil.IOPRIO_CLASS_NONE)
            except (AttributeError, OSError):
                self.logger.debug("I/O priority setting not supported")
            
            self.logger.info("Applied normal system priorities")
            
        except Exception as e:
            self.logger.warning(f"Failed to apply normal priorities: {e}")
    
    def get_ultra_lite_config(self) -> Dict[str, Any]:
        """Get comprehensive Ultra-Lite configuration."""
        return {
            # Core Ultra-Lite requirements
            "thread_cap": 2,
            "io_throttle": 1.0,
            "memory_cap_mb": 512,
            "enable_orb_fallback": False,
            "on_demand_thumbs": True,
            "skip_raw_tiff": True,
            "cache_size_cap_mb": 256,
            
            # Enhanced Step 21 requirements
            "thumbnail_decode_size": 128,  # 128-192px decode
            "thumbnail_max_size": 192,
            "phash_threshold": 6,  # Strict threshold (≤6)
            "skip_raw_formats": True,
            "skip_tiff_formats": True,
            "process_priority": ProcessPriority.BELOW_NORMAL.value,
            "io_priority": IOPriority.LOW.value,
            "animations_enabled": False,
            "use_perceptual_hash_only": True,  # pHash only for suspected groups
        }
    
    def is_ultra_lite_enforced(self) -> bool:
        """Check if Ultra-Lite mode is currently enforced by power management."""
        return self.ultra_lite_enforced
    
    def get_enforcement_reason(self) -> Optional[str]:
        """Get the reason Ultra-Lite mode was enforced."""
        return self.ultra_lite_reason
    
    def get_power_status(self) -> Dict[str, Any]:
        """Get current power status information."""
        return {
            "power_source": self.current_power_source.value,
            "battery_level": self.current_battery_level,
            "ultra_lite_enforced": self.ultra_lite_enforced,
            "enforcement_reason": self.ultra_lite_reason,
            "auto_switch_enabled": self.settings.get("General", "battery_saver_auto_switch", True)
        }
    
    def force_ultra_lite(self, enabled: bool, reason: str = "manual override"):
        """Manually force Ultra-Lite mode on or off."""
        if enabled and not self.ultra_lite_enforced:
            self._enforce_ultra_lite(reason)
        elif not enabled and self.ultra_lite_enforced:
            self._restore_original_preset()
    
    def cleanup(self):
        """Cleanup power monitoring resources."""
        if self.performance_timer:
            self.performance_timer.stop()
        
        # Restore normal priorities if Ultra-Lite was enforced
        if self.ultra_lite_enforced:
            self._apply_normal_priorities()


class UltraLiteEnforcer:
    """Enforces Ultra-Lite mode behaviors throughout the application."""
    
    def __init__(self, settings, power_manager: PowerManager):
        self.settings = settings
        self.power_manager = power_manager
        self.logger = logging.getLogger(__name__)
        
        # Ultra-Lite configuration cache
        self._ultra_lite_config = None
        self._config_timestamp = 0
    
    def is_ultra_lite_active(self) -> bool:
        """Check if Ultra-Lite mode is currently active."""
        performance_config = self.settings._data.get("Performance", {})
        current_preset = performance_config.get("current_preset", "Balanced")
        return current_preset == "Ultra-Lite"
    
    def get_effective_config(self) -> Dict[str, Any]:
        """Get effective configuration with Ultra-Lite enforcement."""
        # Cache config for performance
        current_time = time.time()
        if self._ultra_lite_config is None or (current_time - self._config_timestamp) > 60:
            self._ultra_lite_config = self.power_manager.get_ultra_lite_config()
            self._config_timestamp = current_time
        
        if self.is_ultra_lite_active():
            return self._ultra_lite_config.copy()
        else:
            # Return standard configuration
            performance_config = self.settings._data.get("Performance", {})
            return performance_config
    
    def enforce_thread_limits(self, requested_threads: int) -> int:
        """Enforce thread limits for Ultra-Lite mode."""
        if self.is_ultra_lite_active():
            ultra_lite_threads = self.get_effective_config()["thread_cap"]
            if requested_threads > ultra_lite_threads:
                self.logger.info(f"Ultra-Lite: Limiting threads from {requested_threads} to {ultra_lite_threads}")
                return ultra_lite_threads
        
        return requested_threads
    
    def enforce_memory_limits(self, requested_memory_mb: int) -> int:
        """Enforce memory limits for Ultra-Lite mode."""
        if self.is_ultra_lite_active():
            ultra_lite_memory = self.get_effective_config()["memory_cap_mb"]
            if requested_memory_mb > ultra_lite_memory:
                self.logger.info(f"Ultra-Lite: Limiting memory from {requested_memory_mb}MB to {ultra_lite_memory}MB")
                return ultra_lite_memory
        
        return requested_memory_mb
    
    def should_skip_format(self, file_path: Path) -> bool:
        """Check if file format should be skipped in Ultra-Lite mode."""
        if not self.is_ultra_lite_active():
            return False
        
        config = self.get_effective_config()
        if not config.get("skip_raw_tiff", True):
            return False
        
        # Check RAW formats
        raw_extensions = {'.cr2', '.nef', '.arw', '.dng', '.rw2', '.orf', '.pef', '.srw'}
        
        # Check TIFF formats
        tiff_extensions = {'.tif', '.tiff'}
        
        file_ext = file_path.suffix.lower()
        
        should_skip = file_ext in raw_extensions or file_ext in tiff_extensions
        
        if should_skip:
            self.logger.debug(f"Ultra-Lite: Skipping {file_ext} format: {file_path.name}")
        
        return should_skip
    
    def get_thumbnail_decode_size(self) -> int:
        """Get thumbnail decode size for Ultra-Lite mode."""
        if self.is_ultra_lite_active():
            return self.get_effective_config()["thumbnail_decode_size"]
        else:
            # Standard decode size based on preset
            performance_config = self.settings.get_section("Performance")
            current_preset = performance_config.get("current_preset", "Balanced")
            size_map = {"Balanced": 256, "Accurate": 320}
            return size_map.get(current_preset, 256)
    
    def get_phash_threshold(self) -> int:
        """Get perceptual hash threshold for Ultra-Lite mode."""
        if self.is_ultra_lite_active():
            return self.get_effective_config()["phash_threshold"]
        else:
            # Standard threshold from settings
            hashing_config = self.settings._data.get("Hashing", {})
            thresholds = hashing_config.get("near_dupe_thresholds", {})
            return thresholds.get("phash", 8)
    
    def should_use_phash_only(self) -> bool:
        """Check if only perceptual hash should be used (Ultra-Lite optimization)."""
        if self.is_ultra_lite_active():
            return self.get_effective_config().get("use_perceptual_hash_only", True)
        return False
    
    def are_animations_enabled(self) -> bool:
        """Check if animations should be enabled."""
        if self.is_ultra_lite_active():
            return self.get_effective_config().get("animations_enabled", False)
        return True  # Animations enabled by default for other modes