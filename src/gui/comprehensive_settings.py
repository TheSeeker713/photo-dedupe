#!/usr/bin/env python3
"""
Step 19: Comprehensive Settings Dialog
Multi-tab settings dialog with full configuration options and Low-End Mode support.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Callable

try:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
        QWidget, QPushButton, QLabel, QCheckBox, QSpinBox, QComboBox,
        QSlider, QGroupBox, QLineEdit, QTextEdit, QFrame, QSizePolicy,
        QFileDialog, QMessageBox, QProgressBar, QToolTip, QScrollArea
    )
    from PySide6.QtCore import Qt, QSize, Signal, QTimer, QThread
    from PySide6.QtGui import QFont, QIcon, QPalette, QPixmap, QPainter, QColor
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    # Fallback classes
    class QDialog: pass
    class QWidget: pass
    class QPushButton: pass
    class Signal: pass

# Add src to path for imports
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.settings import Settings
    from gui.easter_egg import show_easter_egg
except ImportError:
    Settings = None
    show_easter_egg = None

class HelpTooltipMixin:
    """Mixin for adding help tooltips to widgets."""
    
    @staticmethod
    def add_help_tooltip(widget, text: str):
        """Add a help tooltip to a widget."""
        widget.setToolTip(f"💡 {text}")
        widget.setToolTipDuration(10000)  # 10 seconds

class SecretEasterEggButton(QPushButton):
    """The tiny, innocuous button that doesn't look like it belongs - even smaller now!"""
    
    def __init__(self):
        super().__init__()
        self.setText("⋄")  # Diamond symbol
        self.setFixedSize(8, 8)  # Even smaller!
        self.setToolTip("")  # No tooltip
        
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #444;
                font-size: 6px;
                font-family: monospace;
            }
            QPushButton:hover {
                color: #666;
                background-color: rgba(255, 255, 255, 0.03);
            }
            QPushButton:pressed {
                color: #888;
            }
        """)
        
        self.clicked.connect(self.activate_easter_egg)
    
    def activate_easter_egg(self):
        """Activate the easter egg game."""
        if show_easter_egg:
            show_easter_egg(self.parent())

class PerformancePresetManager:
    """Manages performance preset configurations."""
    
    PRESETS = {
        "Ultra-Lite": {
            "description": "Minimal resource usage for low-end systems",
            "thread_cap": 2,
            "io_throttle": 1.0,
            "memory_cap_mb": 512,
            "enable_orb_fallback": False,
            "on_demand_thumbs": True,
            "skip_raw_tiff": True,
            "cache_size_cap_mb": 256,
        },
        "Balanced": {
            "description": "Good performance with moderate resource usage",
            "thread_cap": 4,
            "io_throttle": 0.5,
            "memory_cap_mb": 2048,
            "enable_orb_fallback": True,
            "on_demand_thumbs": True,
            "skip_raw_tiff": False,
            "cache_size_cap_mb": 1024,
        },
        "Accurate": {
            "description": "Maximum accuracy and performance",
            "thread_cap": 8,
            "io_throttle": 0.0,
            "memory_cap_mb": 8192,
            "enable_orb_fallback": True,
            "on_demand_thumbs": False,
            "skip_raw_tiff": False,
            "cache_size_cap_mb": 2048,
        },
        "Custom": {
            "description": "User-defined configuration",
        }
    }
    
    @classmethod
    def get_preset_for_settings(cls, settings: Dict[str, Any]) -> str:
        """Determine which preset matches current settings."""
        for preset_name, preset_config in cls.PRESETS.items():
            if preset_name == "Custom":
                continue
                
            matches = True
            for key, expected_value in preset_config.items():
                if key == "description":
                    continue
                    
                # Check if current settings match this preset
                current_value = settings.get(key)
                if current_value != expected_value:
                    matches = False
                    break
            
            if matches:
                return preset_name
        
        return "Custom"

class CacheClearWorker(QThread):
    """Background worker for clearing cache."""
    
    progress = Signal(int, str)
    finished = Signal(bool, str)
    
    def __init__(self, cache_dir: Path):
        super().__init__()
        self.cache_dir = cache_dir
    
    def run(self):
        """Clear the cache directory."""
        try:
            if not self.cache_dir.exists():
                self.finished.emit(True, "Cache directory doesn't exist")
                return
            
            files = list(self.cache_dir.rglob("*"))
            total_files = len([f for f in files if f.is_file()])
            
            if total_files == 0:
                self.finished.emit(True, "Cache is already empty")
                return
            
            deleted_count = 0
            for i, file_path in enumerate(files):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        progress = int((i + 1) / len(files) * 100)
                        self.progress.emit(progress, f"Deleted {deleted_count} files...")
                    except Exception as e:
                        self.progress.emit(int((i + 1) / len(files) * 100), f"Error: {str(e)}")
            
            # Remove empty directories
            for dir_path in sorted([f for f in files if f.is_dir()], reverse=True):
                try:
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                except:
                    pass
            
            self.finished.emit(True, f"Successfully cleared {deleted_count} files from cache")
            
        except Exception as e:
            self.finished.emit(False, f"Error clearing cache: {str(e)}")

class ComprehensiveSettingsDialog(QDialog, HelpTooltipMixin):
    """Comprehensive settings dialog for Step 19."""
    
    settings_changed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings - Photo Deduplication Tool")
        self.setMinimumSize(700, 600)
        self.setModal(True)
        
        # Load current settings
        self.settings = Settings() if Settings else None
        self.settings_data = self.settings.as_dict() if self.settings else {}
        self.original_settings = self.settings_data.copy()
        
        # Track if changes need restart
        self.needs_restart = False
        self.preset_manager = PerformancePresetManager()
        
        # Setup UI
        self.setup_ui()
        self.load_current_settings()
        self.apply_theme()
        
        # Connect preset changes
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
    
    def setup_ui(self):
        """Setup the complete settings UI."""
        layout = QVBoxLayout()
        
        # Create tabs
        self.tab_widget = QTabWidget()
        
        # Create all tabs
        self.setup_general_tab()
        self.setup_performance_tab()
        self.setup_hashing_tab()
        self.setup_cache_tab()
        self.setup_delete_tab()
        self.setup_about_tab()
        
        layout.addWidget(self.tab_widget)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        # Restore defaults button
        self.restore_defaults_button = QPushButton("🔄 Restore Defaults")
        self.restore_defaults_button.clicked.connect(self.restore_defaults)
        self.add_help_tooltip(self.restore_defaults_button, 
                             "Reset all settings to their default values")
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        
        button_layout.addWidget(self.restore_defaults_button)
        button_layout.addWidget(self.status_label)
        button_layout.addStretch()
        
        # Standard dialog buttons
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept_settings)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_settings)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.apply_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def setup_general_tab(self):
        """Setup the General settings tab."""
        general_widget = QScrollArea()
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        # UI Settings
        ui_group = QGroupBox("User Interface")
        ui_layout = QGridLayout(ui_group)
        
        # Theme selection
        ui_layout.addWidget(QLabel("Theme:"), 0, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "System"])
        self.add_help_tooltip(self.theme_combo, "Choose the application color theme")
        ui_layout.addWidget(self.theme_combo, 0, 1)
        
        # HiDPI scaling
        ui_layout.addWidget(QLabel("HiDPI Scaling:"), 1, 0)
        self.hidpi_combo = QComboBox()
        self.hidpi_combo.addItems(["Auto", "100%", "125%", "150%", "200%"])
        self.add_help_tooltip(self.hidpi_combo, "Adjust interface scaling for high-resolution displays")
        ui_layout.addWidget(self.hidpi_combo, 1, 1)
        
        # Show tooltips
        self.show_tooltips_check = QCheckBox("Show help tooltips")
        self.add_help_tooltip(self.show_tooltips_check, "Enable helpful tooltips throughout the interface")
        ui_layout.addWidget(self.show_tooltips_check, 2, 0, 1, 2)
        
        layout.addWidget(ui_group)
        
        # File Patterns
        patterns_group = QGroupBox("File Patterns")
        patterns_layout = QVBoxLayout(patterns_group)
        
        # Include patterns
        patterns_layout.addWidget(QLabel("Include patterns (one per line):"))
        self.include_patterns_text = QTextEdit()
        self.include_patterns_text.setMaximumHeight(80)
        self.add_help_tooltip(self.include_patterns_text, 
                             "File patterns to include in scanning (e.g., *.jpg, *.png)")
        patterns_layout.addWidget(self.include_patterns_text)
        
        # Exclude patterns  
        patterns_layout.addWidget(QLabel("Exclude patterns (one per line):"))
        self.exclude_patterns_text = QTextEdit()
        self.exclude_patterns_text.setMaximumHeight(80)
        self.add_help_tooltip(self.exclude_patterns_text,
                             "File patterns to exclude from scanning (e.g., *thumbnail*, *temp*)")
        patterns_layout.addWidget(self.exclude_patterns_text)
        
        layout.addWidget(patterns_group)
        
        # Battery Settings
        battery_group = QGroupBox("Power Management")
        battery_layout = QGridLayout(battery_group)
        
        self.battery_saver_check = QCheckBox("Auto-switch to Ultra-Lite mode on battery")
        self.add_help_tooltip(self.battery_saver_check,
                             "Automatically reduce performance when running on battery power")
        battery_layout.addWidget(self.battery_saver_check, 0, 0, 1, 2)
        
        layout.addWidget(battery_group)
        layout.addStretch()
        
        general_widget.setWidget(content_widget)
        general_widget.setWidgetResizable(True)
        self.tab_widget.addTab(general_widget, "General")
    
    def setup_performance_tab(self):
        """Setup the Performance settings tab."""
        performance_widget = QScrollArea()
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        # Performance Presets
        presets_group = QGroupBox("Performance Presets")
        presets_layout = QGridLayout(presets_group)
        
        presets_layout.addWidget(QLabel("Preset:"), 0, 0)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Ultra-Lite", "Balanced", "Accurate", "Custom"])
        self.add_help_tooltip(self.preset_combo,
                             "Choose a performance preset or select Custom for manual configuration")
        presets_layout.addWidget(self.preset_combo, 0, 1)
        
        self.preset_description = QLabel()
        self.preset_description.setWordWrap(True)
        self.preset_description.setStyleSheet("color: #888; font-style: italic; margin: 5px;")
        presets_layout.addWidget(self.preset_description, 1, 0, 1, 2)
        
        layout.addWidget(presets_group)
        
        # Threading Settings
        threading_group = QGroupBox("Threading")
        threading_layout = QGridLayout(threading_group)
        
        threading_layout.addWidget(QLabel("Thread cap:"), 0, 0)
        self.thread_cap_spin = QSpinBox()
        self.thread_cap_spin.setRange(1, 32)
        self.thread_cap_spin.valueChanged.connect(self.on_manual_setting_changed)
        self.add_help_tooltip(self.thread_cap_spin,
                             "Maximum number of worker threads for parallel processing")
        threading_layout.addWidget(self.thread_cap_spin, 0, 1)
        
        self.thread_cap_label = QLabel()
        threading_layout.addWidget(self.thread_cap_label, 0, 2)
        
        layout.addWidget(threading_group)
        
        # I/O Settings
        io_group = QGroupBox("I/O Performance")
        io_layout = QGridLayout(io_group)
        
        io_layout.addWidget(QLabel("I/O throttle:"), 0, 0)
        self.io_throttle_slider = QSlider(Qt.Horizontal)
        self.io_throttle_slider.setRange(0, 20)  # 0.0 to 2.0 in 0.1 increments
        self.io_throttle_slider.valueChanged.connect(self.on_io_throttle_changed)
        self.io_throttle_slider.valueChanged.connect(self.on_manual_setting_changed)
        self.add_help_tooltip(self.io_throttle_slider,
                             "Limit I/O operations per second (0 = no limit, higher = more throttling)")
        io_layout.addWidget(self.io_throttle_slider, 0, 1)
        
        self.io_throttle_label = QLabel()
        io_layout.addWidget(self.io_throttle_label, 0, 2)
        
        layout.addWidget(io_group)
        
        # Memory Settings
        memory_group = QGroupBox("Memory")
        memory_layout = QGridLayout(memory_group)
        
        memory_layout.addWidget(QLabel("Memory cap (MB):"), 0, 0)
        self.memory_cap_spin = QSpinBox()
        self.memory_cap_spin.setRange(256, 16384)
        self.memory_cap_spin.setSingleStep(256)
        self.memory_cap_spin.valueChanged.connect(self.on_manual_setting_changed)
        self.add_help_tooltip(self.memory_cap_spin,
                             "Maximum memory usage for image processing and caching")
        memory_layout.addWidget(self.memory_cap_spin, 0, 1)
        
        layout.addWidget(memory_group)
        
        # Feature Settings
        features_group = QGroupBox("Features")
        features_layout = QGridLayout(features_group)
        
        self.orb_fallback_check = QCheckBox("Enable ORB feature matching fallback")
        self.orb_fallback_check.toggled.connect(self.on_manual_setting_changed)
        self.add_help_tooltip(self.orb_fallback_check,
                             "Use advanced ORB features when perceptual hashing fails")
        features_layout.addWidget(self.orb_fallback_check, 0, 0, 1, 2)
        
        self.on_demand_thumbs_check = QCheckBox("Generate thumbnails on-demand")
        self.on_demand_thumbs_check.toggled.connect(self.on_manual_setting_changed)
        self.add_help_tooltip(self.on_demand_thumbs_check,
                             "Generate thumbnails only when needed (saves disk space and startup time)")
        features_layout.addWidget(self.on_demand_thumbs_check, 1, 0, 1, 2)
        
        self.skip_raw_check = QCheckBox("Skip RAW/TIFF files in low-end mode")
        self.skip_raw_check.toggled.connect(self.on_manual_setting_changed)
        self.add_help_tooltip(self.skip_raw_check,
                             "Skip processing large RAW and TIFF files to improve performance")
        features_layout.addWidget(self.skip_raw_check, 2, 0, 1, 2)
        
        layout.addWidget(features_group)
        layout.addStretch()
        
        performance_widget.setWidget(content_widget)
        performance_widget.setWidgetResizable(True)
        self.tab_widget.addTab(performance_widget, "Performance")
    
    def setup_hashing_tab(self):
        """Setup the Hashing settings tab."""
        hashing_widget = QScrollArea()
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        # Similarity Thresholds
        thresholds_group = QGroupBox("Similarity Thresholds")
        thresholds_layout = QGridLayout(thresholds_group)
        
        # Perceptual hash threshold
        thresholds_layout.addWidget(QLabel("Perceptual hash:"), 0, 0)
        self.phash_slider = QSlider(Qt.Horizontal)
        self.phash_slider.setRange(1, 20)
        self.phash_slider.valueChanged.connect(self.on_phash_changed)
        self.add_help_tooltip(self.phash_slider,
                             "Similarity threshold for perceptual hashing (lower = more strict)")
        thresholds_layout.addWidget(self.phash_slider, 0, 1)
        
        self.phash_label = QLabel()
        thresholds_layout.addWidget(self.phash_label, 0, 2)
        
        # Difference hash threshold
        thresholds_layout.addWidget(QLabel("Difference hash:"), 1, 0)
        self.dhash_slider = QSlider(Qt.Horizontal)
        self.dhash_slider.setRange(1, 20)
        self.dhash_slider.valueChanged.connect(self.on_dhash_changed)
        self.add_help_tooltip(self.dhash_slider,
                             "Similarity threshold for difference hashing (lower = more strict)")
        thresholds_layout.addWidget(self.dhash_slider, 1, 1)
        
        self.dhash_label = QLabel()
        thresholds_layout.addWidget(self.dhash_label, 1, 2)
        
        # Average hash threshold
        thresholds_layout.addWidget(QLabel("Average hash:"), 2, 0)
        self.ahash_slider = QSlider(Qt.Horizontal)
        self.ahash_slider.setRange(1, 20)
        self.ahash_slider.valueChanged.connect(self.on_ahash_changed)
        self.add_help_tooltip(self.ahash_slider,
                             "Similarity threshold for average hashing (lower = more strict)")
        thresholds_layout.addWidget(self.ahash_slider, 2, 1)
        
        self.ahash_label = QLabel()
        thresholds_layout.addWidget(self.ahash_label, 2, 2)
        
        layout.addWidget(thresholds_group)
        
        # Strict Mode Settings
        strict_group = QGroupBox("Strict Mode Options")
        strict_layout = QGridLayout(strict_group)
        
        self.strict_hash_check = QCheckBox("Strict hash matching")
        self.add_help_tooltip(self.strict_hash_check,
                             "Require exact hash matches for duplicate detection")
        strict_layout.addWidget(self.strict_hash_check, 0, 0)
        
        self.strict_exif_check = QCheckBox("Strict EXIF comparison")
        self.add_help_tooltip(self.strict_exif_check,
                             "Compare EXIF metadata strictly (camera, date, settings)")
        strict_layout.addWidget(self.strict_exif_check, 1, 0)
        
        self.strict_size_check = QCheckBox("Strict file size matching")
        self.add_help_tooltip(self.strict_size_check,
                             "Require exact file size matches for duplicates")
        strict_layout.addWidget(self.strict_size_check, 2, 0)
        
        layout.addWidget(strict_group)
        
        # Algorithm Settings
        algo_group = QGroupBox("Algorithm Selection")
        algo_layout = QGridLayout(algo_group)
        
        self.use_perceptual_check = QCheckBox("Use perceptual hashing")
        self.add_help_tooltip(self.use_perceptual_check,
                             "Enable perceptual hash comparison for similar images")
        algo_layout.addWidget(self.use_perceptual_check, 0, 0)
        
        self.use_orb_check = QCheckBox("Use ORB feature matching")
        self.add_help_tooltip(self.use_orb_check,
                             "Enable advanced ORB feature detection for complex similarities")
        algo_layout.addWidget(self.use_orb_check, 1, 0)
        
        layout.addWidget(algo_group)
        layout.addStretch()
        
        hashing_widget.setWidget(content_widget)
        hashing_widget.setWidgetResizable(True)
        self.tab_widget.addTab(hashing_widget, "Hashing")
    
    def setup_cache_tab(self):
        """Setup the Cache settings tab."""
        cache_widget = QScrollArea()
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        # Cache Size Settings
        size_group = QGroupBox("Cache Size")
        size_layout = QGridLayout(size_group)
        
        size_layout.addWidget(QLabel("Size cap (MB):"), 0, 0)
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(64, 8192)
        self.cache_size_spin.setSingleStep(64)
        self.add_help_tooltip(self.cache_size_spin,
                             "Maximum cache size in megabytes")
        size_layout.addWidget(self.cache_size_spin, 0, 1)
        
        size_layout.addWidget(QLabel("Max age (days):"), 1, 0)
        self.cache_age_spin = QSpinBox()
        self.cache_age_spin.setRange(1, 365)
        self.add_help_tooltip(self.cache_age_spin,
                             "Automatically remove cache items older than this many days")
        size_layout.addWidget(self.cache_age_spin, 1, 1)
        
        layout.addWidget(size_group)
        
        # Cache Location
        location_group = QGroupBox("Cache Location")
        location_layout = QVBoxLayout(location_group)
        
        cache_path_layout = QHBoxLayout()
        self.cache_path_edit = QLineEdit()
        self.cache_path_edit.setReadOnly(True)
        self.add_help_tooltip(self.cache_path_edit, "Current cache directory location")
        cache_path_layout.addWidget(self.cache_path_edit)
        
        self.browse_cache_button = QPushButton("Browse...")
        self.browse_cache_button.clicked.connect(self.browse_cache_directory)
        self.add_help_tooltip(self.browse_cache_button, "Choose a different cache directory")
        cache_path_layout.addWidget(self.browse_cache_button)
        
        location_layout.addLayout(cache_path_layout)
        layout.addWidget(location_group)
        
        # Cache Management
        management_group = QGroupBox("Cache Management")
        management_layout = QVBoxLayout(management_group)
        
        # Cache info
        self.cache_info_label = QLabel("Calculating cache size...")
        self.cache_info_label.setStyleSheet("color: #888; margin: 5px;")
        management_layout.addWidget(self.cache_info_label)
        
        # Clear cache button
        clear_layout = QHBoxLayout()
        self.clear_cache_button = QPushButton("🗑️ Clear Cache")
        self.clear_cache_button.clicked.connect(self.clear_cache)
        self.add_help_tooltip(self.clear_cache_button,
                             "Delete all cached thumbnails and temporary files")
        clear_layout.addWidget(self.clear_cache_button)
        
        # Progress bar for cache clearing
        self.cache_progress = QProgressBar()
        self.cache_progress.setVisible(False)
        clear_layout.addWidget(self.cache_progress)
        
        clear_layout.addStretch()
        management_layout.addLayout(clear_layout)
        
        layout.addWidget(management_group)
        
        # Security Settings
        security_group = QGroupBox("Security")
        security_layout = QGridLayout(security_group)
        
        self.encrypt_db_check = QCheckBox("Encrypt database (requires restart)")
        self.add_help_tooltip(self.encrypt_db_check,
                             "Encrypt the local database file for additional security")
        security_layout.addWidget(self.encrypt_db_check, 0, 0)
        
        self.secure_delete_check = QCheckBox("Secure file deletion")
        self.add_help_tooltip(self.secure_delete_check,
                             "Overwrite file data when deleting for enhanced security")
        security_layout.addWidget(self.secure_delete_check, 1, 0)
        
        layout.addWidget(security_group)
        layout.addStretch()
        
        cache_widget.setWidget(content_widget)
        cache_widget.setWidgetResizable(True)
        self.tab_widget.addTab(cache_widget, "Cache")
        
        # Start cache size calculation
        QTimer.singleShot(100, self.update_cache_info)
    
    def setup_delete_tab(self):
        """Setup the Delete behavior settings tab."""
        delete_widget = QScrollArea()
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        # Delete Method
        method_group = QGroupBox("Delete Method")
        method_layout = QGridLayout(method_group)
        
        method_layout.addWidget(QLabel("Default action:"), 0, 0)
        self.delete_method_combo = QComboBox()
        self.delete_method_combo.addItems(["Recycle Bin", "Quarantine Folder", "Permanent Delete"])
        self.add_help_tooltip(self.delete_method_combo,
                             "Choose how duplicate files are handled when deleted")
        method_layout.addWidget(self.delete_method_combo, 0, 1)
        
        # Quarantine settings
        method_layout.addWidget(QLabel("Quarantine folder:"), 1, 0)
        quarantine_layout = QHBoxLayout()
        self.quarantine_path_edit = QLineEdit()
        self.add_help_tooltip(self.quarantine_path_edit, "Folder for quarantined duplicate files")
        quarantine_layout.addWidget(self.quarantine_path_edit)
        
        self.browse_quarantine_button = QPushButton("Browse...")
        self.browse_quarantine_button.clicked.connect(self.browse_quarantine_directory)
        quarantine_layout.addWidget(self.browse_quarantine_button)
        
        quarantine_widget = QWidget()
        quarantine_widget.setLayout(quarantine_layout)
        method_layout.addWidget(quarantine_widget, 1, 1)
        
        layout.addWidget(method_group)
        
        # Safety Settings
        safety_group = QGroupBox("Safety Settings")
        safety_layout = QGridLayout(safety_group)
        
        self.confirm_delete_check = QCheckBox("Confirm before delete")
        self.add_help_tooltip(self.confirm_delete_check,
                             "Show confirmation dialog before deleting files")
        safety_layout.addWidget(self.confirm_delete_check, 0, 0)
        
        self.backup_before_delete_check = QCheckBox("Create backup before delete")
        self.add_help_tooltip(self.backup_before_delete_check,
                             "Create a backup of files before deleting them")
        safety_layout.addWidget(self.backup_before_delete_check, 1, 0)
        
        safety_layout.addWidget(QLabel("Daily delete cap:"), 2, 0)
        self.daily_cap_spin = QSpinBox()
        self.daily_cap_spin.setRange(0, 10000)
        self.daily_cap_spin.setSpecialValueText("No limit")
        self.add_help_tooltip(self.daily_cap_spin,
                             "Maximum number of files that can be deleted per day (0 = no limit)")
        safety_layout.addWidget(self.daily_cap_spin, 2, 1)
        
        layout.addWidget(safety_group)
        
        # Original Selection
        selection_group = QGroupBox("Original Selection Rules")
        selection_layout = QGridLayout(selection_group)
        
        selection_layout.addWidget(QLabel("Keep original rule:"), 0, 0)
        self.original_rule_combo = QComboBox()
        self.original_rule_combo.addItems([
            "Keep Largest", "Keep Oldest", "Keep Newest", 
            "Keep Best Quality", "Keep First Found"
        ])
        self.add_help_tooltip(self.original_rule_combo,
                             "Rule for automatically selecting which duplicate to keep as original")
        selection_layout.addWidget(self.original_rule_combo, 0, 1)
        
        self.prefer_jpeg_check = QCheckBox("Prefer JPEG over other formats")
        self.add_help_tooltip(self.prefer_jpeg_check,
                             "Prefer JPEG files as originals over PNG, BMP, etc.")
        selection_layout.addWidget(self.prefer_jpeg_check, 1, 0, 1, 2)
        
        layout.addWidget(selection_group)
        layout.addStretch()
        
        delete_widget.setWidget(content_widget)
        delete_widget.setWidgetResizable(True)
        self.tab_widget.addTab(delete_widget, "Delete")
    
    def setup_about_tab(self):
        """Setup the About tab with the easter egg."""
        about_widget = QWidget()
        layout = QVBoxLayout(about_widget)
        
        # Title
        title = QLabel("Photo Deduplication Tool")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        version = QLabel("Version 1.0.0 - Step 19 Complete")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: #888; margin-bottom: 20px;")
        layout.addWidget(version)
        
        # Description
        description = QTextEdit()
        description.setReadOnly(True)
        description.setMaximumHeight(200)
        description.setPlainText(
            "A comprehensive photo deduplication tool with intelligent duplicate detection, "
            "advanced GUI interface, safe deletion management, and comprehensive reporting.\n\n"
            "Features:\n"
            "• Multiple detection algorithms (SHA256, perceptual hashing)\n"
            "• Professional GUI with keyboard shortcuts\n"
            "• Safe deletion with recycle bin and undo support\n"
            "• Comprehensive CSV/JSON export with 25+ fields\n"
            "• Performance optimization and low-end mode support\n"
            "• Advanced settings and configuration options\n"
            "• Hidden surprises for curious users...\n\n"
            "Built with Python, PySide6, and attention to detail."
        )
        layout.addWidget(description)
        
        # System info
        sys_info = QLabel()
        cpu_count = os.cpu_count() or 4
        sys_info.setText(f"System: {sys.platform} | CPU cores: {cpu_count} | Python: {sys.version_info.major}.{sys.version_info.minor}")
        sys_info.setStyleSheet("color: #666; font-size: 10px; margin: 10px;")
        sys_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(sys_info)
        
        # Credits with easter egg
        credits_frame = QFrame()
        credits_layout = QHBoxLayout(credits_frame)
        credits_layout.setContentsMargins(10, 10, 10, 10)
        
        credits_text = QLabel("© 2025 DigiArtifact.com | Developer: Jeremy Robards")
        credits_text.setStyleSheet("color: #888;")
        credits_layout.addWidget(credits_text)
        
        credits_layout.addStretch()
        
        # The secret easter egg button - even more hidden!
        self.secret_button = SecretEasterEggButton()
        credits_layout.addWidget(self.secret_button)
        
        credits_layout.addSpacing(3)
        
        layout.addWidget(credits_frame)
        layout.addStretch()
        
        self.tab_widget.addTab(about_widget, "About")
    
    def load_current_settings(self):
        """Load current settings into the dialog controls."""
        if not self.settings_data:
            return
        
        # General tab
        ui_settings = self.settings_data.get("UI", {})
        self.theme_combo.setCurrentText(ui_settings.get("theme", "Dark"))
        self.hidpi_combo.setCurrentText(ui_settings.get("hidpi_scaling", "Auto"))
        self.show_tooltips_check.setChecked(ui_settings.get("show_tooltips", True))
        
        general_settings = self.settings_data.get("General", {})
        include_patterns = general_settings.get("include_patterns", [])
        self.include_patterns_text.setPlainText("\\n".join(include_patterns))
        
        exclude_patterns = general_settings.get("exclude_patterns", [])
        self.exclude_patterns_text.setPlainText("\\n".join(exclude_patterns))
        
        self.battery_saver_check.setChecked(general_settings.get("battery_saver_auto_switch", True))
        
        # Performance tab
        current_preset = self.preset_manager.get_preset_for_settings({
            "thread_cap": general_settings.get("thread_cap", 4),
            "io_throttle": general_settings.get("io_throttle", 0.5),
            "memory_cap_mb": 2048,  # Default value
            "enable_orb_fallback": self.settings_data.get("Hashing", {}).get("enable_orb_fallback", True),
            "on_demand_thumbs": self.settings_data.get("Cache", {}).get("on_demand_thumbs", True),
            "skip_raw_tiff": self.settings_data.get("Formats", {}).get("skip_raw_tiff_on_low_end", True),
            "cache_size_cap_mb": self.settings_data.get("Cache", {}).get("cache_size_cap_mb", 1024),
        })
        self.preset_combo.setCurrentText(current_preset)
        
        self.thread_cap_spin.setValue(general_settings.get("thread_cap", 4))
        self.io_throttle_slider.setValue(int(general_settings.get("io_throttle", 0.5) * 10))
        self.memory_cap_spin.setValue(2048)  # Default
        
        hashing_settings = self.settings_data.get("Hashing", {})
        self.orb_fallback_check.setChecked(hashing_settings.get("enable_orb_fallback", True))
        self.use_perceptual_check.setChecked(hashing_settings.get("use_perceptual_hash", True))
        
        cache_settings = self.settings_data.get("Cache", {})
        self.on_demand_thumbs_check.setChecked(cache_settings.get("on_demand_thumbs", True))
        
        formats_settings = self.settings_data.get("Formats", {})
        self.skip_raw_check.setChecked(formats_settings.get("skip_raw_tiff_on_low_end", True))
        
        # Hashing tab
        thresholds = hashing_settings.get("near_dupe_thresholds", {})
        self.phash_slider.setValue(thresholds.get("phash", 8))
        self.dhash_slider.setValue(thresholds.get("dhash", 8))
        self.ahash_slider.setValue(thresholds.get("ahash", 10))
        
        # Cache tab
        self.cache_size_spin.setValue(cache_settings.get("cache_size_cap_mb", 1024))
        self.cache_age_spin.setValue(cache_settings.get("cache_max_age_days", 30))
        self.cache_path_edit.setText(cache_settings.get("cache_dir", ""))
        
        # Delete tab
        delete_settings = self.settings_data.get("DeleteBehavior", {})
        default_action = delete_settings.get("default_action", "recycle")
        if default_action == "recycle":
            self.delete_method_combo.setCurrentText("Recycle Bin")
        elif default_action == "quarantine":
            self.delete_method_combo.setCurrentText("Quarantine Folder")
        else:
            self.delete_method_combo.setCurrentText("Permanent Delete")
        
        self.quarantine_path_edit.setText(delete_settings.get("quarantine_dir", ""))
        self.confirm_delete_check.setChecked(delete_settings.get("confirm_before_delete", True))
        self.daily_cap_spin.setValue(delete_settings.get("daily_cap", 0))
        
        original_rule = delete_settings.get("original_selection_rule", "keep_largest")
        rule_map = {
            "keep_largest": "Keep Largest",
            "keep_oldest": "Keep Oldest", 
            "keep_newest": "Keep Newest",
            "keep_best_quality": "Keep Best Quality",
            "keep_first": "Keep First Found"
        }
        self.original_rule_combo.setCurrentText(rule_map.get(original_rule, "Keep Largest"))
        
        # Update labels
        self.update_thread_cap_label()
        self.update_io_throttle_label()
        self.update_hash_labels()
        self.update_preset_description()
    
    def on_preset_changed(self, preset_name: str):
        """Handle preset selection change."""
        if preset_name == "Custom":
            self.update_preset_description()
            return
        
        if preset_name in self.preset_manager.PRESETS:
            preset_config = self.preset_manager.PRESETS[preset_name]
            
            # Update controls without triggering change events
            self.thread_cap_spin.blockSignals(True)
            self.io_throttle_slider.blockSignals(True)
            self.memory_cap_spin.blockSignals(True)
            self.orb_fallback_check.blockSignals(True)
            self.on_demand_thumbs_check.blockSignals(True)
            self.skip_raw_check.blockSignals(True)
            self.cache_size_spin.blockSignals(True)
            
            self.thread_cap_spin.setValue(preset_config.get("thread_cap", 4))
            self.io_throttle_slider.setValue(int(preset_config.get("io_throttle", 0.5) * 10))
            self.memory_cap_spin.setValue(preset_config.get("memory_cap_mb", 2048))
            self.orb_fallback_check.setChecked(preset_config.get("enable_orb_fallback", True))
            self.on_demand_thumbs_check.setChecked(preset_config.get("on_demand_thumbs", True))
            self.skip_raw_check.setChecked(preset_config.get("skip_raw_tiff", False))
            self.cache_size_spin.setValue(preset_config.get("cache_size_cap_mb", 1024))
            
            # Re-enable signals
            self.thread_cap_spin.blockSignals(False)
            self.io_throttle_slider.blockSignals(False)
            self.memory_cap_spin.blockSignals(False)
            self.orb_fallback_check.blockSignals(False)
            self.on_demand_thumbs_check.blockSignals(False)
            self.skip_raw_check.blockSignals(False)
            self.cache_size_spin.blockSignals(False)
            
            # Update labels
            self.update_thread_cap_label()
            self.update_io_throttle_label()
            self.update_preset_description()
            
            self.status_label.setText(f"Switched to {preset_name} preset")
    
    def on_manual_setting_changed(self):
        """Handle manual setting changes - switch to Custom preset."""
        if self.preset_combo.currentText() != "Custom":
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentText("Custom")
            self.preset_combo.blockSignals(False)
            self.update_preset_description()
            self.status_label.setText("Custom configuration")
    
    def update_preset_description(self):
        """Update the preset description label."""
        preset_name = self.preset_combo.currentText()
        if preset_name in self.preset_manager.PRESETS:
            description = self.preset_manager.PRESETS[preset_name].get("description", "")
            self.preset_description.setText(description)
        else:
            self.preset_description.setText("")
    
    def update_thread_cap_label(self):
        """Update thread cap label with recommended info."""
        value = self.thread_cap_spin.value()
        cpu_count = os.cpu_count() or 4
        if value == cpu_count:
            self.thread_cap_label.setText(f"({value} = CPU cores)")
        elif value > cpu_count:
            self.thread_cap_label.setText(f"({value} > CPU cores)")
        else:
            self.thread_cap_label.setText(f"({value} cores)")
    
    def on_io_throttle_changed(self, value):
        """Update I/O throttle label."""
        self.update_io_throttle_label()
    
    def update_io_throttle_label(self):
        """Update I/O throttle label."""
        value = self.io_throttle_slider.value() / 10.0
        if value == 0:
            self.io_throttle_label.setText("(No limit)")
        else:
            self.io_throttle_label.setText(f"({value:.1f} ops/sec)")
    
    def on_phash_changed(self, value):
        """Update perceptual hash label."""
        self.phash_label.setText(f"({value} bits)")
    
    def on_dhash_changed(self, value):
        """Update difference hash label.""" 
        self.dhash_label.setText(f"({value} bits)")
    
    def on_ahash_changed(self, value):
        """Update average hash label."""
        self.ahash_label.setText(f"({value} bits)")
    
    def update_hash_labels(self):
        """Update all hash threshold labels."""
        self.on_phash_changed(self.phash_slider.value())
        self.on_dhash_changed(self.dhash_slider.value())
        self.on_ahash_changed(self.ahash_slider.value())
    
    def browse_cache_directory(self):
        """Browse for cache directory."""
        current_dir = self.cache_path_edit.text()
        new_dir = QFileDialog.getExistingDirectory(
            self, "Select Cache Directory", current_dir
        )
        if new_dir:
            self.cache_path_edit.setText(new_dir)
            self.needs_restart = True
            self.status_label.setText("Cache directory changed (restart required)")
    
    def browse_quarantine_directory(self):
        """Browse for quarantine directory."""
        current_dir = self.quarantine_path_edit.text()
        new_dir = QFileDialog.getExistingDirectory(
            self, "Select Quarantine Directory", current_dir
        )
        if new_dir:
            self.quarantine_path_edit.setText(new_dir)
    
    def update_cache_info(self):
        """Update cache information display."""
        try:
            cache_dir = Path(self.cache_path_edit.text())
            if not cache_dir.exists():
                self.cache_info_label.setText("Cache directory does not exist")
                return
            
            files = list(cache_dir.rglob("*"))
            file_count = len([f for f in files if f.is_file()])
            
            total_size = 0
            for file_path in files:
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                    except:
                        pass
            
            size_mb = total_size / (1024 * 1024)
            self.cache_info_label.setText(f"Cache contains {file_count} files, {size_mb:.1f} MB")
            
        except Exception:
            self.cache_info_label.setText("Error reading cache information")
    
    def clear_cache(self):
        """Clear the cache directory."""
        cache_dir = Path(self.cache_path_edit.text())
        
        reply = QMessageBox.question(
            self, "Clear Cache",
            f"Are you sure you want to clear all cached files from:\\n{cache_dir}\\n\\n"
            "This will delete all thumbnails and temporary files.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.clear_cache_button.setEnabled(False)
        self.cache_progress.setVisible(True)
        self.cache_progress.setRange(0, 100)
        
        # Start cache clearing worker
        self.cache_worker = CacheClearWorker(cache_dir)
        self.cache_worker.progress.connect(self.on_cache_clear_progress)
        self.cache_worker.finished.connect(self.on_cache_clear_finished)
        self.cache_worker.start()
    
    def on_cache_clear_progress(self, progress: int, message: str):
        """Handle cache clear progress updates."""
        self.cache_progress.setValue(progress)
        self.status_label.setText(message)
    
    def on_cache_clear_finished(self, success: bool, message: str):
        """Handle cache clear completion."""
        self.cache_progress.setVisible(False)
        self.clear_cache_button.setEnabled(True)
        self.status_label.setText(message)
        
        if success:
            QTimer.singleShot(1000, self.update_cache_info)
    
    def restore_defaults(self):
        """Restore all settings to defaults."""
        reply = QMessageBox.question(
            self, "Restore Defaults",
            "Are you sure you want to restore all settings to their default values?\\n\\n"
            "This will reset all configuration and cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.settings:
                # Reset to defaults
                self.settings._data = {}
                self.settings.load()  # This will restore defaults
                self.settings_data = self.settings.as_dict()
                
                # Reload UI
                self.load_current_settings()
                self.status_label.setText("Settings restored to defaults")
                self.needs_restart = True
    
    def get_current_settings(self) -> Dict[str, Any]:
        """Get current settings from dialog controls."""
        settings = {}
        
        # General settings
        settings["General"] = {
            "include_patterns": [p.strip() for p in self.include_patterns_text.toPlainText().split("\\n") if p.strip()],
            "exclude_patterns": [p.strip() for p in self.exclude_patterns_text.toPlainText().split("\\n") if p.strip()],
            "thread_cap": self.thread_cap_spin.value(),
            "io_throttle": self.io_throttle_slider.value() / 10.0,
            "battery_saver_auto_switch": self.battery_saver_check.isChecked(),
        }
        
        # UI settings
        settings["UI"] = {
            "theme": self.theme_combo.currentText(),
            "hidpi_scaling": self.hidpi_combo.currentText(),
            "show_tooltips": self.show_tooltips_check.isChecked(),
        }
        
        # Hashing settings
        settings["Hashing"] = {
            "near_dupe_thresholds": {
                "phash": self.phash_slider.value(),
                "dhash": self.dhash_slider.value(),
                "ahash": self.ahash_slider.value(),
            },
            "enable_orb_fallback": self.orb_fallback_check.isChecked(),
            "use_perceptual_hash": self.use_perceptual_check.isChecked(),
        }
        
        # Cache settings
        settings["Cache"] = {
            "cache_size_cap_mb": self.cache_size_spin.value(),
            "cache_max_age_days": self.cache_age_spin.value(),
            "cache_dir": self.cache_path_edit.text(),
            "on_demand_thumbs": self.on_demand_thumbs_check.isChecked(),
        }
        
        # Delete settings
        delete_method_map = {
            "Recycle Bin": "recycle",
            "Quarantine Folder": "quarantine", 
            "Permanent Delete": "delete"
        }
        
        original_rule_map = {
            "Keep Largest": "keep_largest",
            "Keep Oldest": "keep_oldest",
            "Keep Newest": "keep_newest", 
            "Keep Best Quality": "keep_best_quality",
            "Keep First Found": "keep_first"
        }
        
        settings["DeleteBehavior"] = {
            "default_action": delete_method_map.get(self.delete_method_combo.currentText(), "recycle"),
            "quarantine_dir": self.quarantine_path_edit.text(),
            "confirm_before_delete": self.confirm_delete_check.isChecked(),
            "daily_cap": self.daily_cap_spin.value(),
            "original_selection_rule": original_rule_map.get(self.original_rule_combo.currentText(), "keep_largest"),
        }
        
        # Formats settings
        settings["Formats"] = {
            "skip_raw_tiff_on_low_end": self.skip_raw_check.isChecked(),
        }
        
        return settings
    
    def apply_settings(self):
        """Apply current settings."""
        if not self.settings:
            return
        
        new_settings = self.get_current_settings()
        
        # Update settings object
        for section, values in new_settings.items():
            for key, value in values.items():
                self.settings.set(section, key, value)
        
        self.settings.save()
        self.settings_changed.emit(new_settings)
        
        restart_msg = " (restart required)" if self.needs_restart else ""
        self.status_label.setText(f"Settings applied{restart_msg}")
    
    def accept_settings(self):
        """Accept and apply settings, then close."""
        self.apply_settings()
        
        if self.needs_restart:
            QMessageBox.information(
                self, "Restart Required",
                "Some settings require an application restart to take effect.\\n\\n"
                "Please restart the application for all changes to be applied."
            )
        
        self.accept()
    
    def apply_theme(self):
        """Apply dark theme to the dialog."""
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #2b2b2b;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background-color: #444;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #555;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #555;
                border-bottom: 2px solid #0078d4;
            }
            QTabBar::tab:hover {
                background-color: #4a4a4a;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #444;
                color: white;
                border: 1px solid #666;
                border-radius: 3px;
                padding: 6px 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #555;
                border-color: #777;
            }
            QPushButton:pressed {
                background-color: #333;
            }
            QPushButton:disabled {
                background-color: #333;
                color: #666;
                border-color: #444;
            }
            QComboBox, QSpinBox, QLineEdit {
                background-color: #444;
                color: white;
                border: 1px solid #666;
                border-radius: 3px;
                padding: 4px;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #aaa;
            }
            QSlider::groove:horizontal {
                border: 1px solid #444;
                height: 8px;
                background: #333;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #0078d4;
                border: 1px solid #005a9e;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QCheckBox {
                color: white;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #444;
                border: 1px solid #666;
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border: 1px solid #005a9e;
                border-radius: 2px;
            }
            QTextEdit {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #444;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #666;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #777;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                background-color: #333;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 2px;
            }
            QLabel {
                color: white;
            }
        """)

def show_comprehensive_settings_dialog(parent=None):
    """Show the comprehensive settings dialog."""
    if not PYSIDE6_AVAILABLE:
        return None
        
    dialog = ComprehensiveSettingsDialog(parent)
    return dialog.exec()

if __name__ == "__main__":
    """Demo the settings dialog."""
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
    
    class SettingsDemo(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Step 19: Comprehensive Settings Dialog Demo")
            self.setGeometry(100, 100, 400, 200)
            
            central_widget = QWidget()
            layout = QVBoxLayout(central_widget)
            
            button = QPushButton("🔧 Open Comprehensive Settings")
            button.clicked.connect(self.open_settings)
            layout.addWidget(button)
            
            self.setCentralWidget(central_widget)
        
        def open_settings(self):
            show_comprehensive_settings_dialog(self)
    
    app = QApplication(sys.argv)
    demo = SettingsDemo()
    demo.show()
    app.exec()