#!/usr/bin/env python3
"""
Step 17: Delete Manager with Recycle Bin + Undo
Handles safe file deletion with multiple options and undo functionality.
"""

import os
import sys
import time
import shutil
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

# Optional dependencies
try:
    import send2trash
    SEND2TRASH_AVAILABLE = True
except ImportError:
    SEND2TRASH_AVAILABLE = False
    print("send2trash not available - install with: pip install send2trash")

try:
    from PySide6.QtCore import QObject, Signal
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QTextEdit, QProgressBar, QMessageBox, QCheckBox, QGroupBox,
        QTableWidget, QTableWidgetItem, QHeaderView, QApplication
    )
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    # Fallback classes
    class QObject:
        def __init__(self, *args, **kwargs): pass
    class Signal:
        def __init__(self, *args): pass
        def emit(self, *args): pass
        def connect(self, func): pass


class DeleteMethod(Enum):
    """Available deletion methods."""
    RECYCLE_BIN = "recycle_bin"
    QUARANTINE = "quarantine"
    PERMANENT = "permanent"


@dataclass
class DeletedFile:
    """Information about a deleted file."""
    original_path: str
    file_size: int
    delete_method: DeleteMethod
    timestamp: float
    backup_path: Optional[str] = None
    quarantine_path: Optional[str] = None
    is_safe_duplicate: bool = False
    group_id: Optional[str] = None
    

@dataclass
class DeleteBatch:
    """A batch of deleted files that can be undone together."""
    batch_id: str
    timestamp: float
    delete_method: DeleteMethod
    files: List[DeletedFile]
    total_size: int
    quarantine_dir: Optional[str] = None
    description: str = ""
    
    @property
    def file_count(self) -> int:
        return len(self.files)
        
    @property
    def size_mb(self) -> float:
        return self.total_size / (1024 * 1024)


