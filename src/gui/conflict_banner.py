"""
Conflict banner GUI component for Step 22 - Manual override notifications.

This module provides:
- Non-blocking banner widget for conflict notifications
- User interaction buttons for manual override actions
- Integration with manual override manager
"""

import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

try:
    from PySide6.QtWidgets import (
        QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
        QFrame, QSizePolicy, QSpacerItem, QCheckBox, QTextEdit,
        QButtonGroup, QRadioButton, QGroupBox
    )
    from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QRect, QEasingCurve
    from PySide6.QtGui import QFont, QPalette, QIcon
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QWidget = object
    Signal = lambda *args, **kwargs: None


@dataclass
class ConflictData:
    """Data for a conflict notification."""
    group_id: int
    auto_file_path: str
    user_file_path: str
    auto_file_id: int
    user_file_id: int
    reason: str
    confidence: float


if QT_AVAILABLE:
    class ConflictBanner(QFrame):
        """Non-blocking banner widget for showing original selection conflicts."""
        
        # Signals
        override_requested = Signal(int, int, bool, str)  # group_id, file_id, make_default, notes
        banner_dismissed = Signal(int)  # group_id
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.logger = logging.getLogger(__name__)
            self.current_conflict: Optional[ConflictData] = None
            
            # Setup UI
            self._setup_ui()
            self._setup_animations()
            
            # Auto-dismiss timer
            self.dismiss_timer = QTimer()
            self.dismiss_timer.setSingleShot(True)
            self.dismiss_timer.timeout.connect(self._auto_dismiss)
        
        def _setup_ui(self):
            """Setup the banner UI components."""
            self.setFrameStyle(QFrame.Box)
            self.setStyleSheet("""
                QFrame {
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 6px;
                    padding: 8px;
                }
                QLabel {
                    color: #856404;
                    background: transparent;
                    border: none;
                }
                QPushButton {
                    background-color: #ffc107;
                    border: 1px solid #ffb300;
                    border-radius: 4px;
                    padding: 4px 12px;
                    color: #212529;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ffb300;
                }
                QPushButton:pressed {
                    background-color: #ff8f00;
                }
                QPushButton#dismissButton {
                    background-color: #6c757d;
                    border: 1px solid #545b62;
                    color: white;
                }
                QPushButton#dismissButton:hover {
                    background-color: #545b62;
                }
            """)
            
            # Main layout
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(12, 8, 12, 8)
            main_layout.setSpacing(8)
            
            # Header with icon and title
            header_layout = QHBoxLayout()
            
            # Warning icon (using text for now)
            icon_label = QLabel("⚠️")
            icon_label.setStyleSheet("font-size: 16px;")
            header_layout.addWidget(icon_label)
            
            # Title
            self.title_label = QLabel("Original Selection Conflict")
            title_font = QFont()
            title_font.setBold(True)
            title_font.setPointSize(10)
            self.title_label.setFont(title_font)
            header_layout.addWidget(self.title_label)
            
            # Spacer
            header_layout.addStretch()
            
            # Dismiss button
            self.dismiss_btn = QPushButton("×")
            self.dismiss_btn.setObjectName("dismissButton")
            self.dismiss_btn.setFixedSize(24, 24)
            self.dismiss_btn.clicked.connect(self._dismiss)
            header_layout.addWidget(self.dismiss_btn)
            
            main_layout.addLayout(header_layout)
            
            # Conflict description
            self.description_label = QLabel()
            self.description_label.setWordWrap(True)
            self.description_label.setStyleSheet("font-size: 9pt; margin: 4px 0px;")
            main_layout.addWidget(self.description_label)
            
            # File comparison section
            comparison_frame = QFrame()
            comparison_layout = QHBoxLayout(comparison_frame)
            comparison_layout.setContentsMargins(0, 0, 0, 0)
            
            # Auto selection column
            auto_group = QGroupBox("Algorithm Selected:")
            auto_layout = QVBoxLayout(auto_group)
            
            self.auto_file_label = QLabel()
            self.auto_file_label.setStyleSheet("font-size: 8pt; color: #6c757d;")
            self.auto_file_label.setWordWrap(True)
            auto_layout.addWidget(self.auto_file_label)
            
            self.auto_radio = QRadioButton("Use this as original")
            auto_layout.addWidget(self.auto_radio)
            
            comparison_layout.addWidget(auto_group)
            
            # User selection column  
            user_group = QGroupBox("Your Preference:")
            user_layout = QVBoxLayout(user_group)
            
            self.user_file_label = QLabel()
            self.user_file_label.setStyleSheet("font-size: 8pt; color: #6c757d;")
            self.user_file_label.setWordWrap(True)
            user_layout.addWidget(self.user_file_label)
            
            self.user_radio = QRadioButton("Keep as original")
            self.user_radio.setChecked(True)  # Default to user preference
            user_layout.addWidget(self.user_radio)
            
            comparison_layout.addWidget(user_group)
            
            # Radio button group
            self.selection_group = QButtonGroup()
            self.selection_group.addButton(self.auto_radio, 0)
            self.selection_group.addButton(self.user_radio, 1)
            
            main_layout.addWidget(comparison_frame)
            
            # Options section
            options_layout = QVBoxLayout()
            
            # Make default checkbox
            self.make_default_cb = QCheckBox("Make this rule default going forward")
            self.make_default_cb.setStyleSheet("font-size: 9pt;")
            options_layout.addWidget(self.make_default_cb)
            
            # Notes input
            notes_label = QLabel("Notes (optional):")
            notes_label.setStyleSheet("font-size: 9pt; margin-top: 4px;")
            options_layout.addWidget(notes_label)
            
            self.notes_input = QTextEdit()
            self.notes_input.setMaximumHeight(60)
            self.notes_input.setPlaceholderText("Add a note about why you made this choice...")
            self.notes_input.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 9pt;
                }
            """)
            options_layout.addWidget(self.notes_input)
            
            main_layout.addLayout(options_layout)
            
            # Action buttons
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            self.apply_btn = QPushButton("Apply Choice")
            self.apply_btn.clicked.connect(self._apply_choice)
            button_layout.addWidget(self.apply_btn)
            
            self.later_btn = QPushButton("Decide Later")
            self.later_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e9ecef;
                    border: 1px solid #ced4da;
                    color: #495057;
                }
                QPushButton:hover {
                    background-color: #ced4da;
                }
            """)
            self.later_btn.clicked.connect(self._decide_later)
            button_layout.addWidget(self.later_btn)
            
            main_layout.addLayout(button_layout)
            
            # Initially hidden
            self.hide()
        
        def _setup_animations(self):
            """Setup slide-in/slide-out animations."""
            self.slide_animation = QPropertyAnimation(self, b"geometry")
            self.slide_animation.setDuration(300)
            self.slide_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        def show_conflict(self, conflict: ConflictData, auto_dismiss_ms: int = 30000):
            """Show a conflict notification."""
            self.current_conflict = conflict
            
            # Update UI with conflict data
            self._update_conflict_display()
            
            # Show the banner with animation
            self._show_animated()
            
            # Set auto-dismiss timer
            if auto_dismiss_ms > 0:
                self.dismiss_timer.start(auto_dismiss_ms)
            
            self.logger.info(f"Showing conflict banner for group {conflict.group_id}")
        
        def _update_conflict_display(self):
            """Update the UI with current conflict data."""
            if not self.current_conflict:
                return
            
            conflict = self.current_conflict
            
            # Update description
            self.description_label.setText(
                f"The algorithm selected a different file as the original for this group. "
                f"Confidence: {conflict.confidence:.1%}. Reason: {conflict.reason}"
            )
            
            # Update file labels
            auto_filename = Path(conflict.auto_file_path).name
            user_filename = Path(conflict.user_file_path).name
            
            self.auto_file_label.setText(f"📄 {auto_filename}\n{conflict.auto_file_path}")
            self.user_file_label.setText(f"📄 {user_filename}\n{conflict.user_file_path}")
            
            # Reset form state
            self.user_radio.setChecked(True)
            self.make_default_cb.setChecked(False)
            self.notes_input.clear()
        
        def _show_animated(self):
            """Show banner with slide-down animation."""
            if not self.parent():
                self.show()
                return
            
            # Calculate target geometry
            parent_rect = self.parent().rect()
            target_rect = QRect(0, 0, parent_rect.width(), self.sizeHint().height())
            
            # Start above the visible area
            start_rect = QRect(0, -target_rect.height(), target_rect.width(), target_rect.height())
            
            # Setup animation
            self.setGeometry(start_rect)
            self.show()
            
            self.slide_animation.setStartValue(start_rect)
            self.slide_animation.setEndValue(target_rect)
            self.slide_animation.start()
        
        def _hide_animated(self):
            """Hide banner with slide-up animation."""
            if not self.parent():
                self.hide()
                return
            
            current_rect = self.geometry()
            end_rect = QRect(current_rect.x(), -current_rect.height(), 
                           current_rect.width(), current_rect.height())
            
            self.slide_animation.setStartValue(current_rect)
            self.slide_animation.setEndValue(end_rect)
            self.slide_animation.finished.connect(self.hide)
            self.slide_animation.start()
        
        def _apply_choice(self):
            """Apply the user's choice."""
            if not self.current_conflict:
                return
            
            conflict = self.current_conflict
            
            # Determine which file was selected
            if self.user_radio.isChecked():
                selected_file_id = conflict.user_file_id
            else:
                selected_file_id = conflict.auto_file_id
            
            # Get options
            make_default = self.make_default_cb.isChecked()
            notes = self.notes_input.toPlainText().strip()
            
            # Emit signal
            self.override_requested.emit(
                conflict.group_id,
                selected_file_id,
                make_default,
                notes
            )
            
            # Hide banner
            self._dismiss()
            
            self.logger.info(f"Applied choice for group {conflict.group_id}: "
                           f"file {selected_file_id}, default={make_default}")
        
        def _decide_later(self):
            """Postpone the decision."""
            self._dismiss()
        
        def _dismiss(self):
            """Dismiss the banner."""
            if self.current_conflict:
                self.banner_dismissed.emit(self.current_conflict.group_id)
                self.current_conflict = None
            
            self.dismiss_timer.stop()
            self._hide_animated()
        
        def _auto_dismiss(self):
            """Auto-dismiss after timeout."""
            self.logger.info("Auto-dismissing conflict banner")
            self._dismiss()
        
        def is_showing_conflict(self, group_id: int) -> bool:
            """Check if currently showing conflict for a specific group."""
            return (self.current_conflict is not None and 
                   self.current_conflict.group_id == group_id and 
                   self.isVisible())


    class ConflictBannerManager(QWidget):
        """Manages multiple conflict banners and queues."""
        
        # Signals
        override_applied = Signal(int, int, bool, str)  # group_id, file_id, make_default, notes
        
        def __init__(self, parent=None, max_concurrent_banners: int = 1):
            super().__init__(parent)
            self.logger = logging.getLogger(__name__)
            self.max_concurrent_banners = max_concurrent_banners
            
            # Banner management
            self.active_banners: Dict[int, ConflictBanner] = {}  # group_id -> banner
            self.conflict_queue: list = []
            
            # Setup layout
            self.layout = QVBoxLayout(self)
            self.layout.setContentsMargins(0, 0, 0, 0)
            self.layout.setSpacing(4)
            
            # Spacer to push banners to top
            self.layout.addStretch()
        
        def show_conflict(self, conflict_data: ConflictData, auto_dismiss_ms: int = 30000):
            """Show a conflict banner or queue it if at capacity."""
            group_id = conflict_data.group_id
            
            # Check if already showing for this group
            if group_id in self.active_banners:
                self.logger.debug(f"Conflict banner already active for group {group_id}")
                return
            
            # Check capacity
            if len(self.active_banners) >= self.max_concurrent_banners:
                self.conflict_queue.append((conflict_data, auto_dismiss_ms))
                self.logger.info(f"Queued conflict for group {group_id} (queue size: {len(self.conflict_queue)})")
                return
            
            # Create and show banner
            self._create_and_show_banner(conflict_data, auto_dismiss_ms)
        
        def _create_and_show_banner(self, conflict_data: ConflictData, auto_dismiss_ms: int):
            """Create and show a new conflict banner."""
            banner = ConflictBanner(self)
            
            # Connect signals
            banner.override_requested.connect(self._handle_override_request)
            banner.banner_dismissed.connect(self._handle_banner_dismissed)
            
            # Add to layout and tracking
            self.layout.insertWidget(0, banner)  # Insert at top
            self.active_banners[conflict_data.group_id] = banner
            
            # Show the conflict
            banner.show_conflict(conflict_data, auto_dismiss_ms)
            
            self.logger.info(f"Created conflict banner for group {conflict_data.group_id}")
        
        def _handle_override_request(self, group_id: int, file_id: int, make_default: bool, notes: str):
            """Handle override request from banner."""
            self.override_applied.emit(group_id, file_id, make_default, notes)
        
        def _handle_banner_dismissed(self, group_id: int):
            """Handle banner dismissal."""
            if group_id in self.active_banners:
                banner = self.active_banners.pop(group_id)
                banner.deleteLater()
                
                self.logger.info(f"Dismissed conflict banner for group {group_id}")
                
                # Process queue
                self._process_queue()
        
        def _process_queue(self):
            """Process queued conflicts."""
            while (len(self.active_banners) < self.max_concurrent_banners and 
                   self.conflict_queue):
                conflict_data, auto_dismiss_ms = self.conflict_queue.pop(0)
                self._create_and_show_banner(conflict_data, auto_dismiss_ms)
        
        def dismiss_conflict(self, group_id: int):
            """Programmatically dismiss a conflict banner."""
            if group_id in self.active_banners:
                self.active_banners[group_id]._dismiss()
        
        def dismiss_all_conflicts(self):
            """Dismiss all active conflict banners."""
            for banner in list(self.active_banners.values()):
                banner._dismiss()
        
        def get_active_conflicts(self) -> list:
            """Get list of currently active conflict group IDs."""
            return list(self.active_banners.keys())
        
        def get_queue_size(self) -> int:
            """Get size of conflict queue."""
            return len(self.conflict_queue)


    def create_conflict_banner_manager(parent=None, max_concurrent: int = 1) -> ConflictBannerManager:
        """Factory function to create conflict banner manager."""
        return ConflictBannerManager(parent, max_concurrent)

else:
    # Fallback for non-Qt environments
    class ConflictBanner:
        def __init__(self, *args, **kwargs):
            pass
        
        def show_conflict(self, *args, **kwargs):
            pass
    
    class ConflictBannerManager:
        def __init__(self, *args, **kwargs):
            pass
        
        def show_conflict(self, *args, **kwargs):
            pass
    
    def create_conflict_banner_manager(*args, **kwargs):
        return ConflictBannerManager()