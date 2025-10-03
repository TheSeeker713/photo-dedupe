#!/usr/bin/env python3
"""
Step 20 Demo: Cache Cleanup Scheduler
Interactive demonstration of cache cleanup scheduler with diagnostics card.
"""

import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
        QPushButton, QLabel, QSpinBox, QGroupBox, QGridLayout, QTextEdit,
        QProgressBar, QFrame, QScrollArea
    )
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont
    PYSIDE6_AVAILABLE = True
except ImportError:
    print("❌ PySide6 not available - GUI demo cannot run")
    PYSIDE6_AVAILABLE = False
    sys.exit(1)

from cache.cleanup_scheduler import CacheCleanupScheduler, CleanupMode, create_cache_scheduler
from gui.cache_diagnostics import CacheDiagnosticsCard
from app.settings import Settings

class CacheSimulator:
    """Simulates cache files for testing purposes."""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def create_sample_cache(self, total_size_mb: int = 100):
        """Create sample cache files."""
        print(f"📁 Creating {total_size_mb}MB of sample cache files...")
        
        # Create various types of cache files
        files_to_create = [
            ("thumbnails/thumb_001.jpg", 5, 10),
            ("thumbnails/thumb_002.jpg", 8, 15),
            ("thumbnails/thumb_003.jpg", 12, 5),
            ("temp/processing.tmp", 3, 0),
            ("temp/convert.partial", 7, 1),
            ("hashes/phash_cache.dat", 15, 30),
            ("hashes/dhash_cache.dat", 20, 25),
            ("metadata/exif_cache.json", 5, 8),
            ("metadata/features.cache", 10, 12),
            ("old_data/legacy.dat", 15, 45),
        ]
        
        created_files = 0
        total_created_size = 0
        
        for rel_path, size_mb, age_days in files_to_create:
            if total_created_size >= total_size_mb:
                break
                
            file_path = self.cache_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create file with specified size
            with open(file_path, 'wb') as f:
                data = b'X' * (1024 * 1024)  # 1MB chunks
                for _ in range(size_mb):
                    f.write(data)
            
            # Set age
            if age_days > 0:
                import time
                import os
                age_timestamp = time.time() - (age_days * 24 * 60 * 60)
                os.utime(file_path, (age_timestamp, age_timestamp))
            
            created_files += 1
            total_created_size += size_mb
            
        print(f"✅ Created {created_files} cache files ({total_created_size}MB)")
        return created_files, total_created_size

