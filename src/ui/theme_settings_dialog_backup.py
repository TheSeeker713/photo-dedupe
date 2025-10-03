"""
Theme Settings Dialog for Step 26 - UX polish & accessibility.

This module provides a settings dialog for theme and accessibility options.
"""

import logging
from typing import Optional

try:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QComboBox, QCheckBox, QGroupBox, QSlider, QSpinBox,
        QColorDialog, QTabWidget, QWidget, QFormLayout,
        QMessageBox, QFrame
    )
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QFont, QColor, QPalette
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    # Define dummy classes for non-Qt environments
    class QDialog: pass
    class QVBoxLayout: pass
    class QHBoxLayout: pass
    class QLabel: pass
    class QPushButton: pass
    class QComboBox: pass
    class QCheckBox: pass
    class QGroupBox: pass
    class QSlider: pass
    class QSpinBox: pass
    class QColorDialog: pass
    class QTabWidget: pass
    class QWidget: pass
    class QFormLayout: pass
    class QMessageBox: pass
    class QFrame: pass
    class Qt: pass
    class QFont: pass
    class QColor: pass
    class QPalette: pass
    Signal = lambda: None


if QT_AVAILABLE:
    from ui.theme_manager import ThemeManager, ThemeMode, get_theme_manager
    from ui.accessibility import AccessibilityHelper, get_accessibility_helper
    
    class ThemeSettingsDialog(QDialog):
        """Dialog for theme and accessibility settings."""
        
        theme_changed = Signal(str)
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Theme & Accessibility Settings")
            self.setModal(True)
            self.setMinimumSize(500, 400)
            
            self.theme_manager = get_theme_manager()
            self.accessibility_helper = get_accessibility_helper()
            
            self.setup_ui()
            self.load_current_settings()
            
            # Apply current theme to dialog
            self.apply_theme()
        
        def setup_ui(self):
            """Set up the dialog UI."""
            layout = QVBoxLayout(self)
            
            # Create tab widget
            self.tab_widget = QTabWidget()
            layout.addWidget(self.tab_widget)
            
            # Theme tab
            self.create_theme_tab()
            
            # Accessibility tab
            self.create_accessibility_tab()
            
            # High DPI tab
            self.create_high_dpi_tab()
            
            # Button layout
            button_layout = QHBoxLayout()
            
            self.preview_button = QPushButton("Preview")
            self.preview_button.clicked.connect(self.preview_changes)
            
            self.reset_button = QPushButton("Reset to Defaults")
            self.reset_button.clicked.connect(self.reset_to_defaults)
            
            self.apply_button = QPushButton("Apply")
            self.apply_button.clicked.connect(self.apply_changes)
            
            self.ok_button = QPushButton("OK")
            self.ok_button.clicked.connect(self.accept_changes)
            self.ok_button.setDefault(True)
            
            self.cancel_button = QPushButton("Cancel")
            self.cancel_button.clicked.connect(self.reject)
            
            button_layout.addWidget(self.preview_button)
            button_layout.addWidget(self.reset_button)
            button_layout.addStretch()
            button_layout.addWidget(self.apply_button)
            button_layout.addWidget(self.ok_button)
            button_layout.addWidget(self.cancel_button)
            
            layout.addLayout(button_layout)
            
            # Make dialog accessible
            self.make_accessible()
        
        def create_theme_tab(self):
            """Create the theme settings tab."""
            theme_widget = QWidget()
            layout = QVBoxLayout(theme_widget)
            
            # Theme selection group
            theme_group = QGroupBox("Theme Selection")
            theme_form = QFormLayout(theme_group)
            
            self.theme_combo = QComboBox()
            self.theme_combo.addItems([
                "System Default",
                "Light Theme", 
                "Dark Theme",
                "High Contrast"
            ])
            self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
            
            theme_form.addRow("Theme:", self.theme_combo)
            layout.addWidget(theme_group)
            
            # Theme preview
            preview_group = QGroupBox("Preview")
            preview_layout = QVBoxLayout(preview_group)
            
            self.preview_frame = QFrame()
            self.preview_frame.setMinimumHeight(100)
            self.preview_frame.setFrameStyle(QFrame.Shape.StyledPanel)
            
            # Sample controls for preview
            preview_controls = QHBoxLayout()
            
            sample_button = QPushButton("Sample Button")
            sample_checkbox = QCheckBox("Sample Checkbox")
            sample_combo = QComboBox()
            sample_combo.addItems(["Option 1", "Option 2", "Option 3"])
            
            preview_controls.addWidget(sample_button)
            preview_controls.addWidget(sample_checkbox)
            preview_controls.addWidget(sample_combo)
            preview_controls.addStretch()
            
            preview_layout.addWidget(self.preview_frame)
            preview_layout.addLayout(preview_controls)
            layout.addWidget(preview_group)
            
            layout.addStretch()
            self.tab_widget.addTab(theme_widget, "Theme")
        
        def create_accessibility_tab(self):
            """Create the accessibility settings tab."""
            access_widget = QWidget()
            layout = QVBoxLayout(access_widget)
            
            # Font settings
            font_group = QGroupBox("Font & Text")
            font_form = QFormLayout(font_group)
            
            self.font_size_spin = QSpinBox()
            self.font_size_spin.setMinimum(8)
            self.font_size_spin.setMaximum(24)
            self.font_size_spin.setValue(9)
            self.font_size_spin.setSuffix(" pt")
            
            font_form.addRow("Font Size:", self.font_size_spin)
            layout.addWidget(font_group)
            
            # Interaction settings
            interaction_group = QGroupBox("Interaction")
            interaction_layout = QVBoxLayout(interaction_group)
            
            self.large_buttons_cb = QCheckBox("Large Button Hit Targets")
            self.large_buttons_cb.setChecked(True)
            
            self.keyboard_nav_cb = QCheckBox("Enhanced Keyboard Navigation")
            self.keyboard_nav_cb.setChecked(True)
            
            self.tooltips_cb = QCheckBox("Show Helpful Tooltips")
            self.tooltips_cb.setChecked(True)
            
            self.focus_indicators_cb = QCheckBox("Enhanced Focus Indicators")
            self.focus_indicators_cb.setChecked(True)
            
            interaction_layout.addWidget(self.large_buttons_cb)
            interaction_layout.addWidget(self.keyboard_nav_cb)
            interaction_layout.addWidget(self.tooltips_cb)
            interaction_layout.addWidget(self.focus_indicators_cb)
            
            layout.addWidget(interaction_group)
            
            # Screen reader settings
            reader_group = QGroupBox("Screen Reader Support")
            reader_layout = QVBoxLayout(reader_group)
            
            self.accessible_labels_cb = QCheckBox("Enhanced Accessible Labels")
            self.accessible_labels_cb.setChecked(True)
            
            self.aria_support_cb = QCheckBox("ARIA-like Attributes")
            self.aria_support_cb.setChecked(True)
            
            reader_layout.addWidget(self.accessible_labels_cb)
            reader_layout.addWidget(self.aria_support_cb)
            
            layout.addWidget(reader_group)
            
            layout.addStretch()
            self.tab_widget.addTab(access_widget, "Accessibility")
        
        def create_high_dpi_tab(self):
            """Create the high DPI settings tab."""
            dpi_widget = QWidget()
            layout = QVBoxLayout(dpi_widget)
            
            # DPI settings
            dpi_group = QGroupBox("High-DPI Display Settings")
            dpi_layout = QVBoxLayout(dpi_group)
            
            self.high_dpi_cb = QCheckBox("Enable High-DPI Scaling")
            self.high_dpi_cb.setChecked(True)
            self.high_dpi_cb.toggled.connect(self.on_high_dpi_changed)
            
            dpi_layout.addWidget(self.high_dpi_cb)
            
            # Scale factor
            scale_form = QFormLayout()
            
            self.scale_slider = QSlider(Qt.Orientation.Horizontal)
            self.scale_slider.setMinimum(100)
            self.scale_slider.setMaximum(300)
            self.scale_slider.setValue(100)
            self.scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
            self.scale_slider.setTickInterval(25)
            self.scale_slider.valueChanged.connect(self.on_scale_changed)
            
            self.scale_label = QLabel("100%")
            
            scale_layout = QHBoxLayout()
            scale_layout.addWidget(self.scale_slider)
            scale_layout.addWidget(self.scale_label)
            
            scale_form.addRow("UI Scale Factor:", scale_layout)
            dpi_layout.addLayout(scale_form)
            
            layout.addWidget(dpi_group)
            
            # DPI information
            info_group = QGroupBox("Display Information")
            info_layout = QFormLayout(info_group)
            
            # Get current display info
            try:
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    screen = app.primaryScreen()
                    if screen:
                        dpi = screen.logicalDotsPerInch()
                        ratio = screen.devicePixelRatio()
                        size = screen.size()
                        
                        info_layout.addRow("Screen DPI:", QLabel(f"{dpi:.1f}"))
                        info_layout.addRow("Pixel Ratio:", QLabel(f"{ratio:.2f}"))
                        info_layout.addRow("Resolution:", QLabel(f"{size.width()}×{size.height()}"))
            except:
                info_layout.addRow("Display Info:", QLabel("Not available"))
            
            layout.addWidget(info_group)
            
            layout.addStretch()
            self.tab_widget.addTab(dpi_widget, "High-DPI")
        
        def make_accessible(self):
            """Make the dialog accessible."""
            # Set accessible names and descriptions
            self.setAccessibleName("Theme and Accessibility Settings")
            self.setAccessibleDescription("Configure appearance and accessibility options")
            
            # Make tabs accessible
            self.tab_widget.setAccessibleName("Settings Categories")
            self.tab_widget.tabBar().setAccessibleName("Settings Tabs")
            
            # Make buttons accessible
            buttons = [
                (self.preview_button, "Preview theme changes", "Alt+P"),
                (self.reset_button, "Reset all settings to defaults", "Alt+R"),
                (self.apply_button, "Apply changes", "Alt+A"),
                (self.ok_button, "Apply changes and close", ""),
                (self.cancel_button, "Cancel and close", "Escape")
            ]
            
            for button, description, shortcut in buttons:
                self.accessibility_helper.make_button_accessible(
                    button, help_text=description, shortcut=shortcut
                )
            
            # Make form controls accessible
            self.accessibility_helper.make_input_accessible(
                self.theme_combo, "Theme selection", "Choose the application theme"
            )
            
            self.accessibility_helper.make_checkbox_accessible(
                self.large_buttons_cb, help_text="Make buttons larger for easier clicking"
            )
            
            self.accessibility_helper.make_checkbox_accessible(
                self.keyboard_nav_cb, help_text="Enable enhanced keyboard navigation"
            )
        
        def load_current_settings(self):
            """Load current settings into the dialog."""
            # Load theme setting
            current_theme = self.theme_manager.get_current_theme()
            theme_index = {
                ThemeMode.SYSTEM: 0,
                ThemeMode.LIGHT: 1,
                ThemeMode.DARK: 2,
                ThemeMode.HIGH_CONTRAST: 3
            }.get(current_theme, 0)
            
            self.theme_combo.setCurrentIndex(theme_index)
            
            # Load font size
            current_font_size = self.theme_manager.get_accessible_font_size()
            self.font_size_spin.setValue(current_font_size)
            
            # Load high DPI setting
            self.high_dpi_cb.setChecked(self.theme_manager.high_dpi_scaling)
        
        def on_theme_changed(self, theme_text: str):
            """Handle theme selection change."""
            self.preview_changes()
        
        def on_high_dpi_changed(self, enabled: bool):
            """Handle high DPI setting change."""
            self.scale_slider.setEnabled(enabled)
            self.scale_label.setEnabled(enabled)
        
        def on_scale_changed(self, value: int):
            """Handle scale factor change."""
            self.scale_label.setText(f"{value}%")
        
        def preview_changes(self):
            """Preview the selected theme."""
            theme_text = self.theme_combo.currentText()
            theme_mode = {
                "System Default": ThemeMode.SYSTEM,
                "Light Theme": ThemeMode.LIGHT,
                "Dark Theme": ThemeMode.DARK,
                "High Contrast": ThemeMode.HIGH_CONTRAST
            }.get(theme_text, ThemeMode.SYSTEM)
            
            # Apply theme to preview frame
            colors = self.theme_manager.get_theme_colors(theme_mode)
            if colors:
                self.preview_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {colors['window'].name()};
                        color: {colors['window_text'].name()};
                        border: 2px solid {colors['border'].name()};
                    }}
                """)
        
        def apply_theme(self):
            """Apply current theme to this dialog."""
            stylesheet = self.theme_manager.create_accessible_stylesheet()
            if stylesheet:
                self.setStyleSheet(stylesheet)
        
        def reset_to_defaults(self):
            """Reset all settings to defaults."""
            reply = QMessageBox.question(
                self, "Reset Settings",
                "Are you sure you want to reset all settings to defaults?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.theme_combo.setCurrentIndex(0)  # System
                self.font_size_spin.setValue(9)
                self.large_buttons_cb.setChecked(True)
                self.keyboard_nav_cb.setChecked(True)
                self.tooltips_cb.setChecked(True)
                self.focus_indicators_cb.setChecked(True)
                self.accessible_labels_cb.setChecked(True)
                self.aria_support_cb.setChecked(True)
                self.high_dpi_cb.setChecked(True)
                self.scale_slider.setValue(100)
        
        def apply_changes(self):
            """Apply the selected settings."""
            # Apply theme
            theme_text = self.theme_combo.currentText()
            theme_mode = {
                "System Default": ThemeMode.SYSTEM,
                "Light Theme": ThemeMode.LIGHT,
                "Dark Theme": ThemeMode.DARK,
                "High Contrast": ThemeMode.HIGH_CONTRAST
            }.get(theme_text, ThemeMode.SYSTEM)
            
            self.theme_manager.set_theme(theme_mode)
            
            # Apply high DPI setting
            self.theme_manager.set_high_dpi_scaling(self.high_dpi_cb.isChecked())
            
            # Emit signal for main application
            self.theme_changed.emit(theme_mode.value)
            
            # Show confirmation
            QMessageBox.information(
                self, "Settings Applied",
                "Theme and accessibility settings have been applied."
            )
        
        def accept_changes(self):
            """Apply changes and close dialog."""
            self.apply_changes()
            self.accept()
        
        def reject(self):
            """Close dialog without applying changes."""
            reply = QMessageBox.question(
                self, "Discard Changes",
                "Are you sure you want to discard your changes?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                super().reject()


    def show_theme_settings_dialog(parent=None):
        """Show the theme settings dialog."""
        dialog = ThemeSettingsDialog(parent)
        return dialog


else:
    # Dummy implementations for when Qt is not available
    class ThemeSettingsDialog:
        """Dummy theme settings dialog."""
        def __init__(self, parent=None):
            pass
    
    def show_theme_settings_dialog(parent=None):
        """Dummy show theme settings dialog."""
        print("Theme settings dialog not available (Qt not available)")
        return None
    dialog = ThemeSettingsDialog(parent)
    return dialog.exec()