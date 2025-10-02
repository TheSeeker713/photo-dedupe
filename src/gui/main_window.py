#!/usr/bin/env python3
"""
Step 15: GUI Shell (PySide6)
Main window for the photo deduplication application.
"""

import sys
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QToolBar, QPushButton, QSplitter, QTreeWidget, QTreeWidgetItem,
        QLabel, QProgressBar, QStatusBar, QComboBox, QCheckBox,
        QFileDialog, QMessageBox, QFrame, QScrollArea, QGridLayout,
        QTextEdit, QSlider, QGroupBox, QSpinBox, QTabWidget
    )
    from PySide6.QtCore import Qt, QTimer, QThread, Signal, QSize
    from PySide6.QtGui import QPixmap, QIcon, QAction, QPalette, QFont
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    print("PySide6 not available")
    
    # Fallback classes when PySide6 is not available
    class QWidget:
        def __init__(self, *args, **kwargs): pass
    class QMainWindow:
        def __init__(self, *args, **kwargs): pass
    class Signal:
        def __init__(self, *args, **kwargs): pass
        def emit(self, *args, **kwargs): pass
        def connect(self, *args, **kwargs): pass


# Import our application modules
if __name__ == "__main__":
    # Handle imports when running as main
    sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.settings import Settings
    from store.db import DatabaseManager
    from store.cache import CacheManager
    from core.diagnostics import DiagnosticsPanel, setup_logging
    from ops.grouping import DuplicateGrouper
    from ops.delete_manager import (
        DeleteManager, DeleteMethod, DeleteConfirmationDialog, 
        DeleteProgressDialog
    )
    from gui.selection_model import (
        SelectionModel, KeyboardShortcutManager, BulkActionManager,
        FileSelection, GroupSelection
    )
except ImportError:
    # Fallback for development
    Settings = None
    DatabaseManager = None
    CacheManager = None
    DiagnosticsPanel = None
    setup_logging = None
    DuplicateGrouper = None


@dataclass
class GroupInfo:
    """Information about a duplicate group."""
    group_id: int
    reason: str
    member_count: int
    total_size: int
    reclaimable_size: int
    group_type: str  # "exact", "near", "safe", "conflict"


@dataclass
class FileInfo:
    """Information about a file in a group."""
    file_id: int
    path: str
    size: int
    role: str  # "original", "duplicate", "safe_duplicate"
    similarity_score: float = 0.0
    thumbnail_path: Optional[str] = None


class WorkerStatusWidget(QWidget):
    """Widget to display worker status and progress."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Thread count
        self.thread_label = QLabel("Threads: 0")
        layout.addWidget(self.thread_label)
        
        self.setLayout(layout)
        
    def update_status(self, status: str, progress: int = -1):
        """Update the worker status."""
        self.status_label.setText(status)
        if progress >= 0:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(progress)
        else:
            self.progress_bar.setVisible(False)
            
    def update_thread_count(self, count: int):
        """Update the thread count display."""
        self.thread_label.setText(f"Threads: {count}")


class FilePreviewWidget(QWidget):
    """Widget to display file preview with thumbnail and details."""
    
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Thumbnail
        self.thumbnail_label = QLabel("No image selected")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setMinimumSize(200, 200)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                border: 1px solid gray;
                background-color: #f0f0f0;
            }
        """)
        layout.addWidget(self.thumbnail_label)
        
        # File details
        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(100)
        self.details_text.setReadOnly(True)
        layout.addWidget(self.details_text)
        
        self.setLayout(layout)
        
    def display_file(self, file_info: FileInfo):
        """Display file information and thumbnail."""
        self.current_file = file_info
        
        # Update thumbnail
        if file_info.thumbnail_path and Path(file_info.thumbnail_path).exists():
            pixmap = QPixmap(file_info.thumbnail_path)
            scaled_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumbnail_label.setPixmap(scaled_pixmap)
        else:
            self.thumbnail_label.setText("No thumbnail available")
            self.thumbnail_label.clear()
        
        # Update details
        details = f"""Path: {file_info.path}
Size: {file_info.size / (1024*1024):.2f} MB
Role: {file_info.role}
Similarity: {file_info.similarity_score:.2f}
"""
        self.details_text.setPlainText(details)