class Step20Demo(QMainWindow):
    """Interactive demo for Step 20 cache cleanup scheduler."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Step 20: Cache Cleanup Scheduler Demo")
        self.setGeometry(200, 200, 900, 800)
        
        # Setup test environment
        self.test_dir = Path(tempfile.mkdtemp(prefix="step20_demo_"))
        self.cache_dir = self.test_dir / "cache"
        self.simulator = CacheSimulator(self.cache_dir)
        
        # Create scheduler with test cache
        self.scheduler = CacheCleanupScheduler()
        self.scheduler.cache_dir = self.cache_dir
        self.scheduler.size_cap_mb = 75  # Set cap for easy testing
        
        self.setup_ui()
        self.apply_theme()
        self.connect_signals()
        
        # Initial cache creation
        QTimer.singleShot(1000, self.create_initial_cache)
    
    def setup_ui(self):
        """Setup the demo UI."""
        central_widget = QWidget()
        layout = QHBoxLayout(central_widget)
        layout.setSpacing(20)
        
        # Left panel: Controls and info
        left_panel = self.create_left_panel()
        layout.addWidget(left_panel, 1)
        
        # Right panel: Diagnostics card
        right_panel = self.create_right_panel()
        layout.addWidget(right_panel, 1)
        
        self.setCentralWidget(central_widget)
    
    def create_left_panel(self):
        """Create the left control panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("🧹 Cache Cleanup Scheduler Demo")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "Step 20 demonstrates automated cache cleanup with multiple triggers:\n\n"
            "• App startup (fast sweep)\n"
            "• Periodic idle sweep (every 10 minutes)\n"
            "• Immediate purge when size cap breached\n\n"
            "Try the controls below to test different scenarios!"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("background-color: #333; padding: 15px; border-radius: 5px; margin: 10px;")
        layout.addWidget(desc)
        
        # Cache simulation controls
        sim_group = QGroupBox("Cache Simulation")
        sim_layout = QGridLayout(sim_group)
        
        sim_layout.addWidget(QLabel("Cache Size (MB):"), 0, 0)
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(10, 500)
        self.cache_size_spin.setValue(100)
        sim_layout.addWidget(self.cache_size_spin, 0, 1)
        
        self.create_cache_button = QPushButton("📁 Create Sample Cache")
        self.create_cache_button.clicked.connect(self.create_sample_cache)
        sim_layout.addWidget(self.create_cache_button, 0, 2)
        
        self.clear_cache_button = QPushButton("🗑️ Clear All Cache")
        self.clear_cache_button.clicked.connect(self.clear_all_cache)
        sim_layout.addWidget(self.clear_cache_button, 1, 0, 1, 3)
        
        layout.addWidget(sim_group)
        
        # Scheduler controls
        sched_group = QGroupBox("Scheduler Configuration")
        sched_layout = QGridLayout(sched_group)
        
        sched_layout.addWidget(QLabel("Size Cap (MB):"), 0, 0)
        self.size_cap_spin = QSpinBox()
        self.size_cap_spin.setRange(10, 1000)
        self.size_cap_spin.setValue(75)
        self.size_cap_spin.valueChanged.connect(self.update_size_cap)
        sched_layout.addWidget(self.size_cap_spin, 0, 1)
        
        sched_layout.addWidget(QLabel("Target % after purge:"), 1, 0)
        self.target_pct_spin = QSpinBox()
        self.target_pct_spin.setRange(50, 95)
        self.target_pct_spin.setValue(80)
        self.target_pct_spin.valueChanged.connect(self.update_target_pct)
        sched_layout.addWidget(self.target_pct_spin, 1, 1)
        
        layout.addWidget(sched_group)
        
        # Test triggers
        trigger_group = QGroupBox("Trigger Tests")
        trigger_layout = QVBoxLayout(trigger_group)
        
        self.startup_test_button = QPushButton("🚀 Simulate App Startup")
        self.startup_test_button.clicked.connect(self.simulate_startup)
        trigger_layout.addWidget(self.startup_test_button)
        
        self.idle_test_button = QPushButton("😴 Simulate Idle Trigger")
        self.idle_test_button.clicked.connect(self.simulate_idle)
        trigger_layout.addWidget(self.idle_test_button)
        
        self.breach_test_button = QPushButton("⚠️ Force Cap Breach")
        self.breach_test_button.clicked.connect(self.force_cap_breach)
        trigger_layout.addWidget(self.breach_test_button)
        
        layout.addWidget(trigger_group)
        
        # Activity log
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        self.clear_log_button = QPushButton("🧹 Clear Log")
        self.clear_log_button.clicked.connect(self.clear_log)
        log_layout.addWidget(self.clear_log_button)
        
        layout.addWidget(log_group)
        
        layout.addStretch()
        return panel
    
    def create_right_panel(self):
        """Create the right diagnostics panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Diagnostics card
        self.diagnostics_card = CacheDiagnosticsCard(self.scheduler)
        
        # Scroll area for diagnostics
        scroll = QScrollArea()
        scroll.setWidget(self.diagnostics_card)
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        layout.addWidget(scroll)
        
        return panel
    
    def connect_signals(self):
        """Connect scheduler signals for logging."""
        self.scheduler.cleanup_started.connect(self.on_cleanup_started)
        self.scheduler.cleanup_progress.connect(self.on_cleanup_progress)
        self.scheduler.cleanup_completed.connect(self.on_cleanup_completed)
        self.scheduler.stats_updated.connect(self.on_stats_updated)
    
    def log_message(self, message: str):
        """Add message to activity log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
        # Keep log manageable
        if self.log_text.document().blockCount() > 100:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.Down, cursor.KeepAnchor, 10)
            cursor.removeSelectedText()
    
    def create_initial_cache(self):
        """Create initial cache for demonstration."""
        self.log_message("🚀 Creating initial demo cache...")
        self.simulator.create_sample_cache(100)  # 100MB cache
        self.scheduler._update_stats()
        self.log_message("✅ Initial cache created")
    
    def create_sample_cache(self):
        """Create sample cache with specified size."""
        size_mb = self.cache_size_spin.value()
        self.log_message(f"📁 Creating {size_mb}MB sample cache...")
        
        # Clear existing cache first
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        
        self.simulator = CacheSimulator(self.cache_dir)
        files, total_size = self.simulator.create_sample_cache(size_mb)
        
        self.scheduler._update_stats()
        self.log_message(f"✅ Created {files} files ({total_size}MB)")
    
    def clear_all_cache(self):
        """Clear all cache files."""
        self.log_message("🗑️ Clearing all cache files...")
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.scheduler._update_stats()
        self.log_message("✅ Cache cleared")
    
    def update_size_cap(self, value):
        """Update cache size cap."""
        self.scheduler.update_settings(value)
        self.log_message(f"📏 Size cap updated to {value}MB")
    
    def update_target_pct(self, value):
        """Update purge target percentage."""
        self.scheduler.purge_target_percentage = value
        self.log_message(f"🎯 Purge target updated to {value}%")
    
    def simulate_startup(self):
        """Simulate app startup cleanup."""
        self.log_message("🚀 Simulating app startup cleanup...")
        self.scheduler._startup_cleanup()
    
    def simulate_idle(self):
        """Simulate idle trigger."""
        self.log_message("😴 Simulating idle trigger...")
        self.scheduler._on_idle_detected()
    
    def force_cap_breach(self):
        """Force cache cap breach by creating large files."""
        self.log_message("⚠️ Forcing cache cap breach...")
        
        # Create additional large files to breach cap
        current_size = self.get_current_cache_size()
        cap = self.scheduler.size_cap_mb
        
        if current_size < cap:
            breach_size = int(cap - current_size + 20)  # +20MB to ensure breach
            self.log_message(f"📁 Adding {breach_size}MB to breach {cap}MB cap...")
            
            # Create large breach files
            breach_files = [
                (f"breach/large_file_{i}.dat", 10, 0)
                for i in range(breach_size // 10 + 1)
            ]
            
            for rel_path, size_mb, age_days in breach_files:
                file_path = self.cache_dir / rel_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'wb') as f:
                    data = b'X' * (1024 * 1024)
                    for _ in range(size_mb):
                        f.write(data)
        
        # Force stats update to trigger purge
        self.scheduler._update_stats()
        
    def get_current_cache_size(self) -> float:
        """Get current cache size in MB."""
        total_size = 0
        for file_path in self.cache_dir.rglob("*"):
            if file_path.is_file():
                try:
                    total_size += file_path.stat().st_size
                except OSError:
                    pass
        return total_size / (1024 * 1024)
    
    def clear_log(self):
        """Clear the activity log."""
        self.log_text.clear()
    
    def on_cleanup_started(self, trigger: str, mode: str):
        """Handle cleanup start."""
        self.log_message(f"🧹 Cleanup started: {trigger} -> {mode}")
    
    def on_cleanup_progress(self, progress: int, message: str):
        """Handle cleanup progress."""
        if progress % 25 == 0:  # Log every 25%
            self.log_message(f"📊 Progress: {progress}% - {message}")
    
    def on_cleanup_completed(self, success: bool, message: str, stats: dict):
        """Handle cleanup completion."""
        status = "✅" if success else "❌"
        self.log_message(f"{status} Cleanup completed: {message}")
        
        if stats and 'deleted_size_mb' in stats:
            deleted_mb = stats['deleted_size_mb']
            deleted_files = stats.get('deleted_files', 0)
            self.log_message(f"📈 Cleaned: {deleted_files} files ({deleted_mb:.1f}MB)")
    
    def on_stats_updated(self, diagnostics: dict):
        """Handle stats update."""
        size_mb = diagnostics.get('current_size_mb', 0)
        usage_pct = diagnostics.get('usage_percentage', 0)
        
        if usage_pct > 90:
            self.log_message(f"⚠️ High usage: {size_mb:.1f}MB ({usage_pct:.1f}%)")
    
    def closeEvent(self, event):
        """Clean up on close."""
        self.log_message("🧹 Cleaning up demo environment...")
        
        try:
            if self.test_dir.exists():
                shutil.rmtree(self.test_dir)
                self.log_message("✅ Demo environment cleaned up")
        except Exception as e:
            self.log_message(f"⚠️ Cleanup error: {e}")
        
        event.accept()
    
    def apply_theme(self):
        """Apply dark theme to the demo."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QFrame {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 5px;
                margin: 5px;
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
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #555;
                border-color: #777;
            }
            QPushButton:pressed {
                background-color: #333;
            }
            QSpinBox {
                background-color: #444;
                color: white;
                border: 1px solid #666;
                border-radius: 3px;
                padding: 4px;
                min-width: 60px;
            }
            QTextEdit {
                background-color: #222;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

def main():
    """Run the Step 20 demo."""
    print("🚀 Starting Step 20: Cache Cleanup Scheduler Demo")
    print("=" * 60)
    
    if not PYSIDE6_AVAILABLE:
        print("❌ PySide6 not available - demo cannot run")
        return 1
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    demo = Step20Demo()
    demo.show()
    
    print("✅ Demo window opened")
    print("🎯 Features to test:")
    print("   • Create sample cache files")
    print("   • Adjust size cap and watch auto-purge")
    print("   • Try different cleanup triggers")
    print("   • Monitor diagnostics card updates")
    print("   • Force cache cap breach")
    
    result = app.exec()
    
    print("\n🏁 Step 20 demo completed")
    return result

if __name__ == "__main__":
    sys.exit(main())