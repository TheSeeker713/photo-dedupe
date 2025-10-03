#!/usr/bin/env python3
"""
Settings Dialog with Secret Easter Egg
A settings dialog for the photo deduplication tool with a hidden mini-game.
"""

try:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
        QWidget, QPushButton, QLabel, QCheckBox, QSpinBox, QComboBox,
        QSlider, QGroupBox, QLineEdit, QTextEdit, QFrame, QSizePolicy
    )
    from PySide6.QtCore import Qt, QSize, Signal
    from PySide6.QtGui import QFont, QIcon, QPalette, QPixmap, QPainter, QColor
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    # Fallback classes
    class QDialog: pass
    class QWidget: pass
    class QPushButton: pass
    class Signal: pass

from .easter_egg import show_easter_egg

class SecretEasterEggButton(QPushButton):
    """A tiny, innocuous button that doesn't look like it belongs."""
    
    def __init__(self):
        super().__init__()
        # Make it look like a random UI glitch or design element
        self.setText("⋄")  # Diamond symbol - looks like decoration
        self.setFixedSize(12, 12)  # Very small
        self.setToolTip("")  # No tooltip to avoid suspicion
        
        # Style it to look like an unimportant UI element
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #666;
                font-size: 8px;
                font-family: monospace;
            }
            QPushButton:hover {
                color: #888;
                background-color: rgba(255, 255, 255, 0.05);
            }
            QPushButton:pressed {
                color: #AAA;
            }
        """)
        
        # Connect to easter egg
        self.clicked.connect(self.activate_easter_egg)
    
    def activate_easter_egg(self):
        """Activate the easter egg game."""
        show_easter_egg(self.parent())

class SettingsDialog(QDialog):
    """Settings dialog for the photo deduplication tool."""
    
    settings_changed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings - Photo Deduplication Tool")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        # Create the UI
        self.setup_ui()
        
        # Apply dark theme
        self.apply_theme()
    
    def setup_ui(self):
        """Setup the settings UI."""
        layout = QVBoxLayout()
        
        # Create tabs
        self.tab_widget = QTabWidget()
        
        # General settings tab
        self.setup_general_tab()
        
        # Analysis settings tab
        self.setup_analysis_tab()
        
        # Performance settings tab
        self.setup_performance_tab()
        
        # About tab (where the easter egg will be hidden)
        self.setup_about_tab()
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_settings)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.apply_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def setup_general_tab(self):
        """Setup the general settings tab."""
        general_widget = QWidget()
        layout = QVBoxLayout(general_widget)
        
        # Interface settings
        interface_group = QGroupBox("Interface")
        interface_layout = QGridLayout(interface_group)
        
        # Theme selection
        interface_layout.addWidget(QLabel("Theme:"), 0, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "Auto"])
        interface_layout.addWidget(self.theme_combo, 0, 1)
        
        # Preview size
        interface_layout.addWidget(QLabel("Preview Size:"), 1, 0)
        self.preview_size_slider = QSlider(Qt.Horizontal)
        self.preview_size_slider.setRange(100, 500)
        self.preview_size_slider.setValue(250)
        interface_layout.addWidget(self.preview_size_slider, 1, 1)
        
        # Show tooltips
        self.show_tooltips_check = QCheckBox("Show tooltips")
        self.show_tooltips_check.setChecked(True)
        interface_layout.addWidget(self.show_tooltips_check, 2, 0, 1, 2)
        
        layout.addWidget(interface_group)
        
        # File handling settings
        file_group = QGroupBox("File Handling")
        file_layout = QGridLayout(file_group)
        
        # Default action
        file_layout.addWidget(QLabel("Default duplicate action:"), 0, 0)
        self.default_action_combo = QComboBox()
        self.default_action_combo.addItems(["Ask", "Move to Recycle Bin", "Permanent Delete", "Move to Folder"])
        file_layout.addWidget(self.default_action_combo, 0, 1)
        
        # Backup before delete
        self.backup_check = QCheckBox("Create backup before deletion")
        self.backup_check.setChecked(True)
        file_layout.addWidget(self.backup_check, 1, 0, 1, 2)
        
        layout.addWidget(file_group)
        layout.addStretch()
        
        self.tab_widget.addTab(general_widget, "General")
    
    def setup_analysis_tab(self):
        """Setup the analysis settings tab."""
        analysis_widget = QWidget()
        layout = QVBoxLayout(analysis_widget)
        
        # Similarity settings
        similarity_group = QGroupBox("Similarity Detection")
        similarity_layout = QGridLayout(similarity_group)
        
        # Similarity threshold
        similarity_layout.addWidget(QLabel("Similarity threshold:"), 0, 0)
        self.similarity_slider = QSlider(Qt.Horizontal)
        self.similarity_slider.setRange(50, 100)
        self.similarity_slider.setValue(85)
        similarity_layout.addWidget(self.similarity_slider, 0, 1)
        
        self.similarity_label = QLabel("85%")
        self.similarity_slider.valueChanged.connect(
            lambda v: self.similarity_label.setText(f"{v}%")
        )
        similarity_layout.addWidget(self.similarity_label, 0, 2)
        
        # Hash algorithm
        similarity_layout.addWidget(QLabel("Hash algorithm:"), 1, 0)
        self.hash_combo = QComboBox()
        self.hash_combo.addItems(["Perceptual", "Average", "Difference", "Wavelet"])
        similarity_layout.addWidget(self.hash_combo, 1, 1)
        
        layout.addWidget(similarity_group)
        
        # EXIF settings
        exif_group = QGroupBox("EXIF Analysis")
        exif_layout = QGridLayout(exif_group)
        
        self.analyze_exif_check = QCheckBox("Analyze EXIF data")
        self.analyze_exif_check.setChecked(True)
        exif_layout.addWidget(self.analyze_exif_check, 0, 0, 1, 2)
        
        self.ignore_timestamp_check = QCheckBox("Ignore timestamp differences")
        exif_layout.addWidget(self.ignore_timestamp_check, 1, 0, 1, 2)
        
        layout.addWidget(exif_group)
        layout.addStretch()
        
        self.tab_widget.addTab(analysis_widget, "Analysis")
    
    def setup_performance_tab(self):
        """Setup the performance settings tab."""
        performance_widget = QWidget()
        layout = QVBoxLayout(performance_widget)
        
        # Processing settings
        processing_group = QGroupBox("Processing")
        processing_layout = QGridLayout(processing_group)
        
        # Thread count
        processing_layout.addWidget(QLabel("Worker threads:"), 0, 0)
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 16)
        self.thread_spin.setValue(4)
        processing_layout.addWidget(self.thread_spin, 0, 1)
        
        # Batch size
        processing_layout.addWidget(QLabel("Batch size:"), 1, 0)
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(10, 1000)
        self.batch_spin.setValue(100)
        processing_layout.addWidget(self.batch_spin, 1, 1)
        
        layout.addWidget(processing_group)
        
        # Memory settings
        memory_group = QGroupBox("Memory")
        memory_layout = QGridLayout(memory_group)
        
        # Cache size
        memory_layout.addWidget(QLabel("Cache size (MB):"), 0, 0)
        self.cache_spin = QSpinBox()
        self.cache_spin.setRange(50, 2000)
        self.cache_spin.setValue(500)
        memory_layout.addWidget(self.cache_spin, 0, 1)
        
        # Enable caching
        self.enable_cache_check = QCheckBox("Enable image caching")
        self.enable_cache_check.setChecked(True)
        memory_layout.addWidget(self.enable_cache_check, 1, 0, 1, 2)
        
        layout.addWidget(memory_group)
        layout.addStretch()
        
        self.tab_widget.addTab(performance_widget, "Performance")
    
    def setup_about_tab(self):
        """Setup the about tab with the hidden easter egg."""
        about_widget = QWidget()
        layout = QVBoxLayout(about_widget)
        
        # Title with version
        title = QLabel("Photo Deduplication Tool")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        version = QLabel("Version 1.0.0 (Steps 1-18 Complete)")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: #888; margin-bottom: 20px;")
        layout.addWidget(version)
        
        # Description
        description = QTextEdit()
        description.setReadOnly(True)
        description.setMaximumHeight(150)
        description.setPlainText(
            "A comprehensive tool for finding and managing duplicate photos.\n\n"
            "Features:\n"
            "• Advanced duplicate detection algorithms\n"
            "• EXIF data comparison\n"
            "• Safe deletion with recycle bin support\n"
            "• Comprehensive reporting and export\n"
            "• Intuitive graphical interface\n\n"
            "Built with Python and PySide6."
        )
        layout.addWidget(description)
        
        # Credits section with the hidden easter egg
        credits_frame = QFrame()
        credits_layout = QHBoxLayout(credits_frame)
        credits_layout.setContentsMargins(10, 10, 10, 10)
        
        credits_text = QLabel("© 2025 Photo Deduplication Tool")
        credits_text.setStyleSheet("color: #888;")
        credits_layout.addWidget(credits_text)
        
        # Add some spacing to make the button placement look accidental
        credits_layout.addStretch()
        
        # This is the secret easter egg button - hidden in plain sight!
        # It looks like a decorative element or UI glitch
        self.secret_button = SecretEasterEggButton()
        credits_layout.addWidget(self.secret_button)
        
        # Add a tiny bit more space to make it look natural
        credits_layout.addSpacing(5)
        
        layout.addWidget(credits_frame)
        layout.addStretch()
        
        self.tab_widget.addTab(about_widget, "About")
    
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
                padding: 5px 15px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #555;
                border-color: #777;
            }
            QPushButton:pressed {
                background-color: #333;
            }
            QComboBox, QSpinBox {
                background-color: #444;
                color: white;
                border: 1px solid #666;
                border-radius: 3px;
                padding: 3px;
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
            }
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #444;
                border: 1px solid #666;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border: 1px solid #005a9e;
            }
            QTextEdit {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
            }
            QLabel {
                color: white;
            }
        """)
    
    def apply_settings(self):
        """Apply the current settings."""
        settings = self.get_settings()
        self.settings_changed.emit(settings)
    
    def get_settings(self):
        """Get the current settings as a dictionary."""
        return {
            'theme': self.theme_combo.currentText(),
            'preview_size': self.preview_size_slider.value(),
            'show_tooltips': self.show_tooltips_check.isChecked(),
            'default_action': self.default_action_combo.currentText(),
            'backup_before_delete': self.backup_check.isChecked(),
            'similarity_threshold': self.similarity_slider.value(),
            'hash_algorithm': self.hash_combo.currentText(),
            'analyze_exif': self.analyze_exif_check.isChecked(),
            'ignore_timestamp': self.ignore_timestamp_check.isChecked(),
            'worker_threads': self.thread_spin.value(),
            'batch_size': self.batch_spin.value(),
            'cache_size': self.cache_spin.value(),
            'enable_cache': self.enable_cache_check.isChecked(),
        }
    
    def accept(self):
        """Accept and apply settings."""
        self.apply_settings()
        super().accept()

def show_settings_dialog(parent=None):
    """Show the settings dialog."""
    if not PYSIDE6_AVAILABLE:
        return None
        
    dialog = SettingsDialog(parent)
    return dialog.exec()