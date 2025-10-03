"""
Step 28 - Developer Panel UI
Hidden developer panel for performance profiling and threshold tuning.
"""

import sys
from typing import Dict, Any, Optional, List
from dataclasses import asdict

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, 
        QTableWidget, QTableWidgetItem, QSlider, QSpinBox, QDoubleSpinBox,
        QGroupBox, QFormLayout, QPushButton, QTextEdit, QSplitter,
        QHeaderView, QProgressBar, QCheckBox, QComboBox, QFrame
    )
    from PySide6.QtCore import Qt, QTimer, Signal, QThread, pyqtSignal
    from PySide6.QtGui import QFont, QColor, QPalette
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    # Define dummy classes for non-Qt environments
    class QWidget: pass
    class QVBoxLayout: pass
    class QHBoxLayout: pass
    class QTabWidget: pass
    class QLabel: pass
    class QTableWidget: pass
    class QSlider: pass
    class QSpinBox: pass

# Import performance profiling components
if QT_AVAILABLE:
    try:
        from core.profiler import get_profiler, get_threshold_tuner, TimingData, ThresholdConfig
    except ImportError:
        try:
            from src.core.profiler import get_profiler, get_threshold_tuner, TimingData, ThresholdConfig
        except ImportError:
            # Fallback definitions for testing
            class TimingData:
                def __init__(self, operation, start_time, end_time, duration, metadata=None):
                    self.operation = operation
                    self.start_time = start_time
                    self.end_time = end_time
                    self.duration = duration
                    self.metadata = metadata or {}
            
            class ThresholdConfig:
                def __init__(self):
                    self.perceptual_hash_threshold = 5
                    self.orb_match_threshold = 0.7
                    self.size_difference_threshold = 0.1
                    self.minimum_matches = 10
            
            def get_profiler():
                return None
            
            def get_threshold_tuner():
                return None
    class QTimer: pass
    class Signal: pass
    class QThread: pass
    pyqtSignal = lambda: None

if QT_AVAILABLE:
    from core.profiler import get_profiler, get_threshold_tuner, ThresholdConfig, TimingData


class PerformanceMonitorWidget(QWidget):
    """Widget for displaying performance monitoring data."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.profiler = get_profiler()
        self.setup_ui()
        self.setup_timer()
        
    def setup_ui(self):
        """Setup the performance monitor UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Performance Monitor")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #2196F3; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Controls
        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)
        
        self.enable_checkbox = QCheckBox("Enable Profiling")
        self.enable_checkbox.setChecked(True)
        self.enable_checkbox.toggled.connect(self.toggle_profiling)
        controls_layout.addWidget(self.enable_checkbox)
        
        self.reset_button = QPushButton("Reset Stats")
        self.reset_button.clicked.connect(self.reset_stats)
        controls_layout.addWidget(self.reset_button)
        
        controls_layout.addStretch()
        layout.addWidget(controls_frame)
        
        # Performance table
        self.perf_table = QTableWidget()
        self.perf_table.setColumnCount(8)
        self.perf_table.setHorizontalHeaderLabels([
            'Operation', 'Count', 'Total (ms)', 'Avg (ms)', 
            'Min (ms)', 'Max (ms)', 'Recent Avg (ms)', 'P95 (ms)'
        ])
        
        # Set column widths
        header = self.perf_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 8):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.perf_table)
        
        # Recent activity
        activity_label = QLabel("Recent Activity")
        activity_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(activity_label)
        
        self.activity_text = QTextEdit()
        self.activity_text.setMaximumHeight(100)
        self.activity_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.activity_text)
        
        # Add profiler listener
        self.profiler.add_listener(self.on_timing_event)
    
    def setup_timer(self):
        """Setup update timer."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # Update every second
    
    def toggle_profiling(self, enabled: bool):
        """Toggle profiling on/off."""
        self.profiler.set_enabled(enabled)
        
    def reset_stats(self):
        """Reset all performance statistics."""
        self.profiler.reset_stats()
        self.activity_text.clear()
        self.update_display()
    
    def on_timing_event(self, operation: str, timing_data):
        """Handle timing events from profiler."""
        # timing_data is a TimingData object but we avoid the type annotation to prevent import issues
        duration_ms = timing_data.duration * 1000  # Convert to milliseconds
        message = f"[{operation}] {duration_ms:.2f}ms"
        
        if hasattr(timing_data, 'metadata') and timing_data.metadata:
            metadata_str = ", ".join(f"{k}={v}" for k, v in timing_data.metadata.items())
            message += f" ({metadata_str})"
        
        # Add to activity log
        self.activity_text.append(message)
        
        # Keep only last 50 lines
        document = self.activity_text.document()
        if document.blockCount() > 50:
            cursor = self.activity_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
    
    def update_display(self):
        """Update the performance display."""
        stats = self.profiler.get_stats()
        
        self.perf_table.setRowCount(len(stats))
        
        for row, (operation, stat) in enumerate(stats.items()):
            items = [
                QTableWidgetItem(operation),
                QTableWidgetItem(str(stat.count)),
                QTableWidgetItem(f"{stat.total_time * 1000:.2f}"),
                QTableWidgetItem(f"{stat.avg_time * 1000:.2f}"),
                QTableWidgetItem(f"{stat.min_time * 1000:.2f}"),
                QTableWidgetItem(f"{stat.max_time * 1000:.2f}"),
                QTableWidgetItem(f"{stat.recent_avg * 1000:.2f}"),
                QTableWidgetItem(f"{stat.recent_p95 * 1000:.2f}"),
            ]
            
            for col, item in enumerate(items):
                # Color code based on performance
                if col > 2:  # Timing columns
                    value = float(item.text())
                    if value > 1000:  # > 1 second
                        item.setBackground(QColor(255, 200, 200))  # Light red
                    elif value > 100:  # > 100ms
                        item.setBackground(QColor(255, 255, 200))  # Light yellow
                    else:
                        item.setBackground(QColor(200, 255, 200))  # Light green
                
                self.perf_table.setItem(row, col, item)


class ThresholdTunerWidget(QWidget):
    """Widget for tuning duplicate detection thresholds."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tuner = get_threshold_tuner()
        self.setup_ui()
        self.setup_sample_data()
        
        # Listen for threshold changes
        self.tuner.add_listener(self.on_threshold_change)
    
    def setup_ui(self):
        """Setup the threshold tuner UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Threshold Tuner")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #FF9800; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Split layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - controls
        controls_widget = self.create_controls_panel()
        splitter.addWidget(controls_widget)
        
        # Right panel - results
        results_widget = self.create_results_panel()
        splitter.addWidget(results_widget)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
    
    def create_controls_panel(self) -> QWidget:
        """Create the threshold controls panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Threshold controls
        thresholds_group = QGroupBox("Detection Thresholds")
        thresholds_layout = QFormLayout(thresholds_group)
        
        # Perceptual hash threshold
        self.hash_threshold_spin = QSpinBox()
        self.hash_threshold_spin.setRange(0, 20)
        self.hash_threshold_spin.setValue(self.tuner.config.perceptual_hash_threshold)
        self.hash_threshold_spin.valueChanged.connect(
            lambda v: self.tuner.update_threshold('perceptual_hash_threshold', v)
        )
        thresholds_layout.addRow("Perceptual Hash Distance:", self.hash_threshold_spin)
        
        # ORB match threshold
        self.orb_threshold_spin = QDoubleSpinBox()
        self.orb_threshold_spin.setRange(0.0, 1.0)
        self.orb_threshold_spin.setSingleStep(0.05)
        self.orb_threshold_spin.setDecimals(2)
        self.orb_threshold_spin.setValue(self.tuner.config.orb_match_threshold)
        self.orb_threshold_spin.valueChanged.connect(
            lambda v: self.tuner.update_threshold('orb_match_threshold', v)
        )
        thresholds_layout.addRow("ORB Match Ratio:", self.orb_threshold_spin)
        
        # Size difference threshold
        self.size_threshold_spin = QDoubleSpinBox()
        self.size_threshold_spin.setRange(0.0, 1.0)
        self.size_threshold_spin.setSingleStep(0.05)
        self.size_threshold_spin.setDecimals(2)
        self.size_threshold_spin.setValue(self.tuner.config.size_difference_threshold)
        self.size_threshold_spin.valueChanged.connect(
            lambda v: self.tuner.update_threshold('size_difference_threshold', v)
        )
        thresholds_layout.addRow("Max Size Difference:", self.size_threshold_spin)
        
        # Minimum matches
        self.min_matches_spin = QSpinBox()
        self.min_matches_spin.setRange(1, 100)
        self.min_matches_spin.setValue(self.tuner.config.minimum_matches)
        self.min_matches_spin.valueChanged.connect(
            lambda v: self.tuner.update_threshold('minimum_matches', v)
        )
        thresholds_layout.addRow("Minimum ORB Matches:", self.min_matches_spin)
        
        layout.addWidget(thresholds_group)
        
        # Sample data controls
        sample_group = QGroupBox("Sample Data")
        sample_layout = QVBoxLayout(sample_group)
        
        self.generate_sample_button = QPushButton("Generate Sample Data")
        self.generate_sample_button.clicked.connect(self.generate_sample_data)
        sample_layout.addWidget(self.generate_sample_button)
        
        self.sample_count_label = QLabel("Sample count: 0")
        sample_layout.addWidget(self.sample_count_label)
        
        layout.addWidget(sample_group)
        
        # Preset configurations
        presets_group = QGroupBox("Presets")
        presets_layout = QVBoxLayout(presets_group)
        
        preset_buttons = [
            ("Strict (Low false positives)", self.apply_strict_preset),
            ("Balanced (Default)", self.apply_balanced_preset),
            ("Loose (High recall)", self.apply_loose_preset),
        ]
        
        for name, handler in preset_buttons:
            button = QPushButton(name)
            button.clicked.connect(handler)
            presets_layout.addWidget(button)
        
        layout.addWidget(presets_group)
        layout.addStretch()
        
        return widget
    
    def create_results_panel(self) -> QWidget:
        """Create the results display panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Results summary
        results_group = QGroupBox("Detection Results")
        results_layout = QFormLayout(results_group)
        
        self.group_count_label = QLabel("0")
        self.group_count_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #4CAF50;")
        results_layout.addRow("Duplicate Groups:", self.group_count_label)
        
        self.total_duplicates_label = QLabel("0")
        self.total_duplicates_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2196F3;")
        results_layout.addRow("Total Duplicates:", self.total_duplicates_label)
        
        self.detection_rate_label = QLabel("0%")
        self.detection_rate_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #FF9800;")
        results_layout.addRow("Detection Rate:", self.detection_rate_label)
        
        layout.addWidget(results_group)
        
        # Groups detail
        groups_label = QLabel("Duplicate Groups")
        groups_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(groups_label)
        
        self.groups_text = QTextEdit()
        self.groups_text.setFont(QFont("Consolas", 9))
        self.groups_text.setMaximumHeight(200)
        layout.addWidget(self.groups_text)
        
        # Performance impact
        perf_group = QGroupBox("Performance Impact")
        perf_layout = QFormLayout(perf_group)
        
        self.recompute_time_label = QLabel("0 ms")
        perf_layout.addRow("Last Recompute Time:", self.recompute_time_label)
        
        layout.addWidget(perf_group)
        layout.addStretch()
        
        return widget
    
    def setup_sample_data(self):
        """Setup initial sample data."""
        self.generate_sample_data()
    
    def generate_sample_data(self):
        """Generate sample data for testing."""
        # Create mock sample data
        sample_data = []
        
        # Add some similar images (different sizes, similar hashes)
        for i in range(5):
            sample_data.append({
                'path': f'/path/to/image_{i}.jpg',
                'size': 1000000 + (i * 50000),  # Varying sizes
                'perceptual_hash': 'abcd1234' + str(i),  # Similar hashes
                'orb_features': f'mock_orb_{i}'
            })
        
        # Add some very similar images (duplicates)
        for i in range(3):
            sample_data.append({
                'path': f'/path/to/duplicate_{i}.jpg',
                'size': 2000000,  # Same size
                'perceptual_hash': 'efgh5678',  # Same hash
                'orb_features': 'mock_orb_duplicate'
            })
        
        # Add some different images
        for i in range(7):
            sample_data.append({
                'path': f'/path/to/unique_{i}.jpg',
                'size': 500000 + (i * 100000),
                'perceptual_hash': f'unique{i:04d}',
                'orb_features': f'unique_orb_{i}'
            })
        
        self.tuner.set_sample_data(sample_data)
        self.sample_count_label.setText(f"Sample count: {len(sample_data)}")
    
    def apply_strict_preset(self):
        """Apply strict detection preset."""
        config = ThresholdConfig(
            perceptual_hash_threshold=2,
            orb_match_threshold=0.8,
            size_difference_threshold=0.05,
            minimum_matches=15
        )
        self.apply_config(config)
    
    def apply_balanced_preset(self):
        """Apply balanced detection preset."""
        config = ThresholdConfig(
            perceptual_hash_threshold=5,
            orb_match_threshold=0.7,
            size_difference_threshold=0.1,
            minimum_matches=10
        )
        self.apply_config(config)
    
    def apply_loose_preset(self):
        """Apply loose detection preset."""
        config = ThresholdConfig(
            perceptual_hash_threshold=8,
            orb_match_threshold=0.6,
            size_difference_threshold=0.2,
            minimum_matches=5
        )
        self.apply_config(config)
    
    def apply_config(self, config):
        """Apply a threshold configuration."""
        # config is a ThresholdConfig object but we avoid the type annotation to prevent import issues
        # Update UI controls
        self.hash_threshold_spin.setValue(config.perceptual_hash_threshold)
        self.orb_threshold_spin.setValue(config.orb_match_threshold)
        self.size_threshold_spin.setValue(config.size_difference_threshold)
        self.min_matches_spin.setValue(config.minimum_matches)
        
        # Update tuner
        self.tuner.update_config(config)
    
    def on_threshold_change(self, config, group_count: int):
        """Handle threshold configuration changes."""
        # config is a ThresholdConfig object but we avoid the type annotation to prevent import issues
        total_duplicates = self.tuner.get_total_duplicates()
        sample_count = len(self.tuner._sample_data)
        
        # Update labels
        self.group_count_label.setText(str(group_count))
        self.total_duplicates_label.setText(str(total_duplicates))
        
        if sample_count > 0:
            detection_rate = (total_duplicates / sample_count) * 100
            self.detection_rate_label.setText(f"{detection_rate:.1f}%")
        
        # Update groups display
        groups = self.tuner.get_current_groups()
        groups_text = ""
        
        for i, group in enumerate(groups):
            groups_text += f"Group {i+1}: {len(group)} items\n"
            for idx in group:
                if idx < len(self.tuner._sample_data):
                    item = self.tuner._sample_data[idx]
                    path = item.get('path', f'Item {idx}')
                    groups_text += f"  - {path}\n"
            groups_text += "\n"
        
        self.groups_text.setText(groups_text)


class DeveloperPanel(QTabWidget):
    """Main developer panel with performance monitoring and threshold tuning."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Developer Panel - Performance & Tuning")
        self.setMinimumSize(800, 600)
        self.setup_ui()
        
        # Apply dark theme
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: white;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #555;
            }
            QWidget {
                background-color: #2b2b2b;
                color: white;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
    
    def setup_ui(self):
        """Setup the developer panel UI."""
        # Performance monitoring tab
        self.perf_widget = PerformanceMonitorWidget(self)
        self.addTab(self.perf_widget, "Performance Monitor")
        
        # Threshold tuning tab
        self.threshold_widget = ThresholdTunerWidget(self)
        self.addTab(self.threshold_widget, "Threshold Tuner")


def show_developer_panel(parent=None) -> Optional[DeveloperPanel]:
    """Show the developer panel."""
    if not QT_AVAILABLE:
        print("Developer panel requires PySide6")
        return None
    
    panel = DeveloperPanel(parent)
    panel.show()
    return panel


# Handle Qt not available case
if not QT_AVAILABLE:
    class DeveloperPanel:
        def __init__(self, parent=None):
            pass
    
    def show_developer_panel(parent=None):
        print("Developer panel not available (Qt not available)")
        return None