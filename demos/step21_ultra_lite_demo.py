#!/usr/bin/env python3
"""
Step 21 Interactive Demo: Ultra-Lite Mode and Battery Saver

This demo showcases the Ultra-Lite mode behaviors and battery saver functionality.

Features demonstrated:
- Ultra-Lite preset enforcement
- Battery saver auto-switching
- Runtime performance optimization
- Format skipping and restrictions
- Power-aware diagnostics
"""

import os
import sys
import time
import tempfile
import logging
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                  QHBoxLayout, QLabel, QPushButton, QComboBox,
                                  QTextEdit, QGroupBox, QProgressBar, QCheckBox,
                                  QSlider, QSpinBox, QTabWidget, QGridLayout)
    from PySide6.QtCore import Qt, QTimer, Signal
    from PySide6.QtGui import QFont, QPalette
    QT_AVAILABLE = True
except ImportError:
    print("⚠️  PySide6 not available - running in console mode")
    QT_AVAILABLE = False

from app.settings import Settings
from core.ultra_lite_mode import UltraLiteModeManager, get_ultra_lite_diagnostics
from core.power_manager import PowerManager, UltraLiteEnforcer
from core.thumbs import ThumbnailGenerator


class PowerSimulator:
    """Simulates different power conditions for testing."""
    
    def __init__(self):
        self.current_state = {
            'percent': 85,
            'power_plugged': True,
            'secsleft': None
        }
    
    def set_ac_power(self, level: int = 85):
        """Simulate AC power with specified battery level."""
        self.current_state = {
            'percent': level,
            'power_plugged': True,
            'secsleft': None
        }
    
    def set_dc_power(self, level: int = 60):
        """Simulate DC power (battery) with specified level."""
        self.current_state = {
            'percent': level,
            'power_plugged': False,
            'secsleft': level * 120  # Rough estimate
        }
    
    def set_low_battery(self, level: int = 15):
        """Simulate low battery condition."""
        self.current_state = {
            'percent': level,
            'power_plugged': False,
            'secsleft': level * 60  # Very rough estimate
        }
    
    def get_state(self):
        """Get current simulated power state."""
        return self.current_state.copy()


