"""
Theme Management for Step 26 - UX polish & accessibility.

This module provides comprehensive theme support including:
- Dark/light theme toggle with system detection
- High-contrast mode support
- Custom color schemes
- Accessibility-friendly color choices
- High-DPI scaling support
"""

import logging
from enum import Enum
from typing import Dict, Optional, Tuple
from pathlib import Path

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt, QSettings, Signal, QObject
    from PySide6.QtGui import QPalette, QColor, QFont, QFontMetrics
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QObject = object
    Signal = lambda: None


class ThemeMode(Enum):
    """Available theme modes."""
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"


class ThemeManager(QObject if QT_AVAILABLE else object):
    """Manages application themes and accessibility settings."""
    
    theme_changed = Signal(str) if QT_AVAILABLE else None
    
    def __init__(self):
        if QT_AVAILABLE:
            super().__init__()
        
        self.logger = logging.getLogger(__name__)
        self.settings = QSettings("PhotoDedupe", "Themes") if QT_AVAILABLE else None
        self.current_theme = ThemeMode.SYSTEM
        self.high_dpi_scaling = True
        
        # Color schemes
        self.themes = {
            ThemeMode.LIGHT: self._create_light_theme(),
            ThemeMode.DARK: self._create_dark_theme(),
            ThemeMode.HIGH_CONTRAST: self._create_high_contrast_theme(),
        }
        
        # Load saved preferences
        self._load_theme_settings()
    
    def _create_light_theme(self) -> Dict[str, QColor]:
        """Create light theme color scheme."""
        if not QT_AVAILABLE:
            return {}
        
        return {
            # Base colors
            'window': QColor(240, 240, 240),
            'window_text': QColor(0, 0, 0),
            'base': QColor(255, 255, 255),
            'alternate_base': QColor(245, 245, 245),
            'text': QColor(0, 0, 0),
            'button': QColor(225, 225, 225),
            'button_text': QColor(0, 0, 0),
            'highlight': QColor(0, 120, 215),
            'highlight_text': QColor(255, 255, 255),
            
            # Custom colors
            'primary': QColor(0, 120, 215),
            'secondary': QColor(108, 117, 125),
            'success': QColor(40, 167, 69),
            'warning': QColor(255, 193, 7),
            'danger': QColor(220, 53, 69),
            'info': QColor(23, 162, 184),
            
            # Accessibility colors
            'focus_outline': QColor(0, 120, 215),
            'disabled': QColor(108, 117, 125),
            'border': QColor(206, 212, 218),
            'shadow': QColor(0, 0, 0, 25),
        }
    
    def _create_dark_theme(self) -> Dict[str, QColor]:
        """Create dark theme color scheme."""
        if not QT_AVAILABLE:
            return {}
        
        return {
            # Base colors
            'window': QColor(32, 32, 32),
            'window_text': QColor(255, 255, 255),
            'base': QColor(42, 42, 42),
            'alternate_base': QColor(48, 48, 48),
            'text': QColor(255, 255, 255),
            'button': QColor(64, 64, 64),
            'button_text': QColor(255, 255, 255),
            'highlight': QColor(0, 120, 215),
            'highlight_text': QColor(255, 255, 255),
            
            # Custom colors
            'primary': QColor(100, 170, 255),
            'secondary': QColor(134, 142, 150),
            'success': QColor(72, 187, 120),
            'warning': QColor(255, 220, 60),
            'danger': QColor(248, 81, 73),
            'info': QColor(58, 176, 255),
            
            # Accessibility colors
            'focus_outline': QColor(100, 170, 255),
            'disabled': QColor(108, 117, 125),
            'border': QColor(73, 80, 87),
            'shadow': QColor(0, 0, 0, 50),
        }
    
    def _create_high_contrast_theme(self) -> Dict[str, QColor]:
        """Create high contrast theme for accessibility."""
        if not QT_AVAILABLE:
            return {}
        
        return {
            # Base colors (high contrast)
            'window': QColor(0, 0, 0),
            'window_text': QColor(255, 255, 255),
            'base': QColor(0, 0, 0),
            'alternate_base': QColor(32, 32, 32),
            'text': QColor(255, 255, 255),
            'button': QColor(0, 0, 0),
            'button_text': QColor(255, 255, 255),
            'highlight': QColor(255, 255, 0),
            'highlight_text': QColor(0, 0, 0),
            
            # Custom colors (high contrast)
            'primary': QColor(255, 255, 0),
            'secondary': QColor(128, 128, 128),
            'success': QColor(0, 255, 0),
            'warning': QColor(255, 255, 0),
            'danger': QColor(255, 0, 0),
            'info': QColor(0, 255, 255),
            
            # Accessibility colors
            'focus_outline': QColor(255, 255, 0),
            'disabled': QColor(128, 128, 128),
            'border': QColor(255, 255, 255),
            'shadow': QColor(255, 255, 255, 50),
        }
    
    def _load_theme_settings(self):
        """Load theme settings from storage."""
        if not self.settings:
            return
        
        # Load theme mode
        theme_name = self.settings.value("current_theme", ThemeMode.SYSTEM.value)
        try:
            self.current_theme = ThemeMode(theme_name)
        except ValueError:
            self.current_theme = ThemeMode.SYSTEM
        
        # Load high DPI setting
        self.high_dpi_scaling = self.settings.value("high_dpi_scaling", True, type=bool)
    
    def _save_theme_settings(self):
        """Save theme settings to storage."""
        if not self.settings:
            return
        
        self.settings.setValue("current_theme", self.current_theme.value)
        self.settings.setValue("high_dpi_scaling", self.high_dpi_scaling)
        self.settings.sync()
    
    def set_theme(self, theme_mode: ThemeMode):
        """Set the application theme."""
        if not QT_AVAILABLE:
            return
        
        self.current_theme = theme_mode
        self._save_theme_settings()
        
        # Apply theme to application
        app = QApplication.instance()
        if app:
            self._apply_theme_to_app(app, theme_mode)
        
        # Emit signal for UI updates
        if self.theme_changed:
            self.theme_changed.emit(theme_mode.value)
        
        self.logger.info(f"Theme changed to: {theme_mode.value}")
    
    def _apply_theme_to_app(self, app: QApplication, theme_mode: ThemeMode):
        """Apply theme colors to the application."""
        if theme_mode == ThemeMode.SYSTEM:
            # Use system theme
            app.setPalette(app.style().standardPalette())
            return
        
        # Get theme colors
        colors = self.themes.get(theme_mode, self.themes[ThemeMode.LIGHT])
        
        # Create palette
        palette = QPalette()
        
        # Set palette colors
        palette.setColor(QPalette.ColorRole.Window, colors['window'])
        palette.setColor(QPalette.ColorRole.WindowText, colors['window_text'])
        palette.setColor(QPalette.ColorRole.Base, colors['base'])
        palette.setColor(QPalette.ColorRole.AlternateBase, colors['alternate_base'])
        palette.setColor(QPalette.ColorRole.Text, colors['text'])
        palette.setColor(QPalette.ColorRole.Button, colors['button'])
        palette.setColor(QPalette.ColorRole.ButtonText, colors['button_text'])
        palette.setColor(QPalette.ColorRole.Highlight, colors['highlight'])
        palette.setColor(QPalette.ColorRole.HighlightedText, colors['highlight_text'])
        
        # Apply palette
        app.setPalette(palette)
    
    def get_current_theme(self) -> ThemeMode:
        """Get the current theme mode."""
        return self.current_theme
    
    def get_theme_colors(self, theme_mode: Optional[ThemeMode] = None) -> Dict[str, QColor]:
        """Get colors for a specific theme."""
        if not QT_AVAILABLE:
            return {}
        
        if theme_mode is None:
            theme_mode = self.current_theme
        
        if theme_mode == ThemeMode.SYSTEM:
            # Detect system theme
            app = QApplication.instance()
            if app:
                palette = app.palette()
                # Simple heuristic: if window color is dark, assume dark theme
                window_color = palette.color(QPalette.ColorRole.Window)
                is_dark = window_color.lightness() < 128
                theme_mode = ThemeMode.DARK if is_dark else ThemeMode.LIGHT
            else:
                theme_mode = ThemeMode.LIGHT
        
        return self.themes.get(theme_mode, self.themes[ThemeMode.LIGHT])
    
    def is_dark_theme(self, theme_mode: Optional[ThemeMode] = None) -> bool:
        """Check if the current theme is dark."""
        if theme_mode is None:
            theme_mode = self.current_theme
        
        if theme_mode == ThemeMode.SYSTEM:
            colors = self.get_theme_colors()
            if colors:
                return colors['window'].lightness() < 128
        
        return theme_mode in [ThemeMode.DARK, ThemeMode.HIGH_CONTRAST]
    
    def get_accessible_font_size(self, base_size: int = 9) -> int:
        """Get accessible font size based on system settings."""
        if not QT_AVAILABLE:
            return base_size
        
        app = QApplication.instance()
        if not app:
            return base_size
        
        # Get system font
        system_font = app.font()
        system_size = system_font.pointSize()
        
        # Use larger of base size or system size
        return max(base_size, system_size, 9)  # Minimum 9pt for accessibility
    
    def get_accessible_font(self, base_family: str = "", base_size: int = 9) -> QFont:
        """Get an accessible font with appropriate size."""
        if not QT_AVAILABLE:
            return None
        
        app = QApplication.instance()
        font = app.font() if app else QFont()
        
        if base_family:
            font.setFamily(base_family)
        
        # Set accessible size
        accessible_size = self.get_accessible_font_size(base_size)
        font.setPointSize(accessible_size)
        
        return font
    
    def configure_high_dpi(self):
        """Configure high-DPI support for the application."""
        if not QT_AVAILABLE:
            return
        
        if self.high_dpi_scaling:
            # Enable high-DPI scaling
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
            
            # Set scale factor policy
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
        
        self.logger.info(f"High-DPI scaling: {'enabled' if self.high_dpi_scaling else 'disabled'}")
    
    def set_high_dpi_scaling(self, enabled: bool):
        """Enable or disable high-DPI scaling."""
        self.high_dpi_scaling = enabled
        self._save_theme_settings()
        self.logger.info(f"High-DPI scaling set to: {enabled}")
    
    def get_scaled_size(self, base_size: int) -> int:
        """Get scaled size for high-DPI displays."""
        if not QT_AVAILABLE:
            return base_size
        
        app = QApplication.instance()
        if not app:
            return base_size
        
        # Get device pixel ratio
        screen = app.primaryScreen()
        if screen:
            ratio = screen.devicePixelRatio()
            return int(base_size * ratio)
        
        return base_size
    
    def create_accessible_stylesheet(self) -> str:
        """Create a stylesheet with accessibility improvements."""
        if not QT_AVAILABLE:
            return ""
        
        colors = self.get_theme_colors()
        if not colors:
            return ""
        
        # Get accessible font size
        font_size = self.get_accessible_font_size()
        
        # Create stylesheet
        stylesheet = f"""
        /* Base styling with accessibility improvements */
        QWidget {{
            font-size: {font_size}pt;
            color: {colors['text'].name()};
            background-color: {colors['window'].name()};
        }}
        
        /* Button styling with larger hit targets */
        QPushButton {{
            min-height: 32px;
            min-width: 80px;
            padding: 6px 12px;
            border: 2px solid {colors['border'].name()};
            border-radius: 4px;
            background-color: {colors['button'].name()};
            color: {colors['button_text'].name()};
        }}
        
        QPushButton:hover {{
            background-color: {colors['primary'].name()};
            color: {colors['highlight_text'].name()};
        }}
        
        QPushButton:focus {{
            outline: 2px solid {colors['focus_outline'].name()};
            outline-offset: 2px;
        }}
        
        QPushButton:pressed {{
            background-color: {colors['primary'].name()};
            border: 2px solid {colors['focus_outline'].name()};
        }}
        
        QPushButton:disabled {{
            background-color: {colors['disabled'].name()};
            color: {colors['disabled'].name()};
            border-color: {colors['disabled'].name()};
        }}
        
        /* Checkbox styling with larger hit targets */
        QCheckBox {{
            spacing: 8px;
            min-height: 24px;
        }}
        
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border: 2px solid {colors['border'].name()};
            border-radius: 3px;
            background-color: {colors['base'].name()};
        }}
        
        QCheckBox::indicator:hover {{
            border-color: {colors['primary'].name()};
        }}
        
        QCheckBox::indicator:focus {{
            outline: 2px solid {colors['focus_outline'].name()};
            outline-offset: 2px;
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {colors['primary'].name()};
            border-color: {colors['primary'].name()};
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
        }}
        
        /* Radio button styling */
        QRadioButton {{
            spacing: 8px;
            min-height: 24px;
        }}
        
        QRadioButton::indicator {{
            width: 20px;
            height: 20px;
            border: 2px solid {colors['border'].name()};
            border-radius: 10px;
            background-color: {colors['base'].name()};
        }}
        
        QRadioButton::indicator:hover {{
            border-color: {colors['primary'].name()};
        }}
        
        QRadioButton::indicator:focus {{
            outline: 2px solid {colors['focus_outline'].name()};
            outline-offset: 2px;
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {colors['primary'].name()};
            border-color: {colors['primary'].name()};
        }}
        
        /* Input field styling */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            min-height: 32px;
            padding: 6px;
            border: 2px solid {colors['border'].name()};
            border-radius: 4px;
            background-color: {colors['base'].name()};
            color: {colors['text'].name()};
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {colors['focus_outline'].name()};
            outline: none;
        }}
        
        /* ComboBox styling */
        QComboBox {{
            min-height: 32px;
            padding: 6px;
            border: 2px solid {colors['border'].name()};
            border-radius: 4px;
            background-color: {colors['base'].name()};
            color: {colors['text'].name()};
        }}
        
        QComboBox:focus {{
            border-color: {colors['focus_outline'].name()};
        }}
        
        /* List widget styling */
        QListWidget {{
            border: 2px solid {colors['border'].name()};
            border-radius: 4px;
            background-color: {colors['base'].name()};
            alternate-background-color: {colors['alternate_base'].name()};
        }}
        
        QListWidget::item {{
            min-height: 32px;
            padding: 4px;
            border-bottom: 1px solid {colors['border'].name()};
        }}
        
        QListWidget::item:selected {{
            background-color: {colors['highlight'].name()};
            color: {colors['highlight_text'].name()};
        }}
        
        QListWidget::item:focus {{
            outline: 2px solid {colors['focus_outline'].name()};
            outline-offset: -2px;
        }}
        
        /* Progress bar styling */
        QProgressBar {{
            min-height: 24px;
            border: 2px solid {colors['border'].name()};
            border-radius: 4px;
            background-color: {colors['base'].name()};
            text-align: center;
        }}
        
        QProgressBar::chunk {{
            background-color: {colors['primary'].name()};
            border-radius: 2px;
        }}
        
        /* Menu styling */
        QMenuBar {{
            background-color: {colors['window'].name()};
            color: {colors['window_text'].name()};
        }}
        
        QMenuBar::item {{
            padding: 8px 12px;
            background-color: transparent;
        }}
        
        QMenuBar::item:selected {{
            background-color: {colors['highlight'].name()};
            color: {colors['highlight_text'].name()};
        }}
        
        QMenu {{
            border: 2px solid {colors['border'].name()};
            background-color: {colors['base'].name()};
            color: {colors['text'].name()};
        }}
        
        QMenu::item {{
            padding: 8px 16px;
            min-height: 24px;
        }}
        
        QMenu::item:selected {{
            background-color: {colors['highlight'].name()};
            color: {colors['highlight_text'].name()};
        }}
        
        /* Tooltip styling */
        QToolTip {{
            padding: 8px;
            border: 2px solid {colors['border'].name()};
            border-radius: 4px;
            background-color: {colors['info'].name()};
            color: {colors['highlight_text'].name()};
            font-size: {font_size}pt;
        }}
        
        /* Tab widget styling */
        QTabWidget::pane {{
            border: 2px solid {colors['border'].name()};
            border-radius: 4px;
        }}
        
        QTabBar::tab {{
            min-height: 32px;
            min-width: 80px;
            padding: 8px 16px;
            border: 2px solid {colors['border'].name()};
            background-color: {colors['button'].name()};
            color: {colors['button_text'].name()};
        }}
        
        QTabBar::tab:selected {{
            background-color: {colors['primary'].name()};
            color: {colors['highlight_text'].name()};
        }}
        
        QTabBar::tab:focus {{
            outline: 2px solid {colors['focus_outline'].name()};
            outline-offset: 2px;
        }}
        """
        
        return stylesheet


# Global theme manager instance
_theme_manager = None

def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager