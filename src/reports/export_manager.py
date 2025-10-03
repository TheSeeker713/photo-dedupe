#!/usr/bin/env python3
"""
Step 18: Reports & Export
Comprehensive export functionality for duplicate analysis results.
"""

import csv
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

try:
    from PySide6.QtCore import QObject, Signal
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QTextEdit, QProgressBar, QMessageBox, QCheckBox, QGroupBox,
        QComboBox, QRadioButton, QButtonGroup, QFileDialog, QTableWidget,
        QTableWidgetItem, QHeaderView, QTabWidget, QWidget, QSplitter
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


class ExportFormat(Enum):
    """Available export formats."""
    CSV = "csv"
    JSON = "json"
    BOTH = "both"


class ExportScope(Enum):
    """Export scope options."""
    CURRENT_VIEW = "current_view"
    FULL_DATASET = "full_dataset"
    SELECTED_ONLY = "selected_only"


@dataclass
class ExportField:
    """Configuration for export fields."""
    name: str
    display_name: str
    description: str
    enabled: bool = True
    required: bool = False


@dataclass
class DuplicateRecord:
    """Complete record of a duplicate file analysis."""
    # Core identification
    group_id: str
    original_path: str
    duplicate_path: str
    
    # Classification
    tag: str  # "duplicate", "safe_duplicate", "original"
    reason: str  # "exact", "near", "similar"
    
    # Analysis metrics
    similarity_score: float
    file_hash: Optional[str] = None
    perceptual_hash: Optional[str] = None
    
    # File metadata
    file_size: int = 0
    original_size: int = 0
    
    # EXIF comparison
    exif_match: Optional[bool] = None
    exif_differences: Optional[str] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    date_taken: Optional[str] = None
    
    # Quality metrics
    resolution: Optional[str] = None
    quality_score: Optional[float] = None
    compression_ratio: Optional[float] = None
    
    # Action tracking
    action_taken: str = "pending"  # "kept", "deleted", "quarantined", "pending"
    action_timestamp: Optional[float] = None
    action_method: Optional[str] = None
    
    # Additional metadata
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    confidence_level: Optional[float] = None
    notes: Optional[str] = None


