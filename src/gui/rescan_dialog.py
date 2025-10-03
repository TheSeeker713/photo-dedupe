"""
Rescan GUI component for Step 23 - Rescan & Delta Updates.

This module provides:
- Rescan mode selection interface
- Progress monitoring for rescan operations
- Statistics display and recommendations
- Full rebuild options with data preservation controls
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QProgressBar, QTextEdit, QGroupBox, QRadioButton, QCheckBox,
        QFrame, QSizePolicy, QSpacerItem, QButtonGroup, QTabWidget,
        QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea
    )
    from PySide6.QtCore import Qt, Signal, QTimer, QThread, pyqtSignal
    from PySide6.QtGui import QFont, QIcon, QPalette
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QWidget = object
    Signal = lambda *args, **kwargs: None


if QT_AVAILABLE:
    class RescanWorker(QThread):
        """Worker thread for rescan operations."""
        
        progress_updated = pyqtSignal(str, int)
        rescan_completed = pyqtSignal(dict)
        rescan_failed = pyqtSignal(str)
        
        def __init__(self, rescan_manager, mode, scan_paths, options=None):
            super().__init__()
            self.rescan_manager = rescan_manager
            self.mode = mode
            self.scan_paths = scan_paths
            self.options = options or {}
            self.logger = logging.getLogger(__name__)
        
        def run(self):
            """Run rescan operation in background thread."""
            try:
                def progress_callback(message: str, progress: int):
                    self.progress_updated.emit(message, progress)
                
                if self.mode == "delta_only":
                    stats = self.rescan_manager.perform_delta_rescan(
                        self.scan_paths, progress_callback
                    )
                elif self.mode == "missing_features":
                    stats = self.rescan_manager.perform_missing_features_rescan(
                        progress_callback
                    )
                elif self.mode == "full_rebuild":
                    stats = self.rescan_manager.perform_full_rebuild(
                        self.scan_paths,
                        preserve_overrides=self.options.get('preserve_overrides', True),
                        preserve_groups=self.options.get('preserve_groups', True),
                        progress_callback=progress_callback
                    )
                else:
                    raise ValueError(f"Unknown rescan mode: {self.mode}")
                
                self.rescan_completed.emit(stats.__dict__)
                
            except Exception as e:
                self.logger.error(f"Rescan failed: {e}")
                self.rescan_failed.emit(str(e))
    
    
    class RescanModeSelector(QGroupBox):
        """Widget for selecting rescan mode and options."""
        
        mode_changed = Signal(str)
        
        def __init__(self, parent=None):
            super().__init__("Rescan Mode", parent)
            self.logger = logging.getLogger(__name__)
            self._setup_ui()
        
        def _setup_ui(self):
            """Setup the mode selector UI."""
            layout = QVBoxLayout(self)
            
            # Mode selection
            self.mode_group = QButtonGroup(self)
            
            # Delta rescan option
            self.delta_radio = QRadioButton("Delta Rescan (Recommended)")
            self.delta_radio.setChecked(True)
            self.delta_radio.setToolTip("Only process new and changed files - fastest option")
            layout.addWidget(self.delta_radio)
            
            delta_desc = QLabel("• Only processes new and changed files\n• Preserves existing features and thumbnails\n• Fastest rescan option")
            delta_desc.setStyleSheet("color: #666; margin-left: 20px; font-size: 9pt;")
            layout.addWidget(delta_desc)
            
            # Missing features option
            self.missing_radio = QRadioButton("Process Missing Features")
            self.missing_radio.setToolTip("Process files missing features or thumbnails")
            layout.addWidget(self.missing_radio)
            
            missing_desc = QLabel("• Processes files missing features or thumbnails\n• Useful after interrupted operations\n• Moderate processing time")
            missing_desc.setStyleSheet("color: #666; margin-left: 20px; font-size: 9pt;")
            layout.addWidget(missing_desc)
            
            # Full rebuild option
            self.rebuild_radio = QRadioButton("Full Rebuild")
            self.rebuild_radio.setToolTip("Complete rebuild of all features and thumbnails")
            layout.addWidget(self.rebuild_radio)
            
            rebuild_desc = QLabel("• Clears and rebuilds all features and thumbnails\n• Preserves user data (groups, overrides)\n• Longest processing time")
            rebuild_desc.setStyleSheet("color: #666; margin-left: 20px; font-size: 9pt;")
            layout.addWidget(rebuild_desc)
            
            # Add radio buttons to group
            self.mode_group.addButton(self.delta_radio, 0)
            self.mode_group.addButton(self.missing_radio, 1)
            self.mode_group.addButton(self.rebuild_radio, 2)
            
            # Full rebuild options
            self.rebuild_options = QGroupBox("Full Rebuild Options")
            rebuild_options_layout = QVBoxLayout(self.rebuild_options)
            
            self.preserve_groups_cb = QCheckBox("Preserve duplicate groups")
            self.preserve_groups_cb.setChecked(True)
            self.preserve_groups_cb.setToolTip("Keep existing duplicate group assignments")
            rebuild_options_layout.addWidget(self.preserve_groups_cb)
            
            self.preserve_overrides_cb = QCheckBox("Preserve manual overrides")
            self.preserve_overrides_cb.setChecked(True)
            self.preserve_overrides_cb.setToolTip("Keep manual original selection overrides")
            rebuild_options_layout.addWidget(self.preserve_overrides_cb)
            
            layout.addWidget(self.rebuild_options)
            
            # Initially hide rebuild options
            self.rebuild_options.setVisible(False)
            
            # Connect signals
            self.mode_group.buttonToggled.connect(self._on_mode_changed)
        
        def _on_mode_changed(self, button, checked):
            """Handle mode selection change."""
            if checked:
                # Show/hide rebuild options
                show_rebuild_options = button == self.rebuild_radio
                self.rebuild_options.setVisible(show_rebuild_options)
                
                # Emit mode change signal
                if button == self.delta_radio:
                    self.mode_changed.emit("delta_only")
                elif button == self.missing_radio:
                    self.mode_changed.emit("missing_features")
                elif button == self.rebuild_radio:
                    self.mode_changed.emit("full_rebuild")
        
        def get_selected_mode(self) -> str:
            """Get currently selected rescan mode."""
            if self.delta_radio.isChecked():
                return "delta_only"
            elif self.missing_radio.isChecked():
                return "missing_features"
            elif self.rebuild_radio.isChecked():
                return "full_rebuild"
            return "delta_only"
        
        def get_rebuild_options(self) -> Dict[str, bool]:
            """Get full rebuild options."""
            return {
                'preserve_groups': self.preserve_groups_cb.isChecked(),
                'preserve_overrides': self.preserve_overrides_cb.isChecked()
            }
        
        def set_recommended_mode(self, mode: str, reason: str = ""):
            """Set recommended mode based on analysis."""
            if mode == "delta_only":
                self.delta_radio.setChecked(True)
            elif mode == "missing_features":
                self.missing_radio.setChecked(True)
            elif mode == "full_rebuild":
                self.rebuild_radio.setChecked(True)
            
            if reason:
                self.setToolTip(f"Recommended: {reason}")
    
    
    class RescanProgressWidget(QWidget):
        """Widget for displaying rescan progress."""
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.logger = logging.getLogger(__name__)
            self._setup_ui()
        
        def _setup_ui(self):
            """Setup progress display UI."""
            layout = QVBoxLayout(self)
            
            # Status label
            self.status_label = QLabel("Ready to rescan")
            font = QFont()
            font.setBold(True)
            self.status_label.setFont(font)
            layout.addWidget(self.status_label)
            
            # Progress bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            layout.addWidget(self.progress_bar)
            
            # Progress message
            self.progress_message = QLabel("")
            self.progress_message.setStyleSheet("color: #666; font-size: 9pt;")
            layout.addWidget(self.progress_message)
            
            # Statistics display
            self.stats_widget = QTextEdit()
            self.stats_widget.setMaximumHeight(150)
            self.stats_widget.setStyleSheet("""
                QTextEdit {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    font-family: monospace;
                    font-size: 9pt;
                }
            """)
            self.stats_widget.setVisible(False)
            layout.addWidget(self.stats_widget)
        
        def start_progress(self, mode: str):
            """Start progress display."""
            mode_names = {
                "delta_only": "Delta Rescan",
                "missing_features": "Missing Features",
                "full_rebuild": "Full Rebuild"
            }
            
            self.status_label.setText(f"Running {mode_names.get(mode, mode)}...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
            self.progress_message.setText("Initializing...")
            self.stats_widget.setVisible(False)
        
        def update_progress(self, message: str, progress: int):
            """Update progress display."""
            self.progress_message.setText(message)
            
            if progress >= 0:
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(progress)
        
        def complete_progress(self, stats: Dict[str, Any]):
            """Complete progress and show statistics."""
            self.status_label.setText("Rescan completed successfully")
            self.progress_bar.setVisible(False)
            self.progress_message.setText("")
            
            # Format and display statistics
            stats_text = self._format_rescan_stats(stats)
            self.stats_widget.setPlainText(stats_text)
            self.stats_widget.setVisible(True)
        
        def fail_progress(self, error: str):
            """Show failure state."""
            self.status_label.setText("Rescan failed")
            self.progress_bar.setVisible(False)
            self.progress_message.setText(f"Error: {error}")
            self.stats_widget.setVisible(False)
        
        def _format_rescan_stats(self, stats: Dict[str, Any]) -> str:
            """Format rescan statistics for display."""
            lines = [
                f"RESCAN STATISTICS - {stats.get('mode', 'Unknown').upper()}",
                "=" * 50,
                ""
            ]
            
            # Duration
            total_duration = stats.get('total_duration', 0)
            lines.append(f"Total Duration: {total_duration:.2f} seconds")
            lines.append("")
            
            # File statistics
            lines.extend([
                "FILE PROCESSING:",
                f"  Files Scanned: {stats.get('files_scanned', 0):,}",
                f"  Files New: {stats.get('files_new', 0):,}",
                f"  Files Changed: {stats.get('files_changed', 0):,}",
                f"  Files Unchanged: {stats.get('files_unchanged', 0):,}",
                f"  Files Missing: {stats.get('files_missing', 0):,}",
                f"  Files Processed: {stats.get('files_processed', 0):,}",
                ""
            ])
            
            # Features and thumbnails
            lines.extend([
                "FEATURES & THUMBNAILS:",
                f"  Features Extracted: {stats.get('features_extracted', 0):,}",
                f"  Features Reused: {stats.get('features_reused', 0):,}",
                f"  Thumbnails Created: {stats.get('thumbnails_created', 0):,}",
                f"  Thumbnails Reused: {stats.get('thumbnails_reused', 0):,}",
                ""
            ])
            
            # Rebuild specific stats
            if stats.get('mode') == 'full_rebuild':
                lines.extend([
                    "REBUILD OPERATIONS:",
                    f"  Features Cleared: {stats.get('features_cleared', 0):,}",
                    f"  Thumbnails Cleared: {stats.get('thumbnails_cleared', 0):,}",
                    f"  Groups Preserved: {stats.get('groups_preserved', 0):,}",
                    f"  Overrides Preserved: {stats.get('overrides_preserved', 0):,}",
                    ""
                ])
            
            # Performance metrics
            speed = stats.get('files_processed', 0) / max(total_duration, 0.001)
            efficiency = ((stats.get('features_reused', 0) + stats.get('thumbnails_reused', 0)) / 
                         max(stats.get('features_extracted', 0) + stats.get('features_reused', 0) + 
                             stats.get('thumbnails_created', 0) + stats.get('thumbnails_reused', 0), 1)) * 100
            
            lines.extend([
                "PERFORMANCE:",
                f"  Processing Speed: {speed:.1f} files/second",
                f"  Reuse Efficiency: {efficiency:.1f}%",
                ""
            ])
            
            # Errors
            errors = stats.get('errors', [])
            if errors:
                lines.extend([
                    f"ERRORS ({len(errors)}):",
                ] + [f"  • {error}" for error in errors[:10]])  # Show first 10 errors
                
                if len(errors) > 10:
                    lines.append(f"  ... and {len(errors) - 10} more errors")
            else:
                lines.append("No errors occurred")
            
            return "\n".join(lines)
    
    
    class RescanRecommendationsWidget(QWidget):
        """Widget for showing rescan recommendations."""
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.logger = logging.getLogger(__name__)
            self._setup_ui()
        
        def _setup_ui(self):
            """Setup recommendations display UI."""
            layout = QVBoxLayout(self)
            
            # Title
            title = QLabel("Rescan Recommendations")
            font = QFont()
            font.setBold(True)
            font.setPointSize(12)
            title.setFont(font)
            layout.addWidget(title)
            
            # Recommendations display
            self.recommendations_text = QLabel()
            self.recommendations_text.setWordWrap(True)
            self.recommendations_text.setStyleSheet("""
                QLabel {
                    background-color: #e3f2fd;
                    border: 1px solid #bbdefb;
                    border-radius: 4px;
                    padding: 12px;
                    margin: 8px 0px;
                }
            """)
            layout.addWidget(self.recommendations_text)
            
            # Database statistics table
            self.stats_table = QTableWidget()
            self.stats_table.setMaximumHeight(200)
            layout.addWidget(self.stats_table)
        
        def update_recommendations(self, recommendations: Dict[str, Any]):
            """Update recommendations display."""
            # Format recommendation text
            mode = recommendations.get('recommended_mode', 'delta_only')
            reasons = recommendations.get('reasons', [])
            estimated_files = recommendations.get('estimated_files_to_process', 0)
            
            mode_names = {
                'delta_only': 'Delta Rescan',
                'missing_features': 'Process Missing Features',
                'full_rebuild': 'Full Rebuild'
            }
            
            text_lines = [
                f"📋 Recommended Mode: {mode_names.get(mode, mode)}",
                f"📊 Estimated files to process: {estimated_files:,}",
                ""
            ]
            
            if reasons:
                text_lines.append("📝 Reasons:")
                text_lines.extend([f"  • {reason}" for reason in reasons])
            
            self.recommendations_text.setText("\n".join(text_lines))
            
            # Update statistics table
            self._update_stats_table(recommendations.get('database_stats', {}))
        
        def _update_stats_table(self, stats: Dict[str, Any]):
            """Update database statistics table."""
            self.stats_table.setRowCount(4)
            self.stats_table.setColumnCount(2)
            self.stats_table.setHorizontalHeaderLabels(["Metric", "Count"])
            
            stats_items = [
                ("Active Files", stats.get('active_files', 0)),
                ("Features", stats.get('features_count', 0)),
                ("Thumbnails", stats.get('thumbs_count', 0)),
                ("Groups", stats.get('groups_count', 0))
            ]
            
            for row, (metric, count) in enumerate(stats_items):
                self.stats_table.setItem(row, 0, QTableWidgetItem(metric))
                self.stats_table.setItem(row, 1, QTableWidgetItem(f"{count:,}"))
            
            # Resize columns to content
            self.stats_table.horizontalHeader().setStretchLastSection(True)
            self.stats_table.resizeColumnsToContents()
    
    
    class RescanDialog(QWidget):
        """Main rescan dialog widget."""
        
        rescan_completed = Signal(dict)
        
        def __init__(self, rescan_manager, scan_paths: List[Path], parent=None):
            super().__init__(parent)
            self.rescan_manager = rescan_manager
            self.scan_paths = scan_paths
            self.logger = logging.getLogger(__name__)
            self.rescan_worker = None
            
            self._setup_ui()
            self._load_recommendations()
        
        def _setup_ui(self):
            """Setup the rescan dialog UI."""
            self.setWindowTitle("Rescan Files")
            self.setMinimumSize(600, 500)
            
            layout = QVBoxLayout(self)
            
            # Create tab widget
            self.tab_widget = QTabWidget()
            layout.addWidget(self.tab_widget)
            
            # Recommendations tab
            recommendations_tab = QWidget()
            recommendations_layout = QVBoxLayout(recommendations_tab)
            
            self.recommendations_widget = RescanRecommendationsWidget()
            recommendations_layout.addWidget(self.recommendations_widget)
            
            self.tab_widget.addTab(recommendations_tab, "📊 Analysis")
            
            # Rescan tab
            rescan_tab = QWidget()
            rescan_layout = QVBoxLayout(rescan_tab)
            
            # Mode selector
            self.mode_selector = RescanModeSelector()
            self.mode_selector.mode_changed.connect(self._on_mode_changed)
            rescan_layout.addWidget(self.mode_selector)
            
            # Progress widget
            self.progress_widget = RescanProgressWidget()
            rescan_layout.addWidget(self.progress_widget)
            
            # Spacer
            rescan_layout.addStretch()
            
            self.tab_widget.addTab(rescan_tab, "🔄 Rescan")
            
            # Button layout
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            self.start_button = QPushButton("Start Rescan")
            self.start_button.clicked.connect(self._start_rescan)
            button_layout.addWidget(self.start_button)
            
            self.cancel_button = QPushButton("Cancel")
            self.cancel_button.clicked.connect(self.close)
            button_layout.addWidget(self.cancel_button)
            
            layout.addLayout(button_layout)
        
        def _load_recommendations(self):
            """Load rescan recommendations."""
            try:
                recommendations = self.rescan_manager.get_rescan_recommendations()
                self.recommendations_widget.update_recommendations(recommendations)
                
                # Set recommended mode
                recommended_mode = recommendations.get('recommended_mode')
                if recommended_mode:
                    reasons = recommendations.get('reasons', [])
                    reason_text = "; ".join(reasons) if reasons else ""
                    self.mode_selector.set_recommended_mode(recommended_mode.value, reason_text)
                
            except Exception as e:
                self.logger.error(f"Failed to load recommendations: {e}")
        
        def _on_mode_changed(self, mode: str):
            """Handle rescan mode change."""
            # Could update estimated time/files here
            pass
        
        def _start_rescan(self):
            """Start the rescan operation."""
            if self.rescan_worker and self.rescan_worker.isRunning():
                return
            
            mode = self.mode_selector.get_selected_mode()
            options = self.mode_selector.get_rebuild_options() if mode == "full_rebuild" else {}
            
            # Switch to rescan tab
            self.tab_widget.setCurrentIndex(1)
            
            # Disable start button
            self.start_button.setEnabled(False)
            self.start_button.setText("Rescanning...")
            
            # Start progress
            self.progress_widget.start_progress(mode)
            
            # Create and start worker
            self.rescan_worker = RescanWorker(
                self.rescan_manager, mode, self.scan_paths, options
            )
            
            self.rescan_worker.progress_updated.connect(self.progress_widget.update_progress)
            self.rescan_worker.rescan_completed.connect(self._on_rescan_completed)
            self.rescan_worker.rescan_failed.connect(self._on_rescan_failed)
            
            self.rescan_worker.start()
        
        def _on_rescan_completed(self, stats: Dict[str, Any]):
            """Handle rescan completion."""
            self.progress_widget.complete_progress(stats)
            
            # Re-enable start button
            self.start_button.setEnabled(True)
            self.start_button.setText("Start Rescan")
            
            # Emit completion signal
            self.rescan_completed.emit(stats)
            
            self.logger.info("Rescan completed successfully")
        
        def _on_rescan_failed(self, error: str):
            """Handle rescan failure."""
            self.progress_widget.fail_progress(error)
            
            # Re-enable start button
            self.start_button.setEnabled(True)
            self.start_button.setText("Start Rescan")
            
            self.logger.error(f"Rescan failed: {error}")
        
        def closeEvent(self, event):
            """Handle dialog close."""
            if self.rescan_worker and self.rescan_worker.isRunning():
                self.rescan_worker.terminate()
                self.rescan_worker.wait()
            
            super().closeEvent(event)
    
    
    def create_rescan_dialog(rescan_manager, scan_paths: List[Path], parent=None) -> RescanDialog:
        """Factory function to create rescan dialog."""
        return RescanDialog(rescan_manager, scan_paths, parent)

else:
    # Fallback for non-Qt environments
    class RescanDialog:
        def __init__(self, *args, **kwargs):
            pass
        
        def show(self):
            pass
    
    def create_rescan_dialog(*args, **kwargs):
        return RescanDialog()