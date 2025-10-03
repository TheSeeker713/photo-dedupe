"""
Accessible Widget Classes for Step 26 - UX polish & accessibility.

This module provides enhanced widget classes with built-in accessibility features:
- Better keyboard navigation
- Larger hit targets
- High-DPI support
- Screen reader compatibility
"""

import logging
from typing import Optional, List

try:
    from PySide6.QtWidgets import (
        QWidget, QPushButton, QCheckBox, QRadioButton, QLabel,
        QLineEdit, QTextEdit, QComboBox, QListWidget, QTreeWidget,
        QSlider, QProgressBar, QFrame, QVBoxLayout, QHBoxLayout,
        QSizePolicy, QApplication
    )
    from PySide6.QtCore import Qt, Signal, QSize, QRect
    from PySide6.QtGui import QFont, QFontMetrics, QPainter, QPen, QColor, QKeyEvent
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    # Define dummy classes for non-Qt environments
    class QWidget: pass
    class QPushButton: pass
    class QCheckBox: pass
    class QRadioButton: pass
    class QLabel: pass
    class QLineEdit: pass
    class QTextEdit: pass
    class QComboBox: pass
    class QListWidget: pass
    class QTreeWidget: pass
    class QSlider: pass
    class QProgressBar: pass
    class QFrame: pass
    class QVBoxLayout: pass
    class QHBoxLayout: pass
    class QSizePolicy: pass
    class QApplication: pass
    class Qt: pass
    class Signal: pass
    class QSize: pass
    class QRect: pass
    class QFont: pass
    class QFontMetrics: pass
    class QPainter: pass
    class QPen: pass
    class QColor: pass
    class QKeyEvent: pass
    Signal = lambda: None


