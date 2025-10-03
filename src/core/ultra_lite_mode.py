"""
Step 21 - Low-End Mode Integration

This module integrates all Ultra-Lite mode behaviors and battery saver functionality
into the main app        # Update hashing settings
        hashing_config = self.settings._data.get("Hashing", {})
        hashing_config["near_dupe_thresholds"]["phash"] = config["phash_threshold"]
        hashing_config["use_perceptual_hash"] = True
        hashing_config["enable_orb_fallback"] = config["enable_orb_fallback"]
        
        # Update cache settings
        cache_config = self.settings._data.get("Cache", {})
        cache_config["cache_size_cap_mb"] = config["cache_size_cap_mb"]
        cache_config["on_demand_thumbs"] = config["on_demand_thumbs"]
        
        # Update format settings
        formats_config = self.settings._data.get("Formats", {})
        formats_config["skip_raw_tiff_on_low_end"] = config["skip_raw_tiff"]
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from PySide6.QtCore import QObject, Signal
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QObject = object
    Signal = lambda *args, **kwargs: None

from core.power_manager import PowerManager, UltraLiteEnforcer


class UltraLiteModeManager(QObject):
    """Central manager for Ultra-Lite mode behaviors and enforcement."""
    
    # Signals for mode changes
    mode_changed = Signal(bool, str)  # enabled, reason
    performance_warning = Signal(str)  # warning message
    
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize power management
        self.power_manager = PowerManager(settings)
        self.enforcer = UltraLiteEnforcer(settings, self.power_manager)
        
        # Connect power manager signals
        self.power_manager.ultra_lite_activated.connect(self._on_ultra_lite_activated)
        self.power_manager.power_source_changed.connect(self._on_power_source_changed)
        self.power_manager.battery_level_changed.connect(self._on_battery_level_changed)
        
        self.logger.info("Ultra-Lite Mode Manager initialized")
    
    def _on_ultra_lite_activated(self, activated: bool, reason: str):
        """Handle Ultra-Lite mode activation/deactivation."""
        self.mode_changed.emit(activated, reason)
        
        if activated:
            self.logger.info(f"Ultra-Lite mode activated: {reason}")
            self._log_ultra_lite_enforcement()
        else:
            self.logger.info(f"Ultra-Lite mode deactivated: {reason}")
    
    def _on_power_source_changed(self, power_source: str):
        """Handle power source changes."""
        self.logger.info(f"Power source changed to: {power_source}")
        
        if power_source == "dc":
            self.performance_warning.emit("Running on battery power - Ultra-Lite mode may activate")
        else:
            self.performance_warning.emit("Connected to AC power - full performance available")
    
    def _on_battery_level_changed(self, level: int):
        """Handle battery level changes."""
        if level <= 20:
            self.performance_warning.emit(f"Low battery ({level}%) - Ultra-Lite mode activated")
        elif level <= 30:
            self.performance_warning.emit(f"Battery level: {level}% - consider connecting power")
    
    def _log_ultra_lite_enforcement(self):
        """Log current Ultra-Lite enforcement settings."""
        config = self.enforcer.get_effective_config()
        
        enforcements = [
            f"Thread cap: {config.get('thread_cap', 'default')}",
            f"Memory cap: {config.get('memory_cap_mb', 'default')}MB",
            f"Cache cap: {config.get('cache_size_cap_mb', 'default')}MB",
            f"Thumbnail decode: {config.get('thumbnail_decode_size', 'default')}px",
            f"pHash threshold: ≤{config.get('phash_threshold', 'default')}",
            f"Skip RAW/TIFF: {config.get('skip_raw_tiff', False)}",
            f"pHash only: {config.get('use_perceptual_hash_only', False)}",
            f"Animations: {config.get('animations_enabled', True)}",
        ]
        
        self.logger.info("Ultra-Lite enforcement active:")
        for enforcement in enforcements:
            self.logger.info(f"  • {enforcement}")
    
    def is_ultra_lite_active(self) -> bool:
        """Check if Ultra-Lite mode is currently active."""
        return self.enforcer.is_ultra_lite_active()
    
    def is_enforced_by_power(self) -> bool:
        """Check if Ultra-Lite mode is enforced by power management."""
        return self.power_manager.is_ultra_lite_enforced()
    
    def get_enforcement_reason(self) -> Optional[str]:
        """Get the reason Ultra-Lite mode was enforced."""
        return self.power_manager.get_enforcement_reason()
    
    def get_power_status(self) -> Dict[str, Any]:
        """Get comprehensive power and mode status."""
        power_status = self.power_manager.get_power_status()
        
        return {
            **power_status,
            "ultra_lite_active": self.is_ultra_lite_active(),
            "effective_config": self.enforcer.get_effective_config(),
            "can_override": not self.is_enforced_by_power(),
        }
    
    def force_ultra_lite(self, enabled: bool, reason: str = "manual override"):
        """Manually force Ultra-Lite mode on or off."""
        if self.is_enforced_by_power():
            self.logger.warning("Cannot override Ultra-Lite mode - enforced by power management")
            return False
        
        self.power_manager.force_ultra_lite(enabled, reason)
        return True
    
    def apply_runtime_optimizations(self):
        """Apply runtime optimizations for current mode."""
        if self.is_ultra_lite_active():
            self._apply_ultra_lite_optimizations()
        else:
            self._apply_standard_optimizations()
    
    def _apply_ultra_lite_optimizations(self):
        """Apply Ultra-Lite mode optimizations."""
        config = self.enforcer.get_effective_config()
        
        # Log optimizations being applied
        self.logger.info("Applying Ultra-Lite optimizations:")
        self.logger.info(f"  • Thread limit: {config['thread_cap']}")
        self.logger.info(f"  • Memory limit: {config['memory_cap_mb']}MB")
        self.logger.info(f"  • I/O throttle: {config['io_throttle']} ops/sec")
        self.logger.info(f"  • Thumbnail decode: {config['thumbnail_decode_size']}px")
        self.logger.info(f"  • pHash threshold: ≤{config['phash_threshold']}")
        
        # Update runtime settings
        self.settings.set("General", "thread_cap", config["thread_cap"])
        self.settings.set("General", "io_throttle", config["io_throttle"])
        self.settings.set("General", "animations_enabled", config["animations_enabled"])
        
        # Update hashing settings
        hashing_config = self.settings.get_section("Hashing")
        hashing_config["near_dupe_thresholds"]["phash"] = config["phash_threshold"]
        hashing_config["use_perceptual_hash"] = True
        hashing_config["enable_orb_fallback"] = config["enable_orb_fallback"]
        
        # Update cache settings
        cache_config = self.settings.get_section("Cache")
        cache_config["cache_size_cap_mb"] = config["cache_size_cap_mb"]
        cache_config["on_demand_thumbs"] = config["on_demand_thumbs"]
        
        # Update format settings
        formats_config = self.settings.get_section("Formats")
        formats_config["skip_raw_tiff_on_low_end"] = config["skip_raw_tiff"]
        
        self.settings.save()
    
    def _apply_standard_optimizations(self):
        """Apply standard mode optimizations."""
        self.logger.info("Applying standard performance optimizations")
        
        # Let settings maintain their configured values
        # No forced optimization needed
    
    def cleanup(self):
        """Cleanup resources."""
        self.power_manager.cleanup()
        self.logger.info("Ultra-Lite Mode Manager cleanup complete")


class UltraLiteLogger:
    """Specialized logger for Ultra-Lite mode diagnostics."""
    
    def __init__(self, mode_manager: UltraLiteModeManager):
        self.mode_manager = mode_manager
        self.logger = logging.getLogger("ultra_lite_diagnostics")
    
    def log_mode_change(self, old_preset: str, new_preset: str, reason: str):
        """Log preset mode changes."""
        if new_preset == "Ultra-Lite":
            self.logger.info(f"ULTRA-LITE ACTIVATED: {old_preset} → {new_preset} ({reason})")
            self._log_restrictions()
        else:
            self.logger.info(f"ULTRA-LITE DEACTIVATED: {old_preset} → {new_preset} ({reason})")
    
    def log_format_skip(self, file_path: Path, reason: str):
        """Log when files are skipped due to Ultra-Lite restrictions."""
        self.logger.debug(f"SKIPPED: {file_path.name} - {reason}")
    
    def log_thread_limit(self, requested: int, enforced: int):
        """Log thread limiting enforcement."""
        if requested != enforced:
            self.logger.info(f"THREAD LIMIT: {requested} → {enforced} (Ultra-Lite enforcement)")
    
    def log_memory_limit(self, requested: int, enforced: int):
        """Log memory limiting enforcement."""
        if requested != enforced:
            self.logger.info(f"MEMORY LIMIT: {requested}MB → {enforced}MB (Ultra-Lite enforcement)")
    
    def log_performance_metrics(self, metrics: Dict[str, Any]):
        """Log performance metrics for Ultra-Lite mode."""
        if self.mode_manager.is_ultra_lite_active():
            self.logger.info("ULTRA-LITE METRICS:")
            for key, value in metrics.items():
                self.logger.info(f"  • {key}: {value}")
    
    def _log_restrictions(self):
        """Log active Ultra-Lite restrictions."""
        config = self.mode_manager.enforcer.get_effective_config()
        
        restrictions = [
            "2 threads maximum",
            "512MB memory cap",
            "256MB cache cap",
            "128-192px thumbnail decode",
            "pHash threshold ≤6 (strict)",
            "RAW/TIFF formats skipped",
            "Below-Normal process priority",
            "Low I/O priority",
            "Animations disabled",
            "pHash only for suspected groups"
        ]
        
        self.logger.info("ULTRA-LITE RESTRICTIONS:")
        for restriction in restrictions:
            self.logger.info(f"  • {restriction}")


def create_ultra_lite_manager(settings) -> UltraLiteModeManager:
    """Factory function to create Ultra-Lite mode manager."""
    return UltraLiteModeManager(settings)


def is_ultra_lite_preset_active(settings) -> bool:
    """Quick check if Ultra-Lite preset is currently active."""
    performance_config = settings._data.get("Performance", {})
    current_preset = performance_config.get("current_preset", "Balanced")
    return current_preset == "Ultra-Lite"


def get_ultra_lite_diagnostics(settings) -> Dict[str, Any]:
    """Get comprehensive Ultra-Lite mode diagnostics."""
    manager = create_ultra_lite_manager(settings)
    
    try:
        return {
            "status": manager.get_power_status(),
            "active": manager.is_ultra_lite_active(),
            "enforced": manager.is_enforced_by_power(),
            "reason": manager.get_enforcement_reason(),
            "config": manager.enforcer.get_effective_config(),
            "restrictions": {
                "threads": manager.enforcer.enforce_thread_limits(32),
                "memory": manager.enforcer.enforce_memory_limits(8192),
                "animations": manager.enforcer.are_animations_enabled(),
                "phash_threshold": manager.enforcer.get_phash_threshold(),
                "phash_only": manager.enforcer.should_use_phash_only(),
            }
        }
    finally:
        manager.cleanup()