if QT_AVAILABLE:
    class UltraLiteDemoWindow(QMainWindow):
        """Main demo window for Ultra-Lite mode."""
        
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Step 21 Demo: Ultra-Lite Mode & Battery Saver")
            self.setGeometry(100, 100, 1000, 700)
            
            # Setup demo environment
            self.temp_dir = Path(tempfile.mkdtemp(prefix="step21_demo_"))
            self.settings = Settings(config_dir=self.temp_dir / "config")
            self.power_simulator = PowerSimulator()
            
            # Setup logging
            self.setup_logging()
            
            # Create mode manager
            self.mode_manager = UltraLiteModeManager(self.settings)
            
            # Connect signals
            self.mode_manager.mode_changed.connect(self.on_mode_changed)
            self.mode_manager.performance_warning.connect(self.on_performance_warning)
            
            # Setup UI
            self.setup_ui()
            self.setup_timers()
            
            # Apply dark theme
            self.apply_dark_theme()
            
            # Initial update
            self.update_all_displays()
        
        def setup_logging(self):
            """Setup logging to capture diagnostics."""
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
            # Create log handler for UI display
            self.log_messages = []
        
        def setup_ui(self):
            """Setup the user interface."""
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            layout = QHBoxLayout(central_widget)
            
            # Left panel - Controls
            left_panel = self.create_controls_panel()
            layout.addWidget(left_panel, 1)
            
            # Right panel - Diagnostics
            right_panel = self.create_diagnostics_panel()
            layout.addWidget(right_panel, 2)
        
        def create_controls_panel(self):
            """Create the controls panel."""
            controls_widget = QWidget()
            layout = QVBoxLayout(controls_widget)
            
            # Performance Preset Control
            preset_group = QGroupBox("Performance Preset")
            preset_layout = QVBoxLayout(preset_group)
            
            self.preset_combo = QComboBox()
            self.preset_combo.addItems(["Ultra-Lite", "Balanced", "Accurate"])
            self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
            preset_layout.addWidget(QLabel("Current Preset:"))
            preset_layout.addWidget(self.preset_combo)
            
            layout.addWidget(preset_group)
            
            # Power Simulation Control
            power_group = QGroupBox("Power Simulation")
            power_layout = QVBoxLayout(power_group)
            
            # Power source buttons
            self.ac_power_btn = QPushButton("AC Power (85%)")
            self.ac_power_btn.clicked.connect(lambda: self.simulate_power("ac", 85))
            
            self.dc_power_btn = QPushButton("DC Power (60%)")
            self.dc_power_btn.clicked.connect(lambda: self.simulate_power("dc", 60))
            
            self.low_battery_btn = QPushButton("Low Battery (15%)")
            self.low_battery_btn.clicked.connect(lambda: self.simulate_power("low", 15))
            
            power_layout.addWidget(self.ac_power_btn)
            power_layout.addWidget(self.dc_power_btn)
            power_layout.addWidget(self.low_battery_btn)
            
            # Battery level slider
            power_layout.addWidget(QLabel("Battery Level:"))
            self.battery_slider = QSlider(Qt.Horizontal)
            self.battery_slider.setRange(5, 100)
            self.battery_slider.setValue(85)
            self.battery_slider.valueChanged.connect(self.on_battery_changed)
            power_layout.addWidget(self.battery_slider)
            
            self.battery_label = QLabel("85%")
            power_layout.addWidget(self.battery_label)
            
            layout.addWidget(power_group)
            
            # Settings Control
            settings_group = QGroupBox("Settings")
            settings_layout = QVBoxLayout(settings_group)
            
            self.auto_switch_check = QCheckBox("Battery Saver Auto-Switch")
            self.auto_switch_check.setChecked(True)
            self.auto_switch_check.toggled.connect(self.on_auto_switch_toggled)
            settings_layout.addWidget(self.auto_switch_check)
            
            # Force Ultra-Lite
            self.force_ultra_lite_btn = QPushButton("Force Ultra-Lite Mode")
            self.force_ultra_lite_btn.clicked.connect(self.force_ultra_lite)
            settings_layout.addWidget(self.force_ultra_lite_btn)
            
            layout.addWidget(settings_group)
            
            # Test Operations
            test_group = QGroupBox("Test Operations")
            test_layout = QVBoxLayout(test_group)
            
            self.test_format_btn = QPushButton("Test Format Skipping")
            self.test_format_btn.clicked.connect(self.test_format_skipping)
            
            self.test_thread_btn = QPushButton("Test Thread Limiting")
            self.test_thread_btn.clicked.connect(self.test_thread_limiting)
            
            self.test_diagnostics_btn = QPushButton("Show Full Diagnostics")
            self.test_diagnostics_btn.clicked.connect(self.show_full_diagnostics)
            
            test_layout.addWidget(self.test_format_btn)
            test_layout.addWidget(self.test_thread_btn)
            test_layout.addWidget(self.test_diagnostics_btn)
            
            layout.addWidget(test_group)
            
            layout.addStretch()
            return controls_widget
        
        def create_diagnostics_panel(self):
            """Create the diagnostics panel."""
            diagnostics_widget = QWidget()
            layout = QVBoxLayout(diagnostics_widget)
            
            # Status Display
            status_group = QGroupBox("Ultra-Lite Status")
            status_layout = QGridLayout(status_group)
            
            self.status_labels = {}
            status_items = [
                ("Mode Active:", "mode_active"),
                ("Enforced by Power:", "enforced"),
                ("Enforcement Reason:", "reason"),
                ("Power Source:", "power_source"),
                ("Battery Level:", "battery_level"),
                ("Thread Cap:", "thread_cap"),
                ("Memory Cap:", "memory_cap"),
                ("Cache Cap:", "cache_cap"),
                ("pHash Threshold:", "phash_threshold"),
                ("Animations:", "animations"),
            ]
            
            for i, (label_text, key) in enumerate(status_items):
                label = QLabel(label_text)
                value_label = QLabel("N/A")
                value_label.setStyleSheet("color: #00ff88; font-weight: bold;")
                self.status_labels[key] = value_label
                
                status_layout.addWidget(label, i, 0)
                status_layout.addWidget(value_label, i, 1)
            
            layout.addWidget(status_group)
            
            # Performance Metrics
            metrics_group = QGroupBox("Performance Impact")
            metrics_layout = QVBoxLayout(metrics_group)
            
            self.metrics_progress = {}
            metric_items = [
                ("CPU Usage", "cpu"),
                ("Memory Usage", "memory"),
                ("I/O Usage", "io"),
            ]
            
            for label_text, key in metric_items:
                metrics_layout.addWidget(QLabel(label_text))
                progress = QProgressBar()
                progress.setRange(0, 100)
                self.metrics_progress[key] = progress
                metrics_layout.addWidget(progress)
            
            layout.addWidget(metrics_group)
            
            # Log Display
            log_group = QGroupBox("Activity Log")
            log_layout = QVBoxLayout(log_group)
            
            self.log_display = QTextEdit()
            self.log_display.setMaximumHeight(200)
            self.log_display.setReadOnly(True)
            log_layout.addWidget(self.log_display)
            
            layout.addWidget(log_group)
            
            return diagnostics_widget
        
        def setup_timers(self):
            """Setup update timers."""
            # Status update timer
            self.status_timer = QTimer()
            self.status_timer.timeout.connect(self.update_all_displays)
            self.status_timer.start(2000)  # Update every 2 seconds
            
            # Performance simulation timer
            self.perf_timer = QTimer()
            self.perf_timer.timeout.connect(self.update_performance_metrics)
            self.perf_timer.start(1000)  # Update every second
        
        def apply_dark_theme(self):
            """Apply dark theme styling."""
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QGroupBox {
                    background-color: #3c3c3c;
                    border: 2px solid #555555;
                    border-radius: 8px;
                    margin-top: 1ex;
                    padding-top: 10px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: #00ff88;
                }
                QPushButton {
                    background-color: #4a4a4a;
                    border: 2px solid #666666;
                    border-radius: 6px;
                    padding: 8px;
                    color: #ffffff;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #5a5a5a;
                    border-color: #00ff88;
                }
                QPushButton:pressed {
                    background-color: #333333;
                }
                QComboBox, QCheckBox, QSlider {
                    background-color: #4a4a4a;
                    border: 1px solid #666666;
                    border-radius: 4px;
                    padding: 4px;
                    color: #ffffff;
                }
                QTextEdit {
                    background-color: #1e1e1e;
                    border: 1px solid #666666;
                    border-radius: 4px;
                    color: #ffffff;
                    font-family: monospace;
                }
                QProgressBar {
                    border: 1px solid #666666;
                    border-radius: 4px;
                    background-color: #2b2b2b;
                }
                QProgressBar::chunk {
                    background-color: #00ff88;
                    border-radius: 3px;
                }
            """)
        
        def on_preset_changed(self, preset_name: str):
            """Handle preset selection change."""
            self.settings.set("Performance", "current_preset", preset_name)
            self.settings.save()
            
            self.mode_manager.apply_runtime_optimizations()
            self.log_message(f"🔄 Preset changed to: {preset_name}")
            
            self.update_all_displays()
        
        def simulate_power(self, power_type: str, level: int):
            """Simulate different power conditions."""
            if power_type == "ac":
                self.power_simulator.set_ac_power(level)
                self.log_message(f"🔌 Simulating AC power at {level}%")
            elif power_type == "dc":
                self.power_simulator.set_dc_power(level)
                self.log_message(f"🔋 Simulating DC power (battery) at {level}%")
            elif power_type == "low":
                self.power_simulator.set_low_battery(level)
                self.log_message(f"🪫 Simulating low battery at {level}%")
            
            # Patch the power manager's battery info method
            self.patch_power_manager()
            
            self.battery_slider.setValue(level)
            self.update_all_displays()
        
        def patch_power_manager(self):
            """Patch power manager with simulated battery info."""
            power_state = self.power_simulator.get_state()
            
            # Use patch to override battery info
            with patch.object(self.mode_manager.power_manager, '_get_battery_info', 
                            return_value=power_state):
                self.mode_manager.power_manager._check_power_status()
        
        def on_battery_changed(self, value: int):
            """Handle battery level slider change."""
            self.battery_label.setText(f"{value}%")
            
            # Update current power state
            current_state = self.power_simulator.get_state()
            current_state['percent'] = value
            self.power_simulator.current_state = current_state
            
            self.patch_power_manager()
        
        def on_auto_switch_toggled(self, checked: bool):
            """Handle auto-switch toggle."""
            self.settings.set("General", "battery_saver_auto_switch", checked)
            self.settings.save()
            
            status = "enabled" if checked else "disabled"
            self.log_message(f"⚙️ Battery saver auto-switch {status}")
        
        def force_ultra_lite(self):
            """Force Ultra-Lite mode on/off."""
            current_active = self.mode_manager.is_ultra_lite_active()
            
            if current_active:
                success = self.mode_manager.force_ultra_lite(False, "manual override")
                if success:
                    self.log_message("🔓 Ultra-Lite mode manually disabled")
                else:
                    self.log_message("⚠️ Cannot override - enforced by power management")
            else:
                self.mode_manager.force_ultra_lite(True, "manual override")
                self.log_message("🔒 Ultra-Lite mode manually enabled")
            
            self.update_all_displays()
        
        def test_format_skipping(self):
            """Test format skipping in Ultra-Lite mode."""
            self.log_message("🧪 Testing format skipping...")
            
            # Create thumbnail generator
            db_path = self.temp_dir / "test_formats.db"
            thumb_gen = ThumbnailGenerator(db_path, self.settings)
            
            test_formats = [
                (Path("test.cr2"), "Canon RAW"),
                (Path("test.nef"), "Nikon RAW"),
                (Path("test.tif"), "TIFF"),
                (Path("test.jpg"), "JPEG"),
                (Path("test.png"), "PNG"),
            ]
            
            for file_path, format_name in test_formats:
                skipped = thumb_gen.should_skip_format(file_path)
                status = "SKIPPED" if skipped else "PROCESSED"
                self.log_message(f"  📁 {format_name}: {status}")
        
        def test_thread_limiting(self):
            """Test thread limiting enforcement."""
            self.log_message("🧵 Testing thread limiting...")
            
            enforcer = self.mode_manager.enforcer
            
            test_values = [1, 4, 8, 16, 32]
            for requested in test_values:
                enforced = enforcer.enforce_thread_limits(requested)
                if enforced != requested:
                    self.log_message(f"  🔒 {requested} threads → {enforced} (limited)")
                else:
                    self.log_message(f"  ✅ {requested} threads → {enforced} (allowed)")
        
        def show_full_diagnostics(self):
            """Show comprehensive diagnostics."""
            self.log_message("📊 Full diagnostics:")
            
            diagnostics = get_ultra_lite_diagnostics(self.settings)
            
            self.log_message(f"  • Ultra-Lite active: {diagnostics['active']}")
            self.log_message(f"  • Enforced by power: {diagnostics['enforced']}")
            self.log_message(f"  • Enforcement reason: {diagnostics.get('reason', 'None')}")
            
            restrictions = diagnostics.get('restrictions', {})
            self.log_message(f"  • Thread limit: {restrictions.get('threads', 'N/A')}")
            self.log_message(f"  • Memory limit: {restrictions.get('memory', 'N/A')}MB")
            self.log_message(f"  • Animations: {restrictions.get('animations', 'N/A')}")
            self.log_message(f"  • pHash threshold: {restrictions.get('phash_threshold', 'N/A')}")
        
        def on_mode_changed(self, activated: bool, reason: str):
            """Handle mode change signals."""
            status = "ACTIVATED" if activated else "DEACTIVATED"
            self.log_message(f"🔄 Ultra-Lite mode {status}: {reason}")
        
        def on_performance_warning(self, warning: str):
            """Handle performance warning signals."""
            self.log_message(f"⚠️ {warning}")
        
        def update_all_displays(self):
            """Update all status displays."""
            # Get current status
            power_status = self.mode_manager.get_power_status()
            
            # Update status labels
            self.status_labels["mode_active"].setText(
                "✅ YES" if power_status.get("ultra_lite_active", False) else "❌ NO"
            )
            self.status_labels["enforced"].setText(
                "✅ YES" if power_status.get("ultra_lite_enforced", False) else "❌ NO"
            )
            self.status_labels["reason"].setText(
                power_status.get("enforcement_reason", "None") or "None"
            )
            self.status_labels["power_source"].setText(
                power_status.get("power_source", "UNKNOWN").upper()
            )
            self.status_labels["battery_level"].setText(
                f"{power_status.get('battery_level', 100)}%"
            )
            
            # Update configuration details
            config = power_status.get("effective_config", {})
            self.status_labels["thread_cap"].setText(str(config.get("thread_cap", "N/A")))
            self.status_labels["memory_cap"].setText(f"{config.get('memory_cap_mb', 'N/A')}MB")
            self.status_labels["cache_cap"].setText(f"{config.get('cache_size_cap_mb', 'N/A')}MB")
            self.status_labels["phash_threshold"].setText(f"≤{config.get('phash_threshold', 'N/A')}")
            self.status_labels["animations"].setText(
                "Disabled" if not config.get("animations_enabled", True) else "Enabled"
            )
            
            # Update preset combo
            current_preset = self.settings.get("Performance", "current_preset", "Balanced")
            if self.preset_combo.currentText() != current_preset:
                self.preset_combo.setCurrentText(current_preset)
        
        def update_performance_metrics(self):
            """Update simulated performance metrics."""
            import random
            
            # Simulate different performance based on Ultra-Lite mode
            if self.mode_manager.is_ultra_lite_active():
                # Lower resource usage in Ultra-Lite mode
                cpu_usage = random.randint(20, 40)
                memory_usage = random.randint(30, 50)
                io_usage = random.randint(10, 30)
            else:
                # Higher resource usage in normal modes
                cpu_usage = random.randint(50, 80)
                memory_usage = random.randint(60, 85)
                io_usage = random.randint(40, 70)
            
            self.metrics_progress["cpu"].setValue(cpu_usage)
            self.metrics_progress["memory"].setValue(memory_usage)
            self.metrics_progress["io"].setValue(io_usage)
        
        def log_message(self, message: str):
            """Add message to log display."""
            timestamp = time.strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}"
            
            self.log_display.append(log_entry)
            
            # Keep log size manageable
            if self.log_display.document().blockCount() > 100:
                cursor = self.log_display.textCursor()
                cursor.movePosition(cursor.Start)
                cursor.select(cursor.BlockUnderCursor)
                cursor.removeSelectedText()
        
        def closeEvent(self, event):
            """Handle window close event."""
            self.mode_manager.cleanup()
            
            # Cleanup temp directory
            import shutil
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            
            event.accept()


def main():
    """Main demo execution."""
    if not QT_AVAILABLE:
        print("❌ PySide6 not available - cannot run GUI demo")
        return
    
    app = QApplication(sys.argv)
    
    # Create and show demo window
    demo = UltraLiteDemoWindow()
    demo.show()
    
    print("🚀 Step 21 Ultra-Lite Mode Demo launched!")
    print("💡 Try different power scenarios and preset changes")
    print("📊 Watch the diagnostics panel for real-time updates")
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()