if QT_AVAILABLE:
    from ui.theme_manager import get_theme_manager
    from ui.accessibility import get_accessibility_helper, AccessibilityAttributes, AccessibilityRole
    
    class AccessibleWidget(QWidget):
        """Base widget class with accessibility enhancements."""
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.theme_manager = get_theme_manager()
            self.accessibility_helper = get_accessibility_helper()
            self.logger = logging.getLogger(__name__)
            
            # Accessibility properties
            self.focus_outline_enabled = True
            self.high_dpi_aware = True
            
            # Enable focus by default for interactive widgets
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            
            # Apply theme
            self.apply_accessibility_theme()
        
        def apply_accessibility_theme(self):
            """Apply accessibility-friendly theme to this widget."""
            if not self.theme_manager:
                return
            
            # Get accessible font
            font = self.theme_manager.get_accessible_font()
            if font:
                self.setFont(font)
            
            # Apply accessible stylesheet
            stylesheet = self.theme_manager.create_accessible_stylesheet()
            if stylesheet:
                self.setStyleSheet(stylesheet)
        
        def set_accessible_properties(self, attributes: AccessibilityAttributes):
            """Set accessibility properties for this widget."""
            self.accessibility_helper.set_accessible_attributes(self, attributes)
        
        def paintEvent(self, event):
            """Override paint event to draw focus indicators."""
            super().paintEvent(event)
            
            # Draw enhanced focus outline
            if self.focus_outline_enabled and self.hasFocus():
                self.draw_focus_outline()
        
        def draw_focus_outline(self):
            """Draw enhanced focus outline."""
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Get focus color from theme
            colors = self.theme_manager.get_theme_colors()
            focus_color = colors.get('focus_outline', QColor(0, 120, 215))
            
            # Draw outline
            pen = QPen(focus_color, 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
        
        def sizeHint(self):
            """Return size hint with high-DPI awareness."""
            base_size = super().sizeHint()
            
            if self.high_dpi_aware:
                scaled_size = self.theme_manager.get_scaled_size(max(base_size.width(), base_size.height()))
                return QSize(scaled_size, scaled_size)
            
            return base_size
    
    
    class AccessibleButton(QPushButton):
        """Enhanced button with accessibility features."""
        
        def __init__(self, text="", parent=None):
            super().__init__(text, parent)
            self.theme_manager = get_theme_manager()
            self.accessibility_helper = get_accessibility_helper()
            
            # Set up accessibility
            self.setup_accessibility()
        
        def setup_accessibility(self):
            """Set up accessibility features."""
            # Set minimum size for better hit target
            self.setMinimumHeight(40)  # Larger than default 32px
            self.setMinimumWidth(100)
            
            # Make accessible
            self.accessibility_helper.make_button_accessible(
                self,
                label=self.text(),
                help_text=f"Button: {self.text()}"
            )
            
            # Enable keyboard activation
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        def sizeHint(self):
            """Return size hint with accessibility considerations."""
            base_size = super().sizeHint()
            
            # Ensure minimum accessible size
            min_width = max(100, base_size.width())
            min_height = max(40, base_size.height())
            
            # Scale for high DPI
            if self.theme_manager:
                min_height = self.theme_manager.get_scaled_size(min_height)
                min_width = self.theme_manager.get_scaled_size(min_width)
            
            return QSize(min_width, min_height)
        
        def keyPressEvent(self, event: QKeyEvent):
            """Handle keyboard events for accessibility."""
            # Activate button with Enter or Space
            if event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space]:
                if self.isEnabled():
                    self.click()
                event.accept()
                return
            
            super().keyPressEvent(event)
    
    
    class AccessibleCheckBox(QCheckBox):
        """Enhanced checkbox with accessibility features."""
        
        def __init__(self, text="", parent=None):
            super().__init__(text, parent)
            self.theme_manager = get_theme_manager()
            self.accessibility_helper = get_accessibility_helper()
            
            # Set up accessibility
            self.setup_accessibility()
        
        def setup_accessibility(self):
            """Set up accessibility features."""
            # Increase hit target size
            self.setMinimumHeight(32)
            
            # Add spacing for easier clicking
            self.setStyleSheet("""
                QCheckBox {
                    spacing: 8px;
                    padding: 4px;
                }
                QCheckBox::indicator {
                    width: 24px;
                    height: 24px;
                }
            """)
            
            # Make accessible
            self.accessibility_helper.make_checkbox_accessible(
                self,
                label=self.text(),
                help_text=f"Checkbox: {self.text()}"
            )
        
        def sizeHint(self):
            """Return size hint with accessibility considerations."""
            base_size = super().sizeHint()
            
            # Ensure minimum accessible height
            min_height = max(32, base_size.height())
            
            # Scale for high DPI
            if self.theme_manager:
                min_height = self.theme_manager.get_scaled_size(min_height)
            
            return QSize(base_size.width(), min_height)
    
    
    class AccessibleLabel(QLabel):
        """Enhanced label with accessibility features."""
        
        def __init__(self, text="", parent=None):
            super().__init__(text, parent)
            self.theme_manager = get_theme_manager()
            self.accessibility_helper = get_accessibility_helper()
            self.buddy_widget = None
            
            # Set up accessibility
            self.setup_accessibility()
        
        def setup_accessibility(self):
            """Set up accessibility features."""
            # Set accessible font
            if self.theme_manager:
                font = self.theme_manager.get_accessible_font()
                if font:
                    self.setFont(font)
            
            # Set accessibility attributes
            self.accessibility_helper.set_accessible_attributes(
                self,
                AccessibilityAttributes(
                    role=AccessibilityRole.LABEL,
                    label=self.text()
                )
            )
        
        def setBuddy(self, widget):
            """Set buddy widget for label."""
            super().setBuddy(widget)
            self.buddy_widget = widget
            
            # Update accessibility relationship
            if widget:
                widget.setAccessibleName(self.text())
                self.setAccessibleDescription(f"Label for {widget.__class__.__name__}")
    
    
    class AccessibleLineEdit(QLineEdit):
        """Enhanced line edit with accessibility features."""
        
        def __init__(self, text="", parent=None):
            super().__init__(text, parent)
            self.theme_manager = get_theme_manager()
            self.accessibility_helper = get_accessibility_helper()
            self.is_required = False
            
            # Set up accessibility
            self.setup_accessibility()
        
        def setup_accessibility(self):
            """Set up accessibility features."""
            # Set minimum height for better usability
            self.setMinimumHeight(36)
            
            # Make accessible
            self.accessibility_helper.make_input_accessible(
                self,
                help_text="Text input field"
            )
        
        def set_required(self, required: bool):
            """Set whether this field is required."""
            self.is_required = required
            
            # Update accessibility attributes
            self.accessibility_helper.set_accessible_attributes(
                self,
                AccessibilityAttributes(
                    role=AccessibilityRole.TEXTBOX,
                    required=required,
                    help_text="Required field" if required else "Optional field"
                )
            )
            
            # Visual indication
            if required:
                self.setProperty("required", True)
                self.style().unpolish(self)
                self.style().polish(self)
        
        def sizeHint(self):
            """Return size hint with accessibility considerations."""
            base_size = super().sizeHint()
            
            # Ensure minimum accessible height
            min_height = max(36, base_size.height())
            
            # Scale for high DPI
            if self.theme_manager:
                min_height = self.theme_manager.get_scaled_size(min_height)
            
            return QSize(base_size.width(), min_height)
    
    
    class AccessibleComboBox(QComboBox):
        """Enhanced combo box with accessibility features."""
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.theme_manager = get_theme_manager()
            self.accessibility_helper = get_accessibility_helper()
            
            # Set up accessibility
            self.setup_accessibility()
        
        def setup_accessibility(self):
            """Set up accessibility features."""
            # Set minimum height
            self.setMinimumHeight(36)
            
            # Make accessible
            self.accessibility_helper.set_accessible_attributes(
                self,
                AccessibilityAttributes(
                    role=AccessibilityRole.COMBOBOX,
                    help_text="Dropdown selection"
                )
            )
        
        def sizeHint(self):
            """Return size hint with accessibility considerations."""
            base_size = super().sizeHint()
            
            # Ensure minimum accessible height
            min_height = max(36, base_size.height())
            
            # Scale for high DPI
            if self.theme_manager:
                min_height = self.theme_manager.get_scaled_size(min_height)
            
            return QSize(base_size.width(), min_height)
        
        def keyPressEvent(self, event: QKeyEvent):
            """Handle keyboard events for accessibility."""
            # Allow arrow keys to change selection when not editable
            if not self.isEditable() and event.key() in [Qt.Key.Key_Up, Qt.Key.Key_Down]:
                if event.key() == Qt.Key.Key_Up:
                    new_index = max(0, self.currentIndex() - 1)
                else:
                    new_index = min(self.count() - 1, self.currentIndex() + 1)
                
                self.setCurrentIndex(new_index)
                event.accept()
                return
            
            super().keyPressEvent(event)
    
    
    class AccessibleListWidget(QListWidget):
        """Enhanced list widget with accessibility features."""
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.theme_manager = get_theme_manager()
            self.accessibility_helper = get_accessibility_helper()
            
            # Set up accessibility
            self.setup_accessibility()
        
        def setup_accessibility(self):
            """Set up accessibility features."""
            # Set item height for better touch targets
            if self.itemDelegate():
                self.itemDelegate().sizeHint = lambda option, index: QSize(
                    self.itemDelegate().sizeHint(option, index).width(),
                    max(40, self.itemDelegate().sizeHint(option, index).height())
                )
            
            # Make accessible
            self.accessibility_helper.set_accessible_attributes(
                self,
                AccessibilityAttributes(
                    role=AccessibilityRole.LISTBOX,
                    help_text="List of items"
                )
            )
            
            # Enable keyboard navigation
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        def keyPressEvent(self, event: QKeyEvent):
            """Handle keyboard events for accessibility."""
            # Enhanced navigation
            if event.key() == Qt.Key.Key_Home:
                self.setCurrentRow(0)
                event.accept()
                return
            elif event.key() == Qt.Key.Key_End:
                self.setCurrentRow(self.count() - 1)
                event.accept()
                return
            elif event.key() == Qt.Key.Key_PageUp:
                new_row = max(0, self.currentRow() - 10)
                self.setCurrentRow(new_row)
                event.accept()
                return
            elif event.key() == Qt.Key.Key_PageDown:
                new_row = min(self.count() - 1, self.currentRow() + 10)
                self.setCurrentRow(new_row)
                event.accept()
                return
            
            super().keyPressEvent(event)
    
    
    class AccessibleFrame(QFrame):
        """Enhanced frame with accessibility features."""
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.theme_manager = get_theme_manager()
            self.accessibility_helper = get_accessibility_helper()
            
            # Set up accessibility
            self.setup_accessibility()
        
        def setup_accessibility(self):
            """Set up accessibility features."""
            # Apply accessible styling
            colors = self.theme_manager.get_theme_colors()
            if colors:
                self.setStyleSheet(f"""
                    QFrame {{
                        border: 1px solid {colors.get('border', '#ccc').name()};
                        border-radius: 4px;
                        padding: 8px;
                    }}
                """)
    
    
    class AccessibleProgressBar(QProgressBar):
        """Enhanced progress bar with accessibility features."""
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.theme_manager = get_theme_manager()
            self.accessibility_helper = get_accessibility_helper()
            
            # Set up accessibility
            self.setup_accessibility()
        
        def setup_accessibility(self):
            """Set up accessibility features."""
            # Set minimum height
            self.setMinimumHeight(28)
            
            # Make accessible
            self.accessibility_helper.set_accessible_attributes(
                self,
                AccessibilityAttributes(
                    role=AccessibilityRole.PROGRESSBAR,
                    help_text="Progress indicator"
                )
            )
        
        def setValue(self, value):
            """Set value and update accessibility."""
            super().setValue(value)
            
            # Update accessible description with current progress
            if self.maximum() > 0:
                percentage = (value / self.maximum()) * 100
                self.setAccessibleDescription(f"Progress: {percentage:.0f}% complete")


def create_accessible_layout(widgets: List[QWidget], orientation='vertical') -> QVBoxLayout:
    """Create an accessible layout with proper spacing and focus order."""
    if not QT_AVAILABLE:
        return None
    
    if orientation == 'vertical':
        layout = QVBoxLayout()
    else:
        layout = QHBoxLayout()
    
    # Add widgets with accessible spacing
    for widget in widgets:
        layout.addWidget(widget)
        
        # Set focus policy if not already set
        if widget.focusPolicy() == Qt.FocusPolicy.NoFocus and hasattr(widget, 'setFocusPolicy'):
            # Make interactive widgets focusable
            if isinstance(widget, (QPushButton, QCheckBox, QLineEdit, QComboBox)):
                widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    # Set proper spacing
    layout.setSpacing(12)  # Accessible spacing
    layout.setContentsMargins(16, 16, 16, 16)  # Accessible margins
    
    return layout