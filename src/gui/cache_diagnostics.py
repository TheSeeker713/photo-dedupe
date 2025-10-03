#!/usr/bin/env python3
"""
Cache Diagnostics Card Widget
Visual component for displaying cache statistics and cleanup controls.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
        QLabel, QPushButton, QProgressBar, QFrame, QComboBox,
        QSizePolicy, QSpacerItem, QTextEdit, QScrollArea
    )
    from PySide6.QtCore import Qt, QTimer, Signal, Slot
    from PySide6.QtGui import QFont, QPalette, QColor
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    # Fallback classes
    class QWidget: pass
    class QVBoxLayout: pass
    def Signal(*args): return lambda x: x

# Add src to path for imports
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from cache.cleanup_scheduler import CacheCleanupScheduler, CleanupMode, create_cache_scheduler
    from app.settings import Settings
except ImportError:
    CacheCleanupScheduler = None
    CleanupMode = None
    create_cache_scheduler = None
    Settings = None

class CacheDiagnosticsCard(QWidget):
    """Widget displaying comprehensive cache diagnostics and controls."""
    
    cleanup_requested = Signal(str)  # cleanup mode
    
    def __init__(self, scheduler: Optional[CacheCleanupScheduler] = None, parent=None):
        super().__init__(parent)
        self.scheduler = scheduler
        self.current_diagnostics = {}
        
        self.setup_ui()
        self.apply_theme()
        
        if self.scheduler:
            self.connect_scheduler_signals()
            self.refresh_diagnostics()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_diagnostics)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
    
    def setup_ui(self):
        """Setup the diagnostics card UI."""
        self.setMinimumWidth(400)
        self.setMaximumHeight(600)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("📊 Cache Diagnostics")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Create sections
        self.setup_overview_section(layout)
        self.setup_usage_section(layout)
        self.setup_maintenance_section(layout)
        self.setup_controls_section(layout)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def setup_overview_section(self, parent_layout):
        """Setup cache overview section."""
        overview_group = QGroupBox("Cache Overview")
        overview_layout = QGridLayout(overview_group)
        
        # Current size
        overview_layout.addWidget(QLabel("Current Size:"), 0, 0)
        self.size_label = QLabel("0.0 MB")
        self.size_label.setFont(QFont("Arial", 10, QFont.Bold))
        overview_layout.addWidget(self.size_label, 0, 1)
        
        # File count
        overview_layout.addWidget(QLabel("Files:"), 0, 2)
        self.files_label = QLabel("0")
        self.files_label.setFont(QFont("Arial", 10, QFont.Bold))
        overview_layout.addWidget(self.files_label, 0, 3)
        
        # Usage percentage with progress bar
        overview_layout.addWidget(QLabel("Usage:"), 1, 0)
        self.usage_progress = QProgressBar()
        self.usage_progress.setRange(0, 100)
        self.usage_progress.setTextVisible(True)
        overview_layout.addWidget(self.usage_progress, 1, 1, 1, 3)
        
        # Size cap
        overview_layout.addWidget(QLabel("Size Cap:"), 2, 0)
        self.cap_label = QLabel("1024 MB")
        overview_layout.addWidget(self.cap_label, 2, 1)
        
        # Status indicator
        overview_layout.addWidget(QLabel("Status:"), 2, 2)
        self.status_label = QLabel("Healthy")
        overview_layout.addWidget(self.status_label, 2, 3)
        
        parent_layout.addWidget(overview_group)
    
    def setup_usage_section(self, parent_layout):
        """Setup cache usage details section."""
        usage_group = QGroupBox("Usage Details")
        usage_layout = QGridLayout(usage_group)
        
        # Reclaimable space
        usage_layout.addWidget(QLabel("Reclaimable:"), 0, 0)
        self.reclaimable_label = QLabel("0.0 MB (0 files)")
        usage_layout.addWidget(self.reclaimable_label, 0, 1, 1, 2)
        
        # Fragmentation level
        usage_layout.addWidget(QLabel("Fragmentation:"), 1, 0)
        self.fragmentation_progress = QProgressBar()
        self.fragmentation_progress.setRange(0, 100)
        self.fragmentation_progress.setTextVisible(True)
        self.fragmentation_progress.setFormat("%p% fragmented")
        usage_layout.addWidget(self.fragmentation_progress, 1, 1, 1, 2)
        
        # Oldest file age
        usage_layout.addWidget(QLabel("Oldest File:"), 2, 0)
        self.oldest_file_label = QLabel("N/A")
        usage_layout.addWidget(self.oldest_file_label, 2, 1, 1, 2)
        
        parent_layout.addWidget(usage_group)
    
    def setup_maintenance_section(self, parent_layout):
        """Setup maintenance history section."""
        maintenance_group = QGroupBox("Maintenance History")
        maintenance_layout = QGridLayout(maintenance_group)
        
        # Last cleanup
        maintenance_layout.addWidget(QLabel("Last Cleanup:"), 0, 0)
        self.last_cleanup_label = QLabel("Never")
        maintenance_layout.addWidget(self.last_cleanup_label, 0, 1, 1, 2)
        
        # Cleanup trigger
        maintenance_layout.addWidget(QLabel("Trigger:"), 1, 0)
        self.trigger_label = QLabel("N/A")
        maintenance_layout.addWidget(self.trigger_label, 1, 1, 1, 2)
        
        # Cleanup count
        maintenance_layout.addWidget(QLabel("Total Cleanups:"), 2, 0)
        self.cleanup_count_label = QLabel("0")
        maintenance_layout.addWidget(self.cleanup_count_label, 2, 1)
        
        # Cache hit rate
        maintenance_layout.addWidget(QLabel("Hit Rate:"), 2, 2)
        self.hit_rate_label = QLabel("0%")
        maintenance_layout.addWidget(self.hit_rate_label, 2, 3)
        
        parent_layout.addWidget(maintenance_group)
    
    def setup_controls_section(self, parent_layout):
        """Setup cleanup control section."""
        controls_group = QGroupBox("Cleanup Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        # Recommended action
        rec_layout = QHBoxLayout()
        rec_layout.addWidget(QLabel("Recommended:"))
        self.recommendation_label = QLabel("Cache healthy")
        self.recommendation_label.setFont(QFont("Arial", 9, QFont.Bold))
        rec_layout.addWidget(self.recommendation_label)
        rec_layout.addStretch()
        controls_layout.addLayout(rec_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.quick_clean_button = QPushButton("🧹 Quick Clean")
        self.quick_clean_button.setToolTip("Fast cleanup of obviously old files")
        self.quick_clean_button.clicked.connect(lambda: self.trigger_cleanup("fast_sweep"))
        button_layout.addWidget(self.quick_clean_button)
        
        self.full_clean_button = QPushButton("🔍 Full Clean")
        self.full_clean_button.setToolTip("Comprehensive cache analysis and cleanup")
        self.full_clean_button.clicked.connect(lambda: self.trigger_cleanup("full_sweep"))
        button_layout.addWidget(self.full_clean_button)
        
        self.purge_button = QPushButton("🗑️ Purge")
        self.purge_button.setToolTip("Aggressive cleanup to reduce cache size")
        self.purge_button.clicked.connect(lambda: self.trigger_cleanup("size_purge"))
        button_layout.addWidget(self.purge_button)
        
        controls_layout.addLayout(button_layout)
        
        # Progress bar for active cleanups
        self.cleanup_progress = QProgressBar()
        self.cleanup_progress.setVisible(False)
        controls_layout.addWidget(self.cleanup_progress)
        
        # Status message
        self.status_message = QLabel("")
        self.status_message.setWordWrap(True)
        self.status_message.setMaximumHeight(40)
        self.status_message.setStyleSheet("color: #888; font-style: italic;")
        controls_layout.addWidget(self.status_message)
        
        parent_layout.addWidget(controls_group)
    
    def connect_scheduler_signals(self):
        """Connect to scheduler signals for real-time updates."""
        if not self.scheduler:
            return
        
        self.scheduler.stats_updated.connect(self.update_diagnostics)
        self.scheduler.cleanup_started.connect(self.on_cleanup_started)
        self.scheduler.cleanup_progress.connect(self.on_cleanup_progress)
        self.scheduler.cleanup_completed.connect(self.on_cleanup_completed)
    
    def set_scheduler(self, scheduler: CacheCleanupScheduler):
        """Set the cache scheduler."""
        self.scheduler = scheduler
        self.connect_scheduler_signals()
        self.refresh_diagnostics()
    
    def refresh_diagnostics(self):
        """Refresh diagnostics from scheduler."""
        if self.scheduler:
            diagnostics = self.scheduler.get_diagnostics_card_data()
            self.update_diagnostics(diagnostics)
    
    def update_diagnostics(self, diagnostics: Dict[str, Any]):
        """Update the diagnostics display."""
        self.current_diagnostics = diagnostics
        
        # Overview section
        self.size_label.setText(f"{diagnostics.get('current_size_mb', 0):.1f} MB")
        self.files_label.setText(str(diagnostics.get('current_files', 0)))
        self.cap_label.setText(f"{diagnostics.get('size_cap_mb', 0):.0f} MB")
        
        # Usage progress
        usage_pct = diagnostics.get('usage_percentage', 0)
        self.usage_progress.setValue(int(usage_pct))
        
        # Color code usage based on percentage
        if usage_pct > 90:
            self.usage_progress.setStyleSheet("QProgressBar::chunk { background-color: #ff4444; }")
            status = "⚠️ Critical"
            status_color = "#ff4444"
        elif usage_pct > 75:
            self.usage_progress.setStyleSheet("QProgressBar::chunk { background-color: #ffaa00; }")
            status = "⚠️ High"
            status_color = "#ffaa00"
        elif usage_pct > 50:
            self.usage_progress.setStyleSheet("QProgressBar::chunk { background-color: #ffdd00; }")
            status = "⚡ Moderate"
            status_color = "#ffdd00"
        else:
            self.usage_progress.setStyleSheet("QProgressBar::chunk { background-color: #44ff44; }")
            status = "✅ Healthy"
            status_color = "#44ff44"
        
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        
        # Usage details
        reclaimable_mb = diagnostics.get('reclaimable_size_mb', 0)
        reclaimable_files = diagnostics.get('reclaimable_files', 0)
        self.reclaimable_label.setText(f"{reclaimable_mb:.1f} MB ({reclaimable_files} files)")
        
        frag_level = diagnostics.get('fragmentation_level', 0) * 100
        self.fragmentation_progress.setValue(int(frag_level))
        
        oldest_age = diagnostics.get('oldest_file_age_days', 0)
        if oldest_age > 0:
            self.oldest_file_label.setText(f"{oldest_age} days old")
        else:
            self.oldest_file_label.setText("N/A")
        
        # Maintenance history
        last_cleanup = diagnostics.get('last_cleanup_date')
        if last_cleanup:
            if isinstance(last_cleanup, str):
                try:
                    last_cleanup = datetime.fromisoformat(last_cleanup)
                except:
                    last_cleanup = None
            
            if last_cleanup:
                days_ago = (datetime.now() - last_cleanup).days
                if days_ago == 0:
                    self.last_cleanup_label.setText("Today")
                elif days_ago == 1:
                    self.last_cleanup_label.setText("Yesterday")
                else:
                    self.last_cleanup_label.setText(f"{days_ago} days ago")
            else:
                self.last_cleanup_label.setText("Never")
        else:
            self.last_cleanup_label.setText("Never")
        
        trigger = diagnostics.get('last_cleanup_trigger', 'N/A')
        trigger_map = {
            'app_start': 'App Startup',
            'periodic_idle': 'Idle Timer',
            'size_cap_breach': 'Size Cap',
            'manual': 'Manual'
        }
        self.trigger_label.setText(trigger_map.get(trigger, trigger))
        
        self.cleanup_count_label.setText(str(diagnostics.get('cleanup_count', 0)))
        self.hit_rate_label.setText(f"{diagnostics.get('cache_hit_rate', 0):.1f}%")
        
        # Recommendation
        recommendation = diagnostics.get('recommended_action', 'Cache healthy')
        self.recommendation_label.setText(recommendation)
        
        # Color code recommendation
        if 'purge' in recommendation.lower() or 'critical' in recommendation.lower():
            rec_color = "#ff4444"
        elif 'cleanup' in recommendation.lower() or 'maintenance' in recommendation.lower():
            rec_color = "#ffaa00"
        else:
            rec_color = "#44ff44"
        
        self.recommendation_label.setStyleSheet(f"color: {rec_color};")
        
        # Enable/disable buttons based on state
        is_breached = diagnostics.get('is_size_cap_breached', False)
        self.purge_button.setEnabled(True)
        if is_breached:
            self.purge_button.setStyleSheet("QPushButton { background-color: #ff4444; color: white; font-weight: bold; }")
        else:
            self.purge_button.setStyleSheet("")
    
    def trigger_cleanup(self, mode: str):
        """Trigger a cleanup operation."""
        if self.scheduler:
            if mode == "fast_sweep":
                self.scheduler.trigger_manual_cleanup(CleanupMode.FAST_SWEEP)
            elif mode == "full_sweep":
                self.scheduler.trigger_manual_cleanup(CleanupMode.FULL_SWEEP)
            elif mode == "size_purge":
                self.scheduler.force_size_purge()
        
        self.cleanup_requested.emit(mode)
    
    def on_cleanup_started(self, trigger: str, mode: str):
        """Handle cleanup start."""
        self.cleanup_progress.setVisible(True)
        self.cleanup_progress.setValue(0)
        
        mode_names = {
            'fast_sweep': 'Quick Clean',
            'full_sweep': 'Full Clean',
            'size_purge': 'Cache Purge'
        }
        
        mode_name = mode_names.get(mode, mode)
        self.status_message.setText(f"🚀 Starting {mode_name}...")
        
        # Disable buttons during cleanup
        self.quick_clean_button.setEnabled(False)
        self.full_clean_button.setEnabled(False)
        self.purge_button.setEnabled(False)
    
    def on_cleanup_progress(self, progress: int, message: str):
        """Handle cleanup progress updates."""
        self.cleanup_progress.setValue(progress)
        self.status_message.setText(f"📊 {message}")
    
    def on_cleanup_completed(self, success: bool, message: str, stats: Dict[str, Any]):
        """Handle cleanup completion."""
        self.cleanup_progress.setVisible(False)
        
        if success:
            self.status_message.setText(f"✅ {message}")
            self.status_message.setStyleSheet("color: #44ff44; font-style: italic;")
        else:
            self.status_message.setText(f"❌ {message}")
            self.status_message.setStyleSheet("color: #ff4444; font-style: italic;")
        
        # Re-enable buttons
        self.quick_clean_button.setEnabled(True)
        self.full_clean_button.setEnabled(True)
        self.purge_button.setEnabled(True)
        
        # Clear status after a delay
        QTimer.singleShot(10000, self.clear_status_message)
    
    def clear_status_message(self):
        """Clear the status message."""
        self.status_message.setText("")
        self.status_message.setStyleSheet("color: #888; font-style: italic;")
    
    def apply_theme(self):
        """Apply dark theme to the diagnostics card."""
        self.setStyleSheet("""
            CacheDiagnosticsCard {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #0078d4;
            }
            QLabel {
                color: #ffffff;
                padding: 2px;
            }
            QPushButton {
                background-color: #444;
                color: white;
                border: 1px solid #666;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
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
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                background-color: #333;
                text-align: center;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 2px;
            }
        """)

if __name__ == "__main__":
    """Demo the cache diagnostics card."""
    print("📊 Cache Diagnostics Card Demo")
    print("=" * 40)
    
    if not PYSIDE6_AVAILABLE:
        print("❌ PySide6 not available - demo cannot run")
        sys.exit(1)
    
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    
    app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Cache Diagnostics Demo")
    window.setGeometry(200, 200, 500, 700)
    
    # Create central widget
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    
    # Create scheduler and diagnostics card
    scheduler = create_cache_scheduler()
    diagnostics_card = CacheDiagnosticsCard(scheduler)
    
    layout.addWidget(diagnostics_card)
    layout.addStretch()
    
    window.setCentralWidget(central_widget)
    window.show()
    
    print("✅ Cache diagnostics card displayed")
    print("💡 Try the cleanup buttons to test functionality")
    
    app.exec()