class ReportExporter(QObject):
    """
    Handles export of duplicate analysis results to various formats.
    """
    
    # Signals
    export_started = Signal(int)  # total records
    export_progress = Signal(int, str)  # current, description
    export_completed = Signal(str, str)  # format, file_path
    export_failed = Signal(str)  # error_message
    
    def __init__(self):
        super().__init__()
        
        # Export configuration
        self.available_fields = self._initialize_fields()
        self.export_settings = {
            'include_metadata': True,
            'include_timestamps': True,
            'include_exif_data': True,
            'csv_delimiter': ',',
            'json_indent': 2,
            'date_format': '%Y-%m-%d %H:%M:%S'
        }
        
    def _initialize_fields(self) -> List[ExportField]:
        """Initialize available export fields."""
        return [
            ExportField("group_id", "Group ID", "Unique identifier for the duplicate group", True, True),
            ExportField("original_path", "Original Path", "Path to the original/keeper file", True, True),
            ExportField("duplicate_path", "Duplicate Path", "Path to the duplicate file", True, True),
            ExportField("tag", "Tag", "Classification (duplicate/safe_duplicate/original)", True, True),
            ExportField("reason", "Reason", "Detection method (exact/near/similar)", True, True),
            ExportField("similarity_score", "Similarity Score", "Similarity percentage (0-100)", True, True),
            ExportField("file_hash", "File Hash", "MD5/SHA hash of the file", True, False),
            ExportField("perceptual_hash", "Perceptual Hash", "Perceptual hash for image comparison", True, False),
            ExportField("file_size", "File Size", "Size of duplicate file in bytes", True, False),
            ExportField("original_size", "Original Size", "Size of original file in bytes", True, False),
            ExportField("exif_match", "EXIF Match", "Whether EXIF data matches", True, False),
            ExportField("exif_differences", "EXIF Differences", "Description of EXIF differences", True, False),
            ExportField("camera_make", "Camera Make", "Camera manufacturer", True, False),
            ExportField("camera_model", "Camera Model", "Camera model", True, False),
            ExportField("date_taken", "Date Taken", "Photo capture date from EXIF", True, False),
            ExportField("resolution", "Resolution", "Image resolution (width x height)", True, False),
            ExportField("quality_score", "Quality Score", "Calculated quality metric", True, False),
            ExportField("compression_ratio", "Compression Ratio", "File compression ratio", True, False),
            ExportField("action_taken", "Action Taken", "What action was performed", True, True),
            ExportField("action_timestamp", "Action Timestamp", "When action was performed", True, False),
            ExportField("action_method", "Action Method", "How action was performed", True, False),
            ExportField("created_date", "Created Date", "File creation date", True, False),
            ExportField("modified_date", "Modified Date", "File modification date", True, False),
            ExportField("confidence_level", "Confidence Level", "Detection confidence (0-1)", True, False),
            ExportField("notes", "Notes", "Additional notes or comments", True, False)
        ]
        
    def get_enabled_fields(self) -> List[ExportField]:
        """Get list of enabled export fields."""
        return [field for field in self.available_fields if field.enabled]
        
    def set_field_enabled(self, field_name: str, enabled: bool):
        """Enable or disable a specific field."""
        for field in self.available_fields:
            if field.name == field_name:
                field.enabled = enabled
                break
                
    def export_to_csv(self, records: List[DuplicateRecord], file_path: str) -> bool:
        """
        Export records to CSV format.
        
        Args:
            records: List of duplicate records to export
            file_path: Output CSV file path
            
        Returns:
            True if export was successful
        """
        try:
            self.export_started.emit(len(records))
            
            enabled_fields = self.get_enabled_fields()
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=self.export_settings['csv_delimiter'])
                
                # Write header
                headers = [field.display_name for field in enabled_fields]
                writer.writerow(headers)
                
                # Write data rows
                for i, record in enumerate(records):
                    row = []
                    record_dict = asdict(record)
                    
                    for field in enabled_fields:
                        value = record_dict.get(field.name, '')
                        
                        # Format specific field types
                        if field.name in ['action_timestamp'] and value:
                            if isinstance(value, (int, float)):
                                value = datetime.fromtimestamp(value).strftime(
                                    self.export_settings['date_format']
                                )
                        elif field.name == 'file_size' and value:
                            value = f"{value:,}"  # Add thousands separators
                        elif field.name == 'similarity_score' and value is not None:
                            value = f"{value:.2f}"
                            
                        row.append(str(value) if value is not None else '')
                    
                    writer.writerow(row)
                    self.export_progress.emit(i + 1, f"Writing record {i + 1}")
                    
            self.export_completed.emit("CSV", file_path)
            return True
            
        except Exception as e:
            self.export_failed.emit(f"CSV export failed: {str(e)}")
            return False
            
    def export_to_json(self, records: List[DuplicateRecord], file_path: str) -> bool:
        """
        Export records to JSON format.
        
        Args:
            records: List of duplicate records to export
            file_path: Output JSON file path
            
        Returns:
            True if export was successful
        """
        try:
            self.export_started.emit(len(records))
            
            enabled_fields = self.get_enabled_fields()
            enabled_field_names = {field.name for field in enabled_fields}
            
            # Prepare data structure
            export_data = {
                'metadata': {
                    'export_timestamp': time.time(),
                    'export_date': datetime.now().strftime(self.export_settings['date_format']),
                    'total_records': len(records),
                    'exported_fields': [
                        {
                            'name': field.name,
                            'display_name': field.display_name,
                            'description': field.description
                        }
                        for field in enabled_fields
                    ],
                    'export_settings': self.export_settings.copy()
                },
                'records': []
            }
            
            # Process records
            for i, record in enumerate(records):
                record_dict = asdict(record)
                
                # Filter to enabled fields only
                filtered_record = {
                    key: value for key, value in record_dict.items()
                    if key in enabled_field_names
                }
                
                # Format timestamps
                if 'action_timestamp' in filtered_record and filtered_record['action_timestamp']:
                    timestamp = filtered_record['action_timestamp']
                    if isinstance(timestamp, (int, float)):
                        filtered_record['action_timestamp_formatted'] = datetime.fromtimestamp(
                            timestamp
                        ).strftime(self.export_settings['date_format'])
                
                export_data['records'].append(filtered_record)
                self.export_progress.emit(i + 1, f"Processing record {i + 1}")
                
            # Write JSON file
            with open(file_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(
                    export_data, 
                    jsonfile, 
                    indent=self.export_settings['json_indent'],
                    ensure_ascii=False,
                    default=str  # Handle datetime and other non-serializable objects
                )
                
            self.export_completed.emit("JSON", file_path)
            return True
            
        except Exception as e:
            self.export_failed.emit(f"JSON export failed: {str(e)}")
            return False
            
    def export_both_formats(self, records: List[DuplicateRecord], base_path: str) -> bool:
        """
        Export to both CSV and JSON formats.
        
        Args:
            records: List of duplicate records to export
            base_path: Base file path (without extension)
            
        Returns:
            True if both exports were successful
        """
        csv_path = f"{base_path}.csv"
        json_path = f"{base_path}.json"
        
        csv_success = self.export_to_csv(records, csv_path)
        json_success = self.export_to_json(records, json_path)
        
        return csv_success and json_success
        
    def create_sample_records(self, count: int = 5) -> List[DuplicateRecord]:
        """Create sample records for testing."""
        sample_records = []
        
        for i in range(count):
            record = DuplicateRecord(
                group_id=f"group_{i // 2 + 1}",
                original_path=f"/photos/vacation/IMG_{1000 + i}.jpg",
                duplicate_path=f"/photos/backup/IMG_{1000 + i}_copy.jpg",
                tag="safe_duplicate" if i % 3 == 0 else "duplicate",
                reason="exact" if i % 2 == 0 else "near",
                similarity_score=95.5 + (i * 1.2),
                file_hash=f"abcd{1000 + i}efgh",
                perceptual_hash=f"phash_{1000 + i}",
                file_size=2048000 + (i * 100000),
                original_size=2048000,
                exif_match=i % 2 == 0,
                exif_differences="Resolution difference" if i % 2 == 1 else None,
                camera_make="Canon" if i % 2 == 0 else "Nikon",
                camera_model=f"Camera Model {i + 1}",
                date_taken="2024-08-15 14:30:00",
                resolution=f"{1920 + i * 100}x{1080 + i * 50}",
                quality_score=0.85 + (i * 0.02),
                compression_ratio=0.75,
                action_taken="pending",
                action_timestamp=None,
                action_method=None,
                created_date="2024-08-15 14:30:00",
                modified_date="2024-08-15 14:30:00",
                confidence_level=0.9 + (i * 0.01),
                notes=f"Sample record {i + 1}"
            )
            sample_records.append(record)
            
        return sample_records


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
        
    class QComboBox:
        def __init__(self, *args): pass
        def addItems(self, *args): pass
        def currentText(self): return ""
        
    class QRadioButton:
        def __init__(self, *args): pass
        def isChecked(self): return False
        
    class QButtonGroup:
        def __init__(self, *args): pass
        def addButton(self, *args): pass
        
    class QCheckBox:
        def __init__(self, *args): pass
        def isChecked(self): return False
        def setChecked(self, *args): pass
        
    class QFileDialog:
        @staticmethod
        def getSaveFileName(*args): return ("test_export.csv", "")
        
    class QTableWidget:
        def __init__(self, *args): pass
        
    class QTableWidgetItem:
        def __init__(self, *args): pass
        
    class QTabWidget:
        def __init__(self, *args): pass
        
    class QWidget:
        def __init__(self, *args): pass
        
    class QSplitter:
        def __init__(self, *args): pass


class ExportConfigurationDialog(QDialog):
    """Dialog for configuring export options."""
    
    def __init__(self, exporter: ReportExporter, parent=None):
        super().__init__(parent)
        self.exporter = exporter
        self.selected_format = ExportFormat.CSV
        self.selected_scope = ExportScope.CURRENT_VIEW
        self.field_checkboxes = {}
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Export Configuration")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Export format selection
        format_group = QGroupBox("Export Format")
        format_layout = QVBoxLayout(format_group)
        
        self.format_group = QButtonGroup()
        self.csv_radio = QRadioButton("CSV (Comma-separated values)")
        self.json_radio = QRadioButton("JSON (JavaScript Object Notation)")
        self.both_radio = QRadioButton("Both CSV and JSON")
        
        self.csv_radio.setChecked(True)
        
        self.format_group.addButton(self.csv_radio)
        self.format_group.addButton(self.json_radio)
        self.format_group.addButton(self.both_radio)
        
        format_layout.addWidget(self.csv_radio)
        format_layout.addWidget(self.json_radio)
        format_layout.addWidget(self.both_radio)
        
        layout.addWidget(format_group)
        
        # Export scope selection
        scope_group = QGroupBox("Export Scope")
        scope_layout = QVBoxLayout(scope_group)
        
        self.scope_group = QButtonGroup()
        self.current_view_radio = QRadioButton("Current filtered view only")
        self.full_dataset_radio = QRadioButton("Full dataset (all groups)")
        self.selected_only_radio = QRadioButton("Selected files only")
        
        self.current_view_radio.setChecked(True)
        
        self.scope_group.addButton(self.current_view_radio)
        self.scope_group.addButton(self.full_dataset_radio)
        self.scope_group.addButton(self.selected_only_radio)
        
        scope_layout.addWidget(self.current_view_radio)
        scope_layout.addWidget(self.full_dataset_radio)
        scope_layout.addWidget(self.selected_only_radio)
        
        layout.addWidget(scope_group)
        
        # Field selection
        fields_group = QGroupBox("Export Fields")
        fields_layout = QVBoxLayout(fields_group)
        
        # Select all/none buttons
        field_buttons_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_none_btn = QPushButton("Select None")
        self.select_required_btn = QPushButton("Required Only")
        
        self.select_all_btn.clicked.connect(self.select_all_fields)
        self.select_none_btn.clicked.connect(self.select_no_fields)
        self.select_required_btn.clicked.connect(self.select_required_fields)
        
        field_buttons_layout.addWidget(self.select_all_btn)
        field_buttons_layout.addWidget(self.select_none_btn)
        field_buttons_layout.addWidget(self.select_required_btn)
        field_buttons_layout.addStretch()
        
        fields_layout.addLayout(field_buttons_layout)
        
        # Create checkboxes for each field
        for field in self.exporter.available_fields:
            checkbox = QCheckBox(f"{field.display_name}")
            checkbox.setChecked(field.enabled)
            checkbox.setToolTip(field.description)
            
            if field.required:
                checkbox.setText(f"{field.display_name} (Required)")
                checkbox.setEnabled(False)  # Required fields cannot be unchecked
                
            self.field_checkboxes[field.name] = checkbox
            fields_layout.addWidget(checkbox)
            
        layout.addWidget(fields_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.accept)
        self.export_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        button_layout.addWidget(self.export_btn)
        
        layout.addLayout(button_layout)
        
    def get_selected_format(self) -> ExportFormat:
        """Get the selected export format."""
        if self.csv_radio.isChecked():
            return ExportFormat.CSV
        elif self.json_radio.isChecked():
            return ExportFormat.JSON
        else:
            return ExportFormat.BOTH
            
    def get_selected_scope(self) -> ExportScope:
        """Get the selected export scope."""
        if self.current_view_radio.isChecked():
            return ExportScope.CURRENT_VIEW
        elif self.full_dataset_radio.isChecked():
            return ExportScope.FULL_DATASET
        else:
            return ExportScope.SELECTED_ONLY
            
    def get_selected_fields(self) -> List[str]:
        """Get list of selected field names."""
        selected = []
        for field_name, checkbox in self.field_checkboxes.items():
            if checkbox.isChecked():
                selected.append(field_name)
        return selected
        
    def select_all_fields(self):
        """Select all export fields."""
        for checkbox in self.field_checkboxes.values():
            if checkbox.isEnabled():
                checkbox.setChecked(True)
                
    def select_no_fields(self):
        """Deselect all non-required fields."""
        for field_name, checkbox in self.field_checkboxes.items():
            field = next((f for f in self.exporter.available_fields if f.name == field_name), None)
            if field and not field.required and checkbox.isEnabled():
                checkbox.setChecked(False)
                
    def select_required_fields(self):
        """Select only required fields."""
        for field_name, checkbox in self.field_checkboxes.items():
            field = next((f for f in self.exporter.available_fields if f.name == field_name), None)
            if field:
                checkbox.setChecked(field.required)
                
    def apply_field_selection(self):
        """Apply the selected fields to the exporter."""
        for field_name, checkbox in self.field_checkboxes.items():
            self.exporter.set_field_enabled(field_name, checkbox.isChecked())


class ExportProgressDialog(QDialog):
    """Dialog showing export progress."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Exporting Data...")
        self.setMinimumSize(400, 150)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("Preparing export...")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.detail_label = QLabel("")
        self.detail_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.detail_label)
        
    def update_progress(self, current: int, total: int, description: str = ""):
        """Update progress display."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"Exporting... ({current}/{total})")
        
        if description:
            self.detail_label.setText(description)