class CompareWidget(QWidget):
    """Widget for side-by-side file comparison."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout()
        
        # Left side - Original
        left_group = QGroupBox("Original")
        left_layout = QVBoxLayout()
        self.left_preview = FilePreviewWidget()
        left_layout.addWidget(self.left_preview)
        left_group.setLayout(left_layout)
        layout.addWidget(left_group)
        
        # Similarity score in the middle
        middle_layout = QVBoxLayout()
        middle_layout.addStretch()
        
        self.similarity_label = QLabel("Similarity: N/A")
        self.similarity_label.setAlignment(Qt.AlignCenter)
        self.similarity_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        middle_layout.addWidget(self.similarity_label)
        
        # Zoom controls
        zoom_group = QGroupBox("Zoom")
        zoom_layout = QVBoxLayout()
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(25, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setTickPosition(QSlider.TicksBelow)
        self.zoom_slider.setTickInterval(25)
        zoom_layout.addWidget(self.zoom_slider)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setAlignment(Qt.AlignCenter)
        zoom_layout.addWidget(self.zoom_label)
        zoom_group.setLayout(zoom_layout)
        middle_layout.addWidget(zoom_group)
        
        middle_layout.addStretch()
        
        middle_widget = QWidget()
        middle_widget.setLayout(middle_layout)
        middle_widget.setMaximumWidth(150)
        layout.addWidget(middle_widget)
        
        # Right side - Candidate
        right_group = QGroupBox("Candidate")
        right_layout = QVBoxLayout()
        self.right_preview = FilePreviewWidget()
        right_layout.addWidget(self.right_preview)
        right_group.setLayout(right_layout)
        layout.addWidget(right_group)
        
        self.setLayout(layout)
        
        # Connect zoom slider
        self.zoom_slider.valueChanged.connect(self.update_zoom)
        
    def update_zoom(self, value):
        """Update zoom level display."""
        self.zoom_label.setText(f"{value}%")
        # TODO: Implement actual zooming of images
        
    def compare_files(self, original: FileInfo, candidate: FileInfo):
        """Display two files for comparison."""
        self.left_preview.display_file(original)
        self.right_preview.display_file(candidate)
        self.similarity_label.setText(f"Similarity: {candidate.similarity_score:.1f}%")


class GroupsListWidget(QTreeWidget):
    """Tree widget for displaying duplicate groups."""
    
    group_selected = Signal(int)  # Emitted when a group is selected
    
    def __init__(self):
        super().__init__()
        self.groups_data = {}
        self.init_ui()
        
    def init_ui(self):
        self.setHeaderLabels(["Group", "Type", "Files", "Size", "Reclaimable"])
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        
        # Connect selection
        self.itemSelectionChanged.connect(self.on_selection_changed)
        
    def on_selection_changed(self):
        """Handle group selection."""
        current = self.currentItem()
        if current and current.data(0, Qt.UserRole):
            group_id = current.data(0, Qt.UserRole)
            self.group_selected.emit(group_id)
            
    def load_groups(self, groups: List[GroupInfo]):
        """Load groups into the tree."""
        self.clear()
        self.groups_data = {}
        
        for group in groups:
            item = QTreeWidgetItem([
                f"Group {group.group_id}",
                group.group_type.title(),
                str(group.member_count),
                f"{group.total_size / (1024*1024):.1f} MB",
                f"{group.reclaimable_size / (1024*1024):.1f} MB"
            ])
            item.setData(0, Qt.UserRole, group.group_id)
            self.addTopLevelItem(item)
            self.groups_data[group.group_id] = group
            
        self.expandAll()
        
    def filter_groups(self, filter_type: str):
        """Filter groups by type."""
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            group_id = item.data(0, Qt.UserRole)
            group = self.groups_data.get(group_id)
            
            if filter_type == "All" or not group:
                item.setHidden(False)
            else:
                should_show = (
                    (filter_type == "Exact" and group.group_type == "exact") or
                    (filter_type == "Near" and group.group_type == "near") or
                    (filter_type == "Safe Only" and group.group_type == "safe") or
                    (filter_type == "Conflicts" and group.group_type == "conflict")
                )
                item.setHidden(not should_show)


class CandidateGridWidget(QWidget):
    """Grid widget for displaying candidate files in a group."""
    
    candidate_selected = Signal(object)  # Emitted when a candidate is selected
    
    def __init__(self):
        super().__init__()
        self.files_data = []
        self.file_widgets = []  # Store references to file widgets with checkboxes
        self.init_ui()
        
    def init_ui(self):
        # Scroll area for the grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container for grid
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        
        self.scroll_area.setWidget(self.grid_container)
        
        layout = QVBoxLayout()
        layout.addWidget(self.scroll_area)
        self.setLayout(layout)
        
    def load_candidates(self, files: List[FileInfo]):
        """Load candidate files into the grid."""
        # Clear existing items
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)
            
        self.files_data = files
        self.file_widgets.clear()  # Clear previous widgets
        
        # Add files to grid
        cols = 3  # Number of columns
        for i, file_info in enumerate(files):
            row = i // cols
            col = i % cols
            
            # Create container widget for checkbox + preview
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(2, 2, 2, 2)
            
            # Selection checkbox
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(
                lambda state, path=file_info.path: self.parent().parent().parent().on_file_selection_changed(path, state == 2)
            )
            container_layout.addWidget(checkbox)
            
            # Create preview widget for this file
            preview = FilePreviewWidget()
            preview.display_file(file_info)
            preview.mousePressEvent = lambda event, f=file_info: self.candidate_selected.emit(f)
            
            # Add role indicator
            if file_info.role == "original":
                preview.setStyleSheet("border: 2px solid green;")
            elif file_info.role == "safe_duplicate":
                preview.setStyleSheet("border: 2px solid blue;")
            else:
                preview.setStyleSheet("border: 2px solid orange;")
                
            container_layout.addWidget(preview)
            
            # Store references for selection management
            container.checkbox = checkbox
            container.file_path = file_info.path
            self.file_widgets.append(container)
                
            self.grid_layout.addWidget(container, row, col)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.settings = None
        self.db_manager = None
        self.cache_manager = None
        self.logging_manager = None
        self.diagnostics = None
        self.duplicate_grouper = None
        
        # Sample data for demonstration
        self.sample_groups = []
        self.sample_files = {}
        
        # Selection model and managers
        self.selection_model = SelectionModel()
        self.keyboard_manager = None  # Will be initialized after UI
        self.bulk_action_manager = BulkActionManager(self.selection_model)
        
        # Delete manager
        self.delete_manager = DeleteManager()
        self.delete_method = DeleteMethod.RECYCLE_BIN  # Default method
        self.setup_delete_manager()
        
        self.init_ui()
        self.init_data()
        self.load_sample_data()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Photo Deduplicator")
        self.setGeometry(100, 100, 1400, 800)
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Create toolbar
        self.create_toolbar()
        
        # Create main content area
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left pane - Groups list and filters
        left_pane = self.create_left_pane()
        main_splitter.addWidget(left_pane)
        
        # Right pane - Preview area
        right_pane = self.create_right_pane()
        main_splitter.addWidget(right_pane)
        
        # Set splitter proportions
        main_splitter.setSizes([400, 1000])
        
        main_layout.addWidget(main_splitter)
        
        # Create status bar
        self.create_status_bar()
        
        # Update UI state
        self.update_ui_state()
        
        # Initialize keyboard shortcuts after UI is ready
        self.setup_keyboard_shortcuts()
        
    def create_toolbar(self):
        """Create the top toolbar."""
        toolbar = QToolBar()
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)
        
        # Pick Folders
        self.pick_folders_action = QAction("📁 Pick Folder(s)", self)
        self.pick_folders_action.triggered.connect(self.pick_folders)
        toolbar.addAction(self.pick_folders_action)
        
        toolbar.addSeparator()
        
        # Include Subfolders checkbox
        self.include_subfolders_cb = QCheckBox("Include Subfolders")
        self.include_subfolders_cb.setChecked(True)
        toolbar.addWidget(self.include_subfolders_cb)
        
        toolbar.addSeparator()
        
        # Start/Pause/Resume
        self.start_action = QAction("▶️ Start", self)
        self.start_action.triggered.connect(self.start_scan)
        toolbar.addAction(self.start_action)
        
        self.pause_action = QAction("⏸️ Pause", self)
        self.pause_action.triggered.connect(self.pause_scan)
        self.pause_action.setEnabled(False)
        toolbar.addAction(self.pause_action)
        
        self.resume_action = QAction("⏯️ Resume", self)
        self.resume_action.triggered.connect(self.resume_scan)
        self.resume_action.setEnabled(False)
        toolbar.addAction(self.resume_action)
        
        toolbar.addSeparator()
        
        # Dry Run checkbox
        self.dry_run_cb = QCheckBox("Dry Run")
        self.dry_run_cb.setChecked(True)
        toolbar.addWidget(self.dry_run_cb)
        
        toolbar.addSeparator()
        
        # Delete Selected
        self.delete_action = QAction("🗑️ Delete Selected", self)
        self.delete_action.triggered.connect(self.delete_selected)
        self.delete_action.setEnabled(False)
        toolbar.addAction(self.delete_action)
        
        # Undo Delete
        self.undo_delete_action = QAction("↶ Undo Delete", self)
        self.undo_delete_action.triggered.connect(self.undo_delete)
        self.undo_delete_action.setEnabled(False)
        toolbar.addAction(self.undo_delete_action)
        
        # Open Recycle Bin
        self.open_recycle_action = QAction("🗂️ Open Recycle Bin", self)
        self.open_recycle_action.triggered.connect(self.open_recycle_bin)
        toolbar.addAction(self.open_recycle_action)
        
        toolbar.addSeparator()
        
        # Delete method selection
        toolbar.addWidget(QLabel("Delete Method:"))
        self.delete_method_combo = QComboBox()
        self.delete_method_combo.addItems(["Recycle Bin", "Quarantine", "Permanent"])
        self.delete_method_combo.currentTextChanged.connect(self.on_delete_method_changed)
        toolbar.addWidget(self.delete_method_combo)
        
        toolbar.addSeparator()
        
        # Export Report
        self.export_action = QAction("📊 Export Report", self)
        self.export_action.triggered.connect(self.export_report)
        toolbar.addAction(self.export_action)
        
        toolbar.addSeparator()
        
        # Selection controls
        self.selection_info_label = QLabel("Selected: 0 files")
        toolbar.addWidget(self.selection_info_label)
        
        toolbar.addSeparator()
        
        # Bulk action buttons
        self.select_all_safe_action = QAction("✅ Select All Safe", self)
        self.select_all_safe_action.triggered.connect(self.select_all_safe)
        toolbar.addAction(self.select_all_safe_action)
        
        self.select_all_duplicates_action = QAction("🔄 Select All Duplicates", self)
        self.select_all_duplicates_action.triggered.connect(self.select_all_duplicates)
        toolbar.addAction(self.select_all_duplicates_action)
        
        self.clear_selection_action = QAction("❌ Clear Selection", self)
        self.clear_selection_action.triggered.connect(self.clear_selection)
        toolbar.addAction(self.clear_selection_action)
        
        self.export_selection_action = QAction("💾 Export Selection", self)
        self.export_selection_action.triggered.connect(self.export_selection)
        toolbar.addAction(self.export_selection_action)
        
        toolbar.addSeparator()
        
        # Settings
        self.settings_action = QAction("⚙️ Settings", self)
        self.settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(self.settings_action)
        
    def create_left_pane(self):
        """Create the left pane with groups list and filters."""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Filters
        filters_group = QGroupBox("Filters")
        filters_layout = QVBoxLayout(filters_group)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Exact", "Near", "Safe Only", "Conflicts"])
        self.filter_combo.currentTextChanged.connect(self.filter_groups)
        filters_layout.addWidget(QLabel("Show:"))
        filters_layout.addWidget(self.filter_combo)
        
        # Space saved estimate
        self.space_saved_label = QLabel("Space to reclaim: 0 MB")
        self.space_saved_label.setStyleSheet("font-weight: bold; color: green;")
        filters_layout.addWidget(self.space_saved_label)
        
        left_layout.addWidget(filters_group)
        
        # Groups list
        groups_group = QGroupBox("Duplicate Groups")
        groups_layout = QVBoxLayout(groups_group)
        
        self.groups_list = GroupsListWidget()
        self.groups_list.group_selected.connect(self.load_group_files)
        groups_layout.addWidget(self.groups_list)
        
        left_layout.addWidget(groups_group)
        
        return left_widget
        
    def create_right_pane(self):
        """Create the right pane with preview area."""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Tab widget for different views
        self.preview_tabs = QTabWidget()
        
        # Overview tab - show original and candidates grid
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        
        # Original file preview
        original_group = QGroupBox("Original File")
        original_layout = QVBoxLayout(original_group)
        self.original_preview = FilePreviewWidget()
        original_layout.addWidget(self.original_preview)
        overview_layout.addWidget(original_group)
        
        # Candidates grid
        candidates_group = QGroupBox("Duplicate Candidates")
        candidates_layout = QVBoxLayout(candidates_group)
        self.candidates_grid = CandidateGridWidget()
        self.candidates_grid.candidate_selected.connect(self.show_comparison)
        candidates_layout.addWidget(self.candidates_grid)
        overview_layout.addWidget(candidates_group)
        
        self.preview_tabs.addTab(overview_tab, "Overview")
        
        # Compare tab - side-by-side comparison
        self.compare_widget = CompareWidget()
        self.preview_tabs.addTab(self.compare_widget, "Compare")
        
        right_layout.addWidget(self.preview_tabs)
        
        return right_widget
        
    def create_status_bar(self):
        """Create the status bar."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # Worker status
        self.worker_status = WorkerStatusWidget()
        status_bar.addWidget(self.worker_status)
        
        status_bar.addPermanentWidget(QLabel("|"))
        
        # Cache status
        self.cache_status_label = QLabel("Cache: 0 MB")
        status_bar.addPermanentWidget(self.cache_status_label)
        
        # Update timer for status
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # Update every second
        
    def init_data(self):
        """Initialize data managers."""
        try:
            if Settings:
                self.settings = Settings()
            if DatabaseManager:
                self.db_manager = DatabaseManager()
            if CacheManager and self.settings:
                cache_dir = self.settings.get("Cache", "cache_dir")
                self.cache_manager = CacheManager(cache_dir)
            if setup_logging and self.settings:
                self.logging_manager = setup_logging(self.settings)
            if DiagnosticsPanel and self.db_manager and self.cache_manager:
                self.diagnostics = DiagnosticsPanel(
                    self.db_manager.db_path,
                    self.cache_manager,
                    Path("logs")
                )
        except Exception as e:
            print(f"Warning: Could not initialize data managers: {e}")
            
    def load_sample_data(self):
        """Load sample data for demonstration."""
        # Create sample groups
        self.sample_groups = [
            GroupInfo(1, "exact_match", 3, 6*1024*1024, 4*1024*1024, "exact"),
            GroupInfo(2, "similar_phash", 2, 4*1024*1024, 2*1024*1024, "near"), 
            GroupInfo(3, "size_match", 4, 8*1024*1024, 6*1024*1024, "safe"),
            GroupInfo(4, "name_conflict", 2, 3*1024*1024, 1*1024*1024, "conflict"),
        ]
        
        # Create sample files for each group
        self.sample_files = {
            1: [
                FileInfo(1, "/photos/vacation/IMG_001.jpg", 2*1024*1024, "original", 100.0),
                FileInfo(2, "/photos/backup/IMG_001.jpg", 2*1024*1024, "duplicate", 100.0),
                FileInfo(3, "/photos/copies/IMG_001_copy.jpg", 2*1024*1024, "duplicate", 100.0),
            ],
            2: [
                FileInfo(4, "/photos/sunset1.jpg", 2*1024*1024, "original", 95.5),
                FileInfo(5, "/photos/sunset2.jpg", 2*1024*1024, "duplicate", 95.5),
            ],
            3: [
                FileInfo(6, "/photos/family/dad.jpg", 2*1024*1024, "original", 88.2),
                FileInfo(7, "/photos/family/dad_edit.jpg", 2*1024*1024, "safe_duplicate", 88.2),
                FileInfo(8, "/photos/family/dad_crop.jpg", 2*1024*1024, "safe_duplicate", 85.1),
                FileInfo(9, "/photos/family/dad_old.jpg", 2*1024*1024, "duplicate", 82.7),
            ],
            4: [
                FileInfo(10, "/photos/DSC_001.jpg", 1*1024*1024, "original", 75.0),
                FileInfo(11, "/photos/temp/DSC_001.jpg", 2*1024*1024, "duplicate", 75.0),
            ],
        }
        
        # Load into UI
        self.groups_list.load_groups(self.sample_groups)
        self.update_space_estimate()
        
    def update_space_estimate(self):
        """Update the space savings estimate."""
        total_reclaimable = sum(group.reclaimable_size for group in self.sample_groups)
        self.space_saved_label.setText(f"Space to reclaim: {total_reclaimable / (1024*1024):.1f} MB")
        
    def filter_groups(self, filter_type: str):
        """Filter groups by type."""
        self.groups_list.filter_groups(filter_type)
        
    def load_group_files(self, group_id: int):
        """Load files for the selected group."""
        files = self.sample_files.get(group_id, [])
        
        if files:
            # Find original file
            original = next((f for f in files if f.role == "original"), files[0])
            self.original_preview.display_file(original)
            
            # Load candidates (excluding original)
            candidates = [f for f in files if f.role != "original"]
            self.candidates_grid.load_candidates(candidates)
            
            # Enable/disable actions based on selection
            self.delete_action.setEnabled(len(candidates) > 0)
            
    def show_comparison(self, candidate_file: FileInfo):
        """Show side-by-side comparison."""
        # Get current group's original file
        current_group_id = None
        current_item = self.groups_list.currentItem()
        if current_item:
            current_group_id = current_item.data(0, Qt.UserRole)
            
        if current_group_id:
            files = self.sample_files.get(current_group_id, [])
            original = next((f for f in files if f.role == "original"), None)
            
            if original:
                self.compare_widget.compare_files(original, candidate_file)
                self.preview_tabs.setCurrentIndex(1)  # Switch to Compare tab
                
    def update_ui_state(self):
        """Update UI state based on current conditions."""
        # Enable/disable actions based on state
        has_folders = True  # TODO: Check if folders are selected
        is_scanning = False  # TODO: Check if scanning is in progress
        
        self.start_action.setEnabled(has_folders and not is_scanning)
        self.pause_action.setEnabled(is_scanning)
        self.resume_action.setEnabled(False)  # TODO: Implement pause/resume
        
    def update_status(self):
        """Update status bar information."""
        # Update worker status
        self.worker_status.update_status("Ready", -1)
        self.worker_status.update_thread_count(0)
        
        # Update cache status
        self.cache_status_label.setText("Cache: 0 MB")
        
    # Action handlers
    def pick_folders(self):
        """Handle pick folders action."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan")
        if folder:
            self.worker_status.update_status(f"Selected: {folder}")
            self.update_ui_state()
            
    def start_scan(self):
        """Handle start scan action."""
        self.worker_status.update_status("Starting scan...", 0)
        # TODO: Implement actual scanning
        QMessageBox.information(self, "Scan", "Scan started! (Demo mode)")
        
    def pause_scan(self):
        """Handle pause scan action."""
        self.worker_status.update_status("Paused")
        # TODO: Implement pause
        
    def resume_scan(self):
        """Handle resume scan action."""
        self.worker_status.update_status("Resuming...")
        # TODO: Implement resume
        
    def delete_selected(self):
        """Handle delete selected action."""
        reply = QMessageBox.question(
            self, "Delete Files",
            "Are you sure you want to delete the selected duplicate files?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # TODO: Implement deletion
            QMessageBox.information(self, "Delete", "Files deleted! (Demo mode)")
            
    def export_report(self):
        """Handle export report action."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Report", "duplicate_report.txt", "Text Files (*.txt)"
        )
        if filename:
            # TODO: Implement report export
            QMessageBox.information(self, "Export", f"Report exported to {filename}! (Demo mode)")
            
    def open_settings(self):
        """Handle open settings action."""
        # TODO: Implement settings dialog
        QMessageBox.information(self, "Settings", "Settings dialog (Not implemented yet)")
        
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for selection operations."""
        if self.selection_model:
            self.keyboard_manager = KeyboardShortcutManager(self, self.selection_model)
            
            # Connect keyboard shortcuts to our handlers
            self.keyboard_manager.toggle_selection.connect(self.handle_toggle_selection)
            self.keyboard_manager.open_compare.connect(self.handle_open_compare)
            self.keyboard_manager.delete_selected.connect(self.handle_delete_selected)
            self.keyboard_manager.undo_action.connect(self.handle_undo)
            self.keyboard_manager.export_selection.connect(self.export_selection)
            
    def handle_toggle_selection(self, file_path: str):
        """Handle Space key toggle selection."""
        current_selection = self.selection_model.is_file_selected_by_path(file_path)
        self.selection_model.set_file_selection_by_path(file_path, not current_selection)
        self.update_selection_ui()
        
    def handle_open_compare(self, file_path: str):
        """Handle Enter key open compare."""
        # Switch to compare tab and show the file
        self.preview_tabs.setCurrentIndex(1)  # Compare tab
        # TODO: Load file for comparison
        
    def handle_delete_selected(self):
        """Handle Del key delete selected files."""
        if self.bulk_action_manager.has_selected_files():
            self.delete_selected()
            
    def handle_undo(self):
        """Handle Ctrl+Z undo operation."""
        if self.bulk_action_manager.can_undo():
            success = self.bulk_action_manager.undo_last_operation()
            if success:
                self.update_selection_ui()
                QMessageBox.information(self, "Undo", "Last operation undone")
            else:
                QMessageBox.warning(self, "Undo", "Failed to undo last operation")
        else:
            QMessageBox.information(self, "Undo", "No operations to undo")
            
    def on_file_selection_changed(self, file_path: str, selected: bool):
        """Handle file selection checkbox changes."""
        self.selection_model.set_file_selection_by_path(file_path, selected)
        self.update_selection_ui()
        
    def select_all_safe(self):
        """Select all files marked as safe to delete."""
        if not self.sample_groups:
            return
            
        for group in self.sample_groups:
            for file_data in group['files']:
                if file_data.get('is_safe_to_delete', False):
                    self.selection_model.set_file_selection_by_path(file_data['path'], True)
                    
        self.update_selection_ui()
        self.update_file_checkboxes()
        
    def select_all_duplicates(self):
        """Select all duplicate files (non-safe)."""
        if not self.sample_groups:
            return
            
        for group in self.sample_groups:
            for file_data in group['files']:
                if not file_data.get('is_safe_to_delete', False) and len(group['files']) > 1:
                    self.selection_model.set_file_selection_by_path(file_data['path'], True)
                    
        self.update_selection_ui()
        self.update_file_checkboxes()
        
    def clear_selection(self):
        """Clear all selections."""
        self.selection_model.clear_all_selections()
        self.update_selection_ui()
        self.update_file_checkboxes()
        
    def export_selection(self):
        """Export current selection to file."""
        if not self.bulk_action_manager.has_selected_files():
            QMessageBox.information(self, "Export", "No files selected for export")
            return
            
        filename, file_type = QFileDialog.getSaveFileName(
            self, "Export Selection", "selection.json",
            "JSON Files (*.json);;CSV Files (*.csv)"
        )
        
        if filename:
            try:
                if filename.endswith('.csv'):
                    self.bulk_action_manager.export_selection_csv(filename)
                else:
                    self.bulk_action_manager.export_selection_json(filename)
                QMessageBox.information(self, "Export", f"Selection exported to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export selection: {str(e)}")
                
    def update_selection_ui(self):
        """Update the selection information in the UI."""
        if self.selection_model:
            # Count both ID-based and path-based selections
            id_selected = len(self.selection_model.get_selected_file_ids())
            path_selected = len(self.selection_model.selected_files)
            total_selected = max(id_selected, path_selected)  # Use the larger count
            self.selection_info_label.setText(f"Selected: {total_selected} files")
            
        # Update overall UI state including delete buttons
        self.update_ui_state()
            
    def update_file_checkboxes(self):
        """Update checkbox states to match selection model."""
        if not hasattr(self, 'candidates_grid') or not self.candidates_grid.file_widgets:
            return
            
        for widget in self.candidates_grid.file_widgets:
            if hasattr(widget, 'checkbox') and hasattr(widget, 'file_path'):
                is_selected = self.selection_model.is_file_selected_by_path(widget.file_path)
                widget.checkbox.setChecked(is_selected)
                
    def load_group_files(self, group_id: int):
        """Load files for a specific group and update selection state."""
        # Call original method
        if hasattr(self, '_original_load_group_files'):
            self._original_load_group_files(group_id)
        
        # Update checkboxes after loading
        self.update_file_checkboxes()
        
    def setup_delete_manager(self):
        """Setup delete manager with signal connections."""
        if not self.delete_manager:
            return
            
        # Connect delete manager signals
        self.delete_manager.delete_started.connect(self.on_delete_started)
        self.delete_manager.delete_progress.connect(self.on_delete_progress)
        self.delete_manager.delete_completed.connect(self.on_delete_completed)
        self.delete_manager.delete_failed.connect(self.on_delete_failed)
        self.delete_manager.undo_completed.connect(self.on_undo_completed)
        self.delete_manager.undo_failed.connect(self.on_undo_failed)
        
    def on_delete_method_changed(self, method_text: str):
        """Handle delete method combo box changes."""
        method_map = {
            "Recycle Bin": DeleteMethod.RECYCLE_BIN,
            "Quarantine": DeleteMethod.QUARANTINE,
            "Permanent": DeleteMethod.PERMANENT
        }
        self.delete_method = method_map.get(method_text, DeleteMethod.RECYCLE_BIN)
        
    def delete_selected(self):
        """Handle delete selected action with confirmation dialog."""
        if not self.selection_model or not self.delete_manager:
            QMessageBox.warning(self, "Error", "Delete system not available")
            return
            
        # Get selected files
        selected_files = []
        
        # Check both ID-based and path-based selections
        selected_ids = self.selection_model.get_selected_file_ids()
        selected_paths = list(self.selection_model.selected_files)
        
        # Add ID-based selections
        for file_id in selected_ids:
            file_sel = self.selection_model.file_selections.get(file_id)
            if file_sel:
                selected_files.append({
                    'path': file_sel.file_path,
                    'size': file_sel.file_size,
                    'is_safe': file_sel.is_safe_duplicate
                })
                
        # Add path-based selections (for demo/testing)
        for file_path in selected_paths:
            if isinstance(file_path, str) and file_path not in [f['path'] for f in selected_files]:
                # Estimate file size for demo files
                try:
                    if Path(file_path).exists():
                        size = Path(file_path).stat().st_size
                    else:
                        size = 1024 * 1024  # Default 1MB for demo
                except:
                    size = 1024 * 1024
                    
                selected_files.append({
                    'path': file_path,
                    'size': size,
                    'is_safe': True
                })
        
        if not selected_files:
            QMessageBox.information(self, "No Selection", "No files selected for deletion")
            return
            
        # Show confirmation dialog
        confirmation = DeleteConfirmationDialog(selected_files, self.delete_method, self)
        
        if confirmation.exec() and confirmation.confirmed:
            # Perform deletion
            file_paths = [f['path'] for f in selected_files]
            description = f"Delete {len(file_paths)} selected files"
            
            try:
                # Show progress dialog
                self.progress_dialog = DeleteProgressDialog(self)
                self.progress_dialog.show()
                
                # Start deletion
                batch = self.delete_manager.delete_files(file_paths, self.delete_method, description)
                
                # Close progress dialog
                if hasattr(self, 'progress_dialog'):
                    self.progress_dialog.close()
                    
                # Clear selections after successful deletion
                self.selection_model.clear_all_selections()
                self.update_selection_ui()
                self.update_file_checkboxes()
                
            except Exception as e:
                if hasattr(self, 'progress_dialog'):
                    self.progress_dialog.close()
                QMessageBox.critical(self, "Delete Error", f"Failed to delete files: {str(e)}")
                
    def undo_delete(self):
        """Undo the last delete operation."""
        if not self.delete_manager or not self.delete_manager.can_undo():
            QMessageBox.information(self, "Undo", "No delete operations to undo")
            return
            
        last_batch = self.delete_manager.get_last_batch()
        if not last_batch:
            return
            
        # Confirm undo
        reply = QMessageBox.question(
            self, "Undo Delete",
            f"Undo deletion of {last_batch.file_count} files ({last_batch.size_mb:.1f} MB)?\\n\\n"
            f"Method: {last_batch.delete_method.value.replace('_', ' ').title()}\\n"
            f"Time: {datetime.fromtimestamp(last_batch.timestamp).strftime('%Y-%m-%d %H:%M:%S')}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success = self.delete_manager.undo_last_batch()
                if success:
                    QMessageBox.information(
                        self, "Undo Complete", 
                        f"Successfully restored files from the last delete operation"
                    )
                else:
                    QMessageBox.warning(
                        self, "Undo Failed",
                        "Could not restore all files. Check the console for details."
                    )
            except Exception as e:
                QMessageBox.critical(self, "Undo Error", f"Failed to undo delete: {str(e)}")
                
    def open_recycle_bin(self):
        """Open the system recycle bin or quarantine folder."""
        if not self.delete_manager:
            return
            
        try:
            # If last batch was quarantine, open that folder
            last_batch = self.delete_manager.get_last_batch()
            if last_batch and last_batch.delete_method == DeleteMethod.QUARANTINE:
                self.delete_manager.open_quarantine_dir(last_batch)
            else:
                self.delete_manager.open_recycle_bin()
        except Exception as e:
            QMessageBox.warning(self, "Open Folder", f"Could not open folder: {str(e)}")
            
    def on_delete_started(self, total_files: int):
        """Handle delete operation start."""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.update_progress(0, total_files)
            
    def on_delete_progress(self, current: int, current_file: str):
        """Handle delete progress updates."""
        if hasattr(self, 'progress_dialog'):
            # Get total from progress bar max (set in on_delete_started)
            total = getattr(self.progress_dialog.progress_bar, 'maximum', lambda: current)()
            self.progress_dialog.update_progress(current, total, current_file)
            QApplication.processEvents()  # Keep UI responsive
            
    def on_delete_completed(self, batch):
        """Handle delete operation completion."""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
            
        # Update undo button state
        self.undo_delete_action.setEnabled(self.delete_manager.can_undo())
        
        # Show completion message
        QMessageBox.information(
            self, "Delete Complete",
            f"Successfully deleted {batch.file_count} files ({batch.size_mb:.1f} MB)\\n\\n"
            f"Method: {batch.delete_method.value.replace('_', ' ').title()}"
        )
        
    def on_delete_failed(self, file_path: str, error_message: str):
        """Handle individual file delete failures."""
        print(f"Failed to delete {file_path}: {error_message}")
        
    def on_undo_completed(self, batch):
        """Handle undo operation completion."""
        self.undo_delete_action.setEnabled(self.delete_manager.can_undo())
        
    def on_undo_failed(self, error_message: str):
        """Handle undo operation failures."""
        QMessageBox.warning(self, "Undo Failed", f"Undo operation failed: {error_message}")
        
    def update_ui_state(self):
        """Update UI state based on current data and selections."""
        # Update delete button state
        has_selection = (
            self.selection_model and 
            (len(self.selection_model.get_selected_file_ids()) > 0 or 
             len(self.selection_model.selected_files) > 0)
        )
        self.delete_action.setEnabled(has_selection)
        
        # Update undo button state
        if self.delete_manager:
            self.undo_delete_action.setEnabled(self.delete_manager.can_undo())
            
        # Update delete method combo based on availability
        if hasattr(self, 'delete_method_combo'):
            if not self.delete_manager.can_use_recycle_bin():
                # Disable recycle bin option if send2trash not available
                for i in range(self.delete_method_combo.count()):
                    if self.delete_method_combo.itemText(i) == "Recycle Bin":
                        self.delete_method_combo.setItemData(i, False, Qt.UserRole - 1)
                        break


def main():
    """Main application entry point."""
    if not PYSIDE6_AVAILABLE:
        print("PySide6 is required to run the GUI application.")
        print("Install it with: pip install PySide6")
        return 1
        
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Photo Deduplicator")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("PhotoDedupe")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())