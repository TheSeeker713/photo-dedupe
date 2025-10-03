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