class DeleteManager(QObject):
    """
    Manages file deletion with multiple methods and undo capabilities.
    """
    
    # Signals
    delete_started = Signal(int)  # total files to delete
    delete_progress = Signal(int, str)  # progress, current file
    delete_completed = Signal(object)  # DeleteBatch
    delete_failed = Signal(str, str)  # file_path, error_message
    undo_completed = Signal(object)  # DeleteBatch
    undo_failed = Signal(str)  # error_message
    
    def __init__(self, quarantine_base_dir: Optional[str] = None):
        super().__init__()
        
        # Configuration
        self.quarantine_base_dir = Path(quarantine_base_dir) if quarantine_base_dir else Path.cwd() / "quarantine"
        self.max_undo_batches = 10
        
        # Undo stack
        self.delete_history: List[DeleteBatch] = []
        
        # Statistics
        self.total_deleted_files = 0
        self.total_deleted_size = 0
        
    def can_use_recycle_bin(self) -> bool:
        """Check if recycle bin deletion is available."""
        return SEND2TRASH_AVAILABLE
        
    def can_undo(self) -> bool:
        """Check if there are batches that can be undone."""
        return len(self.delete_history) > 0
        
    def get_last_batch(self) -> Optional[DeleteBatch]:
        """Get the most recent delete batch."""
        return self.delete_history[-1] if self.delete_history else None
        
    def create_quarantine_dir(self, timestamp: Optional[float] = None) -> Path:
        """Create a timestamped quarantine directory."""
        if timestamp is None:
            timestamp = time.time()
            
        date_str = datetime.fromtimestamp(timestamp).strftime("%Y%m%d_%H%M%S")
        quarantine_dir = self.quarantine_base_dir / f"deleted_{date_str}"
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        
        return quarantine_dir
        
    def delete_files(self, file_paths: List[str], method: DeleteMethod = DeleteMethod.RECYCLE_BIN,
                    description: str = "") -> DeleteBatch:
        """
        Delete files using the specified method.
        
        Args:
            file_paths: List of file paths to delete
            method: Deletion method to use
            description: Description of this delete operation
            
        Returns:
            DeleteBatch containing information about deleted files
        """
        if not file_paths:
            raise ValueError("No files provided for deletion")
            
        timestamp = time.time()
        batch_id = f"batch_{int(timestamp)}"
        
        self.delete_started.emit(len(file_paths))
        
        deleted_files = []
        total_size = 0
        quarantine_dir = None
        
        # Create quarantine directory if needed
        if method == DeleteMethod.QUARANTINE:
            quarantine_dir = self.create_quarantine_dir(timestamp)
            
        for i, file_path in enumerate(file_paths):
            try:
                file_path_obj = Path(file_path)
                
                if not file_path_obj.exists():
                    self.delete_failed.emit(file_path, "File not found")
                    continue
                    
                file_size = file_path_obj.stat().st_size
                
                deleted_file = DeletedFile(
                    original_path=file_path,
                    file_size=file_size,
                    delete_method=method,
                    timestamp=timestamp
                )
                
                # Perform deletion based on method
                if method == DeleteMethod.RECYCLE_BIN:
                    self._delete_to_recycle_bin(file_path_obj, deleted_file)
                elif method == DeleteMethod.QUARANTINE:
                    self._delete_to_quarantine(file_path_obj, deleted_file, quarantine_dir)
                elif method == DeleteMethod.PERMANENT:
                    self._delete_permanent(file_path_obj, deleted_file)
                    
                deleted_files.append(deleted_file)
                total_size += file_size
                
                self.delete_progress.emit(i + 1, file_path)
                
            except Exception as e:
                self.delete_failed.emit(file_path, str(e))
                continue
                
        # Create batch record
        batch = DeleteBatch(
            batch_id=batch_id,
            timestamp=timestamp,
            delete_method=method,
            files=deleted_files,
            total_size=total_size,
            quarantine_dir=str(quarantine_dir) if quarantine_dir else None,
            description=description or f"Deleted {len(deleted_files)} files"
        )
        
        # Add to history
        self.delete_history.append(batch)
        
        # Keep only recent batches
        if len(self.delete_history) > self.max_undo_batches:
            self.delete_history.pop(0)
            
        # Update statistics
        self.total_deleted_files += len(deleted_files)
        self.total_deleted_size += total_size
        
        self.delete_completed.emit(batch)
        return batch
        
    def _delete_to_recycle_bin(self, file_path: Path, deleted_file: DeletedFile):
        """Delete file to recycle bin."""
        if not SEND2TRASH_AVAILABLE:
            raise RuntimeError("send2trash not available")
            
        send2trash.send2trash(str(file_path))
        # Note: We can't easily track recycle bin location, so backup_path stays None
        
    def _delete_to_quarantine(self, file_path: Path, deleted_file: DeletedFile, quarantine_dir: Path):
        """Move file to quarantine directory."""
        # Create unique filename in quarantine to avoid conflicts
        base_name = file_path.name
        counter = 1
        quarantine_path = quarantine_dir / base_name
        
        while quarantine_path.exists():
            name_parts = file_path.stem, counter, file_path.suffix
            quarantine_path = quarantine_dir / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
            counter += 1
            
        # Move file to quarantine
        shutil.move(str(file_path), str(quarantine_path))
        deleted_file.quarantine_path = str(quarantine_path)
        
    def _delete_permanent(self, file_path: Path, deleted_file: DeletedFile):
        """Permanently delete file."""
        file_path.unlink()
        # No way to undo permanent deletion
        
    def undo_last_batch(self) -> bool:
        """
        Undo the last delete batch.
        
        Returns:
            True if undo was successful, False otherwise
        """
        if not self.delete_history:
            return False
            
        batch = self.delete_history.pop()
        
        try:
            restored_count = 0
            
            for deleted_file in batch.files:
                try:
                    if self._restore_file(deleted_file):
                        restored_count += 1
                except Exception as e:
                    self.undo_failed.emit(f"Failed to restore {deleted_file.original_path}: {str(e)}")
                    continue
                    
            # Update statistics
            self.total_deleted_files -= restored_count
            self.total_deleted_size -= sum(f.file_size for f in batch.files[:restored_count])
            
            self.undo_completed.emit(batch)
            return restored_count > 0
            
        except Exception as e:
            # Put batch back in history if undo failed
            self.delete_history.append(batch)
            self.undo_failed.emit(f"Undo failed: {str(e)}")
            return False
            
    def _restore_file(self, deleted_file: DeletedFile) -> bool:
        """
        Restore a single deleted file.
        
        Returns:
            True if restoration was successful
        """
        if deleted_file.delete_method == DeleteMethod.PERMANENT:
            # Cannot restore permanently deleted files
            return False
            
        elif deleted_file.delete_method == DeleteMethod.QUARANTINE:
            if deleted_file.quarantine_path and Path(deleted_file.quarantine_path).exists():
                # Move back from quarantine
                original_path = Path(deleted_file.original_path)
                original_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(deleted_file.quarantine_path, str(original_path))
                return True
                
        elif deleted_file.delete_method == DeleteMethod.RECYCLE_BIN:
            # Cannot programmatically restore from recycle bin
            # This would require platform-specific recycle bin APIs
            return False
            
        return False
        
    def open_recycle_bin(self):
        """Open the system recycle bin."""
        try:
            if sys.platform.startswith('win'):
                os.system('start shell:RecycleBinFolder')
            elif sys.platform.startswith('darwin'):
                os.system('open ~/.Trash')
            elif sys.platform.startswith('linux'):
                # Different desktop environments have different trash locations
                trash_dirs = [
                    Path.home() / '.local/share/Trash',
                    Path('/trash'),
                    Path('/var/trash')
                ]
                for trash_dir in trash_dirs:
                    if trash_dir.exists():
                        os.system(f'xdg-open "{trash_dir}"')
                        break
        except Exception as e:
            print(f"Failed to open recycle bin: {e}")
            
    def open_quarantine_dir(self, batch: Optional[DeleteBatch] = None):
        """Open quarantine directory for a specific batch or the base directory."""
        try:
            if batch and batch.quarantine_dir:
                target_dir = Path(batch.quarantine_dir)
            else:
                target_dir = self.quarantine_base_dir
                
            if target_dir.exists():
                if sys.platform.startswith('win'):
                    os.system(f'explorer "{target_dir}"')
                elif sys.platform.startswith('darwin'):
                    os.system(f'open "{target_dir}"')
                else:
                    os.system(f'xdg-open "{target_dir}"')
            else:
                print(f"Quarantine directory does not exist: {target_dir}")
        except Exception as e:
            print(f"Failed to open quarantine directory: {e}")
            
    def export_delete_history(self, file_path: str):
        """Export delete history to JSON file."""
        history_data = []
        
        for batch in self.delete_history:
            batch_data = asdict(batch)
            # Convert enum to string for JSON serialization
            batch_data['delete_method'] = batch.delete_method.value
            
            # Convert enum in files list too
            for file_data in batch_data['files']:
                if 'delete_method' in file_data:
                    file_data['delete_method'] = file_data['delete_method'].value if hasattr(file_data['delete_method'], 'value') else str(file_data['delete_method'])
            
            history_data.append(batch_data)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({
                'export_timestamp': time.time(),
                'total_batches': len(self.delete_history),
                'total_deleted_files': self.total_deleted_files,
                'total_deleted_size': self.total_deleted_size,
                'batches': history_data
            }, f, indent=2)
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get deletion statistics."""
        return {
            'total_batches': len(self.delete_history),
            'total_deleted_files': self.total_deleted_files,
            'total_deleted_size': self.total_deleted_size,
            'total_deleted_size_mb': self.total_deleted_size / (1024 * 1024),
            'can_undo': self.can_undo(),
            'recycle_bin_available': self.can_use_recycle_bin(),
            'quarantine_base_dir': str(self.quarantine_base_dir)
        }


# Fallback classes when PySide6 is not available
if not PYSIDE6_AVAILABLE:
    class QDialog:
        def __init__(self, *args, **kwargs): pass
        def exec(self): return False
        
    class QVBoxLayout:
        def __init__(self, *args): pass
        def addWidget(self, *args): pass
        
    class QHBoxLayout:
        def __init__(self, *args): pass
        def addWidget(self, *args): pass
        
    class QLabel:
        def __init__(self, *args): pass
        
    class QPushButton:
        def __init__(self, *args): pass
        def clicked(self): return Signal()
        
    class QTextEdit:
        def __init__(self, *args): pass
        
    class QProgressBar:
        def __init__(self, *args): pass
        
    class QMessageBox:
        def __init__(self, *args): pass
        @staticmethod
        def question(*args): return True
        @staticmethod
        def information(*args): pass
        @staticmethod
        def warning(*args): pass
        @staticmethod
        def critical(*args): pass
        
    class QCheckBox:
        def __init__(self, *args): pass
        
    class QGroupBox:
        def __init__(self, *args): pass
        
    class QTableWidget:
        def __init__(self, *args): pass
        
    class QTableWidgetItem:
        def __init__(self, *args): pass
        
    class QHeaderView:
        ResizeToContents = None


class DeleteConfirmationDialog(QDialog):
    """Dialog to confirm file deletion with details."""
    
    def __init__(self, files_to_delete: List[Dict[str, Any]], method: DeleteMethod, parent=None):
        super().__init__(parent)
        self.files_to_delete = files_to_delete
        self.method = method
        self.confirmed = False
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Confirm File Deletion")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel(f"Delete {len(self.files_to_delete)} files using {self.method.value.replace('_', ' ').title()}?")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold; margin: 10px;")
        layout.addWidget(header_label)
        
        # Statistics
        total_size = sum(f.get('size', 0) for f in self.files_to_delete)
        stats_label = QLabel(f"Total size: {total_size / (1024*1024):.1f} MB")
        stats_label.setStyleSheet("color: #666; margin: 5px 10px;")
        layout.addWidget(stats_label)
        
        # Method-specific warning
        if self.method == DeleteMethod.PERMANENT:
            warning_label = QLabel("⚠️ WARNING: Permanent deletion cannot be undone!")
            warning_label.setStyleSheet("color: red; font-weight: bold; margin: 10px;")
            layout.addWidget(warning_label)
        elif self.method == DeleteMethod.RECYCLE_BIN:
            info_label = QLabel("ℹ️ Files will be moved to Recycle Bin/Trash")
            info_label.setStyleSheet("color: blue; margin: 10px;")
            layout.addWidget(info_label)
        elif self.method == DeleteMethod.QUARANTINE:
            info_label = QLabel("ℹ️ Files will be moved to quarantine folder (can be undone)")
            info_label.setStyleSheet("color: green; margin: 10px;")
            layout.addWidget(info_label)
        
        # File list (preview)
        files_group = QGroupBox("Files to delete:")
        files_layout = QVBoxLayout(files_group)
        
        files_text = QTextEdit()
        files_text.setMaximumHeight(150)
        files_text.setReadOnly(True)
        
        # Show first 20 files
        file_list = []
        for i, file_info in enumerate(self.files_to_delete[:20]):
            path = file_info.get('path', 'Unknown')
            size = file_info.get('size', 0)
            file_list.append(f"{Path(path).name} ({size / (1024*1024):.1f} MB)")
            
        if len(self.files_to_delete) > 20:
            file_list.append(f"... and {len(self.files_to_delete) - 20} more files")
            
        files_text.setText('\n'.join(file_list))
        files_layout.addWidget(files_text)
        layout.addWidget(files_group)
        
        # Options
        if self.method == DeleteMethod.QUARANTINE:
            self.remember_location_cb = QCheckBox("Remember quarantine location for easy access")
            self.remember_location_cb.setChecked(True)
            layout.addWidget(self.remember_location_cb)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.confirm_btn = QPushButton("Delete Files")
        self.confirm_btn.clicked.connect(self.accept)
        self.confirm_btn.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold;")
        button_layout.addWidget(self.confirm_btn)
        
        layout.addLayout(button_layout)
        
    def accept(self):
        self.confirmed = True
        super().accept()


class DeleteProgressDialog(QDialog):
    """Dialog showing deletion progress."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Deleting Files...")
        self.setMinimumSize(400, 150)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("Preparing deletion...")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.current_file_label = QLabel("")
        self.current_file_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.current_file_label)
        
    def update_progress(self, current: int, total: int, current_file: str = ""):
        """Update progress display."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"Deleting files... ({current}/{total})")
        
        if current_file:
            # Show just filename, not full path
            filename = Path(current_file).name
            self.current_file_label.setText(f"Current: {filename}")