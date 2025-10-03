"""
Accessibility Utilities for Step 26 - UX polish & accessibility.

This module provides utilities for improving accessibility including:
- Keyboard navigation helpers
- Screen reader support
- Focus management
- ARIA-like attributes for Qt widgets
- Accessibility testing utilities
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Union, Callable
from dataclasses import dataclass

try:
    from PySide6.QtWidgets import (
        QWidget, QApplication, QShortcut, QLabel, QAbstractButton,
        QCheckBox, QRadioButton, QPushButton, QLineEdit, QTextEdit,
        QComboBox, QListWidget, QTreeWidget, QTableWidget, QTabWidget,
        QSlider, QProgressBar, QSpinBox, QDoubleSpinBox
    )
    from PySide6.QtCore import Qt, QObject, Signal, QEvent, QTimer
    from PySide6.QtGui import QKeySequence, QAccessible, QKeyEvent
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    # Define dummy classes for non-Qt environments
    class QWidget: pass
    class QObject: pass
    class QLabel: pass
    class QAbstractButton: pass
    class QCheckBox: pass
    class QRadioButton: pass
    class QPushButton: pass
    class QLineEdit: pass
    class QTextEdit: pass
    class QComboBox: pass
    class QListWidget: pass
    class QTreeWidget: pass
    class QTableWidget: pass
    class QTabWidget: pass
    class QSlider: pass
    class QProgressBar: pass
    class QSpinBox: pass
    class QDoubleSpinBox: pass
    class QShortcut: pass
    class QApplication: pass
    class Qt: pass
    class QEvent: pass
    class QTimer: pass
    class QKeySequence: pass
    class QAccessible: pass
    class QKeyEvent: pass
    Signal = lambda: None


class AccessibilityRole(Enum):
    """Accessibility roles for UI elements."""
    BUTTON = "button"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    TEXTBOX = "textbox"
    LABEL = "label"
    LISTBOX = "listbox"
    COMBOBOX = "combobox"
    SLIDER = "slider"
    PROGRESSBAR = "progressbar"
    TAB = "tab"
    TABPANEL = "tabpanel"
    MENU = "menu"
    MENUITEM = "menuitem"
    DIALOG = "dialog"
    ALERT = "alert"


@dataclass
class AccessibilityAttributes:
    """Accessibility attributes for UI elements."""
    role: Optional[AccessibilityRole] = None
    label: Optional[str] = None
    description: Optional[str] = None
    help_text: Optional[str] = None
    shortcut: Optional[str] = None
    required: bool = False
    invalid: bool = False
    expanded: Optional[bool] = None
    selected: Optional[bool] = None
    level: Optional[int] = None


class KeyboardNavigationManager(QObject if QT_AVAILABLE else object):
    """Manages keyboard navigation for improved accessibility."""
    
    focus_changed = Signal(QWidget) if QT_AVAILABLE else None
    
    def __init__(self, parent_widget: QWidget = None):
        if QT_AVAILABLE:
            super().__init__()
        
        self.logger = logging.getLogger(__name__)
        self.parent_widget = parent_widget
        self.focusable_widgets = []
        self.current_focus_index = -1
        self.navigation_enabled = True
        
        # Install keyboard shortcuts
        if QT_AVAILABLE and parent_widget:
            self._install_shortcuts()
    
    def _install_shortcuts(self):
        """Install keyboard shortcuts for navigation."""
        if not QT_AVAILABLE:
            return
        
        # Tab navigation (supplementary to default)
        self.tab_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Tab), self.parent_widget)
        self.tab_shortcut.activated.connect(self.focus_next)
        
        self.shift_tab_shortcut = QShortcut(QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_Tab), self.parent_widget)
        self.shift_tab_shortcut.activated.connect(self.focus_previous)
        
        # Arrow key navigation for lists and grids
        self.up_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Up), self.parent_widget)
        self.up_shortcut.activated.connect(lambda: self.navigate_list(-1))
        
        self.down_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Down), self.parent_widget)
        self.down_shortcut.activated.connect(lambda: self.navigate_list(1))
        
        # Home/End navigation
        self.home_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Home), self.parent_widget)
        self.home_shortcut.activated.connect(self.focus_first)
        
        self.end_shortcut = QShortcut(QKeySequence(Qt.Key.Key_End), self.parent_widget)
        self.end_shortcut.activated.connect(self.focus_last)
        
        # Escape key for dialogs
        self.escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self.parent_widget)
        self.escape_shortcut.activated.connect(self._handle_escape)
    
    def register_focusable_widgets(self, widgets: List[QWidget]):
        """Register widgets for keyboard navigation."""
        self.focusable_widgets = [w for w in widgets if w and w.isEnabled() and w.isVisible()]
        self.current_focus_index = -1
        
        # Find currently focused widget
        if QT_AVAILABLE:
            focused = QApplication.focusWidget()
            if focused in self.focusable_widgets:
                self.current_focus_index = self.focusable_widgets.index(focused)
        
        self.logger.debug(f"Registered {len(self.focusable_widgets)} focusable widgets")
    
    def focus_next(self):
        """Focus the next widget in the navigation order."""
        if not self.navigation_enabled or not self.focusable_widgets:
            return
        
        self.current_focus_index = (self.current_focus_index + 1) % len(self.focusable_widgets)
        self._set_focus_to_current()
    
    def focus_previous(self):
        """Focus the previous widget in the navigation order."""
        if not self.navigation_enabled or not self.focusable_widgets:
            return
        
        self.current_focus_index = (self.current_focus_index - 1) % len(self.focusable_widgets)
        self._set_focus_to_current()
    
    def focus_first(self):
        """Focus the first widget in the navigation order."""
        if not self.navigation_enabled or not self.focusable_widgets:
            return
        
        self.current_focus_index = 0
        self._set_focus_to_current()
    
    def focus_last(self):
        """Focus the last widget in the navigation order."""
        if not self.navigation_enabled or not self.focusable_widgets:
            return
        
        self.current_focus_index = len(self.focusable_widgets) - 1
        self._set_focus_to_current()
    
    def navigate_list(self, direction: int):
        """Navigate within list-like widgets using arrow keys."""
        if not QT_AVAILABLE:
            return
        
        focused = QApplication.focusWidget()
        if not focused:
            return
        
        # Handle different widget types
        if isinstance(focused, QListWidget):
            current_row = focused.currentRow()
            new_row = max(0, min(focused.count() - 1, current_row + direction))
            focused.setCurrentRow(new_row)
        
        elif isinstance(focused, QTreeWidget):
            current_item = focused.currentItem()
            if current_item:
                if direction > 0:
                    next_item = focused.itemBelow(current_item)
                else:
                    next_item = focused.itemAbove(current_item)
                
                if next_item:
                    focused.setCurrentItem(next_item)
        
        elif isinstance(focused, QComboBox):
            if focused.isEditable():
                return  # Let default behavior handle editable combo boxes
            
            current_index = focused.currentIndex()
            new_index = max(0, min(focused.count() - 1, current_index + direction))
            focused.setCurrentIndex(new_index)
    
    def _set_focus_to_current(self):
        """Set focus to the current widget in the navigation order."""
        if (0 <= self.current_focus_index < len(self.focusable_widgets)):
            widget = self.focusable_widgets[self.current_focus_index]
            if widget and widget.isEnabled() and widget.isVisible():
                widget.setFocus(Qt.FocusReason.TabFocusReason)
                
                if self.focus_changed:
                    self.focus_changed.emit(widget)
    
    def _handle_escape(self):
        """Handle escape key press."""
        if not QT_AVAILABLE:
            return
        
        # Close dialogs or return focus to main window
        focused = QApplication.focusWidget()
        if focused:
            # Find parent dialog
            parent = focused.parent()
            while parent:
                if hasattr(parent, 'close') and hasattr(parent, 'setModal'):
                    parent.close()
                    return
                parent = parent.parent()
    
    def set_navigation_enabled(self, enabled: bool):
        """Enable or disable keyboard navigation."""
        self.navigation_enabled = enabled


class AccessibilityHelper:
    """Helper class for adding accessibility features to widgets."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.widget_attributes = {}
    
    def set_accessible_attributes(self, widget: QWidget, attributes: AccessibilityAttributes):
        """Set accessibility attributes for a widget."""
        if not QT_AVAILABLE or not widget:
            return
        
        self.widget_attributes[widget] = attributes
        
        # Set accessible name and description
        if attributes.label:
            widget.setAccessibleName(attributes.label)
        
        if attributes.description:
            widget.setAccessibleDescription(attributes.description)
        
        # Set tooltip with help text
        if attributes.help_text:
            widget.setToolTip(attributes.help_text)
        
        # Set shortcut if provided
        if attributes.shortcut and hasattr(widget, 'setShortcut'):
            widget.setShortcut(QKeySequence(attributes.shortcut))
        
        # Set additional properties for screen readers
        if attributes.required:
            widget.setProperty("required", True)
        
        if attributes.invalid:
            widget.setProperty("invalid", True)
            widget.setProperty("aria-invalid", "true")
        
        # Role-specific setup
        self._setup_role_specific_attributes(widget, attributes)
    
    def _setup_role_specific_attributes(self, widget: QWidget, attributes: AccessibilityAttributes):
        """Set up role-specific accessibility attributes."""
        if not attributes.role:
            return
        
        # Set ARIA-like properties
        widget.setProperty("role", attributes.role.value)
        
        if attributes.role == AccessibilityRole.BUTTON:
            if hasattr(widget, 'clicked'):
                # Ensure button is activatable with Enter/Space
                widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        elif attributes.role == AccessibilityRole.CHECKBOX:
            if attributes.selected is not None:
                widget.setProperty("aria-checked", str(attributes.selected).lower())
        
        elif attributes.role == AccessibilityRole.TEXTBOX:
            if attributes.required:
                widget.setProperty("aria-required", "true")
            if attributes.invalid:
                widget.setProperty("aria-invalid", "true")
        
        elif attributes.role == AccessibilityRole.LISTBOX:
            if hasattr(widget, 'setSelectionMode'):
                # Ensure proper selection behavior
                pass
        
        elif attributes.role in [AccessibilityRole.TAB, AccessibilityRole.TABPANEL]:
            if attributes.selected is not None:
                widget.setProperty("aria-selected", str(attributes.selected).lower())
            if attributes.expanded is not None:
                widget.setProperty("aria-expanded", str(attributes.expanded).lower())
    
    def create_label_for_widget(self, widget: QWidget, label_text: str, 
                               shortcut_key: str = None) -> QLabel:
        """Create an accessible label for a widget."""
        if not QT_AVAILABLE:
            return None
        
        label = QLabel(label_text)
        label.setBuddy(widget)
        
        # Add shortcut if provided
        if shortcut_key:
            label.setText(f"&{shortcut_key}{label_text[1:]}" if label_text else f"&{shortcut_key}")
        
        # Set accessibility attributes
        self.set_accessible_attributes(label, AccessibilityAttributes(
            role=AccessibilityRole.LABEL,
            label=label_text
        ))
        
        return label
    
    def make_button_accessible(self, button: QAbstractButton, 
                             label: str = None, shortcut: str = None,
                             help_text: str = None) -> QAbstractButton:
        """Make a button fully accessible."""
        if not QT_AVAILABLE:
            return button
        
        # Set up accessibility attributes
        attributes = AccessibilityAttributes(
            role=AccessibilityRole.BUTTON,
            label=label or button.text(),
            help_text=help_text,
            shortcut=shortcut
        )
        
        self.set_accessible_attributes(button, attributes)
        
        # Ensure proper focus behavior
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Add keyboard activation
        def handle_key_press(event):
            if event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space]:
                if button.isEnabled():
                    button.click()
                event.accept()
                return True
            return False
        
        button.keyPressEvent = lambda event: (
            handle_key_press(event) or 
            QAbstractButton.keyPressEvent(button, event)
        )
        
        return button
    
    def make_checkbox_accessible(self, checkbox: QCheckBox,
                                label: str = None, help_text: str = None) -> QCheckBox:
        """Make a checkbox fully accessible with larger hit target."""
        if not QT_AVAILABLE:
            return checkbox
        
        # Set up accessibility attributes
        attributes = AccessibilityAttributes(
            role=AccessibilityRole.CHECKBOX,
            label=label or checkbox.text(),
            help_text=help_text,
            selected=checkbox.isChecked()
        )
        
        self.set_accessible_attributes(checkbox, attributes)
        
        # Increase hit target size
        checkbox.setMinimumHeight(32)
        checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 8px;
                padding: 4px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        
        # Update accessibility state when checked state changes
        def update_checked_state():
            checkbox.setProperty("aria-checked", str(checkbox.isChecked()).lower())
        
        checkbox.toggled.connect(update_checked_state)
        
        return checkbox
    
    def make_input_accessible(self, input_widget: Union[QLineEdit, QTextEdit],
                            label: str = None, help_text: str = None,
                            required: bool = False) -> Union[QLineEdit, QTextEdit]:
        """Make an input widget fully accessible."""
        if not QT_AVAILABLE:
            return input_widget
        
        # Set up accessibility attributes
        attributes = AccessibilityAttributes(
            role=AccessibilityRole.TEXTBOX,
            label=label,
            help_text=help_text,
            required=required
        )
        
        self.set_accessible_attributes(input_widget, attributes)
        
        # Add validation state updates
        if hasattr(input_widget, 'textChanged'):
            def update_validation_state():
                # This would be connected to actual validation logic
                text = input_widget.text() if hasattr(input_widget, 'text') else input_widget.toPlainText()
                is_invalid = required and not text.strip()
                
                input_widget.setProperty("invalid", is_invalid)
                input_widget.setProperty("aria-invalid", str(is_invalid).lower())
                
                # Update visual state
                if is_invalid:
                    input_widget.setStyleSheet("border: 2px solid red;")
                else:
                    input_widget.setStyleSheet("")
            
            input_widget.textChanged.connect(update_validation_state)
        
        return input_widget


class AccessibilityTester:
    """Utility class for testing accessibility compliance."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def run_accessibility_audit(self, widget: QWidget) -> Dict[str, List[str]]:
        """Run basic accessibility audit on a widget tree."""
        if not QT_AVAILABLE:
            return {}
        
        issues = {
            'critical': [],
            'warning': [],
            'info': []
        }
        
        # Recursively check all widgets
        self._audit_widget_tree(widget, issues)
        
        return issues
    
    def _audit_widget_tree(self, widget: QWidget, issues: Dict[str, List[str]]):
        """Recursively audit widget tree for accessibility issues."""
        if not widget:
            return
        
        widget_name = widget.objectName() or widget.__class__.__name__
        
        # Check for missing accessible names
        if not widget.accessibleName() and self._needs_accessible_name(widget):
            issues['warning'].append(f"{widget_name}: Missing accessible name")
        
        # Check for missing tooltips on interactive elements
        if not widget.toolTip() and self._is_interactive(widget):
            issues['info'].append(f"{widget_name}: Consider adding tooltip for help")
        
        # Check for keyboard focus
        if self._is_interactive(widget) and widget.focusPolicy() == Qt.FocusPolicy.NoFocus:
            issues['critical'].append(f"{widget_name}: Interactive element not keyboard accessible")
        
        # Check button sizes
        if isinstance(widget, QAbstractButton) and widget.size().height() < 32:
            issues['warning'].append(f"{widget_name}: Button height below recommended 32px")
        
        # Check color contrast (basic check)
        if hasattr(widget, 'palette'):
            palette = widget.palette()
            bg_color = palette.color(palette.ColorRole.Window)
            text_color = palette.color(palette.ColorRole.WindowText)
            
            # Simple contrast check (should be more sophisticated)
            if self._calculate_contrast_ratio(bg_color, text_color) < 4.5:
                issues['warning'].append(f"{widget_name}: Low color contrast ratio")
        
        # Recursively check children
        for child in widget.findChildren(QWidget):
            if child.parent() == widget:  # Only direct children
                self._audit_widget_tree(child, issues)
    
    def _needs_accessible_name(self, widget: QWidget) -> bool:
        """Check if widget needs an accessible name."""
        return isinstance(widget, (
            QAbstractButton, QLineEdit, QTextEdit, QComboBox,
            QListWidget, QTreeWidget, QTableWidget, QSlider,
            QSpinBox, QDoubleSpinBox
        ))
    
    def _is_interactive(self, widget: QWidget) -> bool:
        """Check if widget is interactive."""
        return isinstance(widget, (
            QAbstractButton, QLineEdit, QTextEdit, QComboBox,
            QListWidget, QTreeWidget, QTableWidget, QSlider,
            QSpinBox, QDoubleSpinBox, QTabWidget
        ))
    
    def _calculate_contrast_ratio(self, color1, color2) -> float:
        """Calculate contrast ratio between two colors."""
        if not QT_AVAILABLE:
            return 0.0
        
        # Simple luminance calculation
        def luminance(color):
            r, g, b = color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0
            
            # Convert to linear RGB
            def to_linear(c):
                return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            
            r_lin, g_lin, b_lin = to_linear(r), to_linear(g), to_linear(b)
            
            # Calculate luminance
            return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin
        
        l1 = luminance(color1)
        l2 = luminance(color2)
        
        # Ensure l1 is the lighter color
        if l1 < l2:
            l1, l2 = l2, l1
        
        # Calculate contrast ratio
        return (l1 + 0.05) / (l2 + 0.05)


# Global instances
_keyboard_nav_manager = None
_accessibility_helper = None
_accessibility_tester = None

def get_keyboard_navigation_manager(parent_widget: QWidget = None) -> KeyboardNavigationManager:
    """Get or create keyboard navigation manager."""
    global _keyboard_nav_manager
    if _keyboard_nav_manager is None:
        _keyboard_nav_manager = KeyboardNavigationManager(parent_widget)
    return _keyboard_nav_manager

def get_accessibility_helper() -> AccessibilityHelper:
    """Get or create accessibility helper."""
    global _accessibility_helper
    if _accessibility_helper is None:
        _accessibility_helper = AccessibilityHelper()
    return _accessibility_helper

def get_accessibility_tester() -> AccessibilityTester:
    """Get or create accessibility tester."""
    global _accessibility_tester
    if _accessibility_tester is None:
        _accessibility_tester = AccessibilityTester()
    return _accessibility_tester