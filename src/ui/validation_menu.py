"""
Menu integration for Step 25 validation.

This module provides a validation menu item that can be integrated into 
the main photo-dedupe application.
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional

try:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QTextEdit, QProgressBar, QCheckBox, QMessageBox
    )
    from PySide6.QtCore import Qt, QThread, pyqtSignal
    from PySide6.QtGui import QFont
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QDialog = object


class ValidationDialog(QDialog):
    """GUI dialog for running validation tests."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Step 25 - Validation Suite")
        self.setMinimumSize(600, 500)
        
        self.validation_thread = None
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Photo-Dedupe Validation Suite")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Description
        desc = QLabel(
            "This validation suite creates a test dataset and runs comprehensive "
            "tests to verify the photo-dedupe system is working correctly."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Options
        options_layout = QHBoxLayout()
        self.keep_files_cb = QCheckBox("Keep test files after validation")
        self.verbose_cb = QCheckBox("Verbose logging")
        options_layout.addWidget(self.keep_files_cb)
        options_layout.addWidget(self.verbose_cb)
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Results display
        self.results_text = QTextEdit()
        self.results_text.setFont(QFont("Consolas", 9))
        self.results_text.setVisible(False)
        layout.addWidget(self.results_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("Run Validation")
        self.run_button.clicked.connect(self.start_validation)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        
        button_layout.addStretch()
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
    
    def start_validation(self):
        """Start validation in background thread."""
        if self.validation_thread and self.validation_thread.isRunning():
            return
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.results_text.setVisible(True)
        self.results_text.clear()
        self.results_text.append("Starting validation...")
        
        # Disable run button
        self.run_button.setEnabled(False)
        
        # Start validation thread
        self.validation_thread = ValidationWorker(
            keep_files=self.keep_files_cb.isChecked(),
            verbose=self.verbose_cb.isChecked()
        )
        self.validation_thread.progress_updated.connect(self.update_progress)
        self.validation_thread.validation_completed.connect(self.validation_finished)
        self.validation_thread.start()
    
    def update_progress(self, message: str):
        """Update progress display."""
        self.results_text.append(message)
        # Scroll to bottom
        cursor = self.results_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.results_text.setTextCursor(cursor)
    
    def validation_finished(self, summary_text: str, success: bool):
        """Handle validation completion."""
        self.progress_bar.setVisible(False)
        self.results_text.append("\n" + summary_text)
        
        # Re-enable button
        self.run_button.setEnabled(True)
        
        # Show completion message
        if success:
            QMessageBox.information(
                self, "Validation Complete",
                "✅ Validation completed successfully!"
            )
        else:
            QMessageBox.warning(
                self, "Validation Issues",
                "⚠️ Validation completed with issues. Check the results for details."
            )


if QT_AVAILABLE:
    class ValidationWorker(QThread):
        """Worker thread for running validation."""
        
        progress_updated = pyqtSignal(str)
        validation_completed = pyqtSignal(str, bool)  # summary_text, success
        
        def __init__(self, keep_files=False, verbose=False):
            super().__init__()
            self.keep_files = keep_files
            self.verbose = verbose
            self.logger = logging.getLogger(__name__)
        
        def run(self):
            """Run validation in background."""
            try:
                # Import here to avoid circular dependencies
                from tests.validation_runner import ValidationRunner, print_validation_summary
                import io
                import sys
                
                # Create temp directory
                temp_dir = Path(tempfile.mkdtemp())
                self.progress_updated.emit(f"Using temp directory: {temp_dir}")
                
                # Run validation
                runner = ValidationRunner(temp_dir)
                self.progress_updated.emit("Creating test dataset...")
                
                summary = runner.run_full_validation()
                
                # Capture summary output
                summary_output = io.StringIO()
                original_stdout = sys.stdout
                try:
                    sys.stdout = summary_output
                    print_validation_summary(summary)
                    summary_text = summary_output.getvalue()
                finally:
                    sys.stdout = original_stdout
                
                # Cleanup
                if not self.keep_files:
                    try:
                        import shutil
                        shutil.rmtree(temp_dir)
                    except Exception as e:
                        self.progress_updated.emit(f"Cleanup warning: {e}")
                else:
                    self.progress_updated.emit(f"Test files preserved in: {temp_dir}")
                
                # Signal completion
                success = summary.success_rate >= 80
                self.validation_completed.emit(summary_text, success)
                
            except Exception as e:
                self.logger.error(f"Validation failed: {e}")
                self.validation_completed.emit(f"Validation failed: {str(e)}", False)


def show_validation_dialog(parent=None):
    """Show the validation dialog."""
    if not QT_AVAILABLE:
        print("GUI validation requires PySide6")
        return
    
    dialog = ValidationDialog(parent)
    dialog.exec()


def run_validation_command():
    """Run validation as a command-line operation."""
    try:
        from tests.validation_runner import ValidationRunner, print_validation_summary
        import tempfile
        import shutil
        
        print("Running Step 25 validation...")
        
        # Create temp directory
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Run validation
            runner = ValidationRunner(temp_dir)
            summary = runner.run_full_validation()
            
            # Print results
            print_validation_summary(summary)
            
            return summary.success_rate >= 80
            
        finally:
            # Cleanup
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
    
    except Exception as e:
        print(f"Validation failed: {e}")
        return False