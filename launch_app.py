#!/usr/bin/env python3
"""
Photo Deduplication Tool - Main Application Launcher
A complete photo deduplication application with secret easter egg functionality.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QToolBar, QPushButton, QLabel, QFrame, QMessageBox
    )
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont, QPalette
    
    from gui.settings_dialog import show_settings_dialog
    from gui.easter_egg import show_easter_egg
    
    class PhotoDedupeApp(QMainWindow):
        """Main application window with easter egg integration."""
        
        def __init__(self):
            super().__init__()
            self.setWindowTitle("📷 Photo Deduplication Tool v1.0 - with Secret Features! 🎮")
            self.setGeometry(100, 100, 1000, 700)
            
            self.setup_ui()
            self.apply_theme()
            
        def setup_ui(self):
            """Setup the main UI."""
            # Central widget
            central_widget = QWidget()
            layout = QVBoxLayout(central_widget)
            
            # Create toolbar
            toolbar = self.create_toolbar()
            self.addToolBar(toolbar)
            
            # Welcome message
            welcome_frame = QFrame()
            welcome_layout = QVBoxLayout(welcome_frame)
            
            title = QLabel("📷 Photo Deduplication Tool")
            title.setFont(QFont("Arial", 24, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("color: #FFD700; margin: 20px;")
            welcome_layout.addWidget(title)
            
            subtitle = QLabel("Find and manage duplicate photos with advanced algorithms")
            subtitle.setFont(QFont("Arial", 12))
            subtitle.setAlignment(Qt.AlignCenter)
            subtitle.setStyleSheet("color: #CCCCCC; margin-bottom: 30px;")
            welcome_layout.addWidget(subtitle)
            
            # Feature list
            features = QLabel("""
🔍 Advanced duplicate detection algorithms
📊 Comprehensive similarity analysis
🗂️ Safe deletion with recycle bin support
📈 Detailed reporting and export capabilities
⚙️ Configurable settings and preferences
🎮 Hidden surprises for the observant... 

💡 TIP: Explore the settings to discover all features!
            """)
            features.setFont(QFont("Consolas", 10))
            features.setAlignment(Qt.AlignCenter)
            features.setStyleSheet("color: #AAAAAA; background-color: #333; padding: 20px; border-radius: 10px; margin: 20px;")
            welcome_layout.addWidget(features)
            
            # Easter egg hint (subtle)
            hint = QLabel("👀 Curious users often find the most interesting features...")
            hint_font = QFont("Arial", 9)
            hint_font.setItalic(True)
            hint.setFont(hint_font)
            hint.setAlignment(Qt.AlignCenter)
            hint.setStyleSheet("color: #888; margin: 10px;")
            welcome_layout.addWidget(hint)
            
            layout.addWidget(welcome_frame)
            self.setCentralWidget(central_widget)
            
            # Status bar
            self.statusBar().showMessage("Ready - Photo Deduplication Tool with Secret Features! 🎮")
            
        def create_toolbar(self):
            """Create the main toolbar."""
            toolbar = QToolBar()
            toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            
            # Main actions
            scan_action = toolbar.addAction("🔍 Scan for Duplicates")
            scan_action.triggered.connect(self.scan_duplicates)
            
            toolbar.addSeparator()
            
            compare_action = toolbar.addAction("⚖️ Compare Images")
            compare_action.triggered.connect(self.compare_images)
            
            toolbar.addSeparator()
            
            export_action = toolbar.addAction("📊 Export Report")
            export_action.triggered.connect(self.export_report)
            
            toolbar.addSeparator()
            
            # Settings action (contains the easter egg!)
            settings_action = toolbar.addAction("⚙️ Settings")
            settings_action.triggered.connect(self.open_settings)
            
            toolbar.addSeparator()
            
            # Direct easter egg action (for testing/demo)
            easter_action = toolbar.addAction("🎮 Secret Game")
            easter_action.triggered.connect(self.launch_easter_egg)
            easter_action.setVisible(False)  # Hidden by default
            
            # Developer mode toggle
            dev_action = toolbar.addAction("🔧 Dev Mode")
            dev_action.triggered.connect(lambda: easter_action.setVisible(not easter_action.isVisible()))
            
            return toolbar
        
        def scan_duplicates(self):
            """Handle scan for duplicates action."""
            QMessageBox.information(self, "Scan", 
                "Duplicate scanning functionality would be implemented here.\n\n"
                "This is the main feature of the photo deduplication tool!\n\n"
                "💡 Pro tip: Check out the Settings for configuration options...")
        
        def compare_images(self):
            """Handle compare images action."""
            QMessageBox.information(self, "Compare", 
                "Image comparison functionality would be implemented here.\n\n"
                "Compare similar images side-by-side to decide which to keep.")
        
        def export_report(self):
            """Handle export report action."""
            QMessageBox.information(self, "Export", 
                "Report export functionality is already implemented!\n\n"
                "Export duplicate analysis results to CSV or JSON format.")
        
        def open_settings(self):
            """Open the settings dialog (contains the easter egg!)."""
            print("🔍 Opening settings dialog...")
            print("💡 HINT: Look for something small and diamond-shaped in the About tab! 💎")
            
            result = show_settings_dialog(self)
            if result:
                self.statusBar().showMessage("Settings updated!", 3000)
            else:
                self.statusBar().showMessage("Settings opened - did you find anything interesting? 😉", 5000)
        
        def launch_easter_egg(self):
            """Launch the easter egg directly (for testing)."""
            print("🎮 Launching PacDupe mini-game directly...")
            show_easter_egg(self)
        
        def apply_theme(self):
            """Apply dark theme to the application."""
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QToolBar {
                    background-color: #3c3c3c;
                    border: 1px solid #555;
                    spacing: 3px;
                    padding: 5px;
                }
                QToolBar QToolButton {
                    background-color: #444;
                    color: white;
                    border: 1px solid #666;
                    border-radius: 3px;
                    padding: 8px 12px;
                    margin: 2px;
                }
                QToolBar QToolButton:hover {
                    background-color: #555;
                    border-color: #777;
                }
                QToolBar QToolButton:pressed {
                    background-color: #333;
                }
                QFrame {
                    background-color: #2b2b2b;
                }
                QLabel {
                    color: white;
                }
                QStatusBar {
                    background-color: #3c3c3c;
                    color: #ccc;
                    border-top: 1px solid #555;
                }
            """)

    def main():
        """Run the photo deduplication application."""
        print("🎮 Photo Deduplication Tool - Starting...")
        print("==========================================")
        print()
        print("🔍 Main Features:")
        print("- Advanced duplicate detection")
        print("- Image similarity analysis") 
        print("- Safe file management")
        print("- Export capabilities")
        print("- Professional settings")
        print()
        print("🎮 SECRET FEATURE:")
        print("There's a hidden mini-game somewhere in this app!")
        print("💡 HINT: Check the Settings -> About tab for something tiny...")
        print()
        
        app = QApplication(sys.argv)
        
        # Set dark theme globally
        app.setStyle('Fusion')
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, "#2b2b2b")
        palette.setColor(QPalette.ColorRole.WindowText, "#ffffff")
        palette.setColor(QPalette.ColorRole.Base, "#333333")
        palette.setColor(QPalette.ColorRole.AlternateBase, "#555555")
        palette.setColor(QPalette.ColorRole.Text, "#ffffff")
        palette.setColor(QPalette.ColorRole.Button, "#444444")
        palette.setColor(QPalette.ColorRole.ButtonText, "#ffffff")
        app.setPalette(palette)
        
        # Create and show main window
        window = PhotoDedupeApp()
        window.show()
        
        print("✅ Application launched successfully!")
        print("🎯 Ready to find duplicates and... other things! 😉")
        print()
        print("🔍 Easter Egg Hunt Instructions:")
        print("1. Click the '⚙️ Settings' button")
        print("2. Go to the 'About' tab") 
        print("3. Look for a tiny diamond symbol (⋄)")
        print("4. Click it to play PacDupe!")
        
        return app.exec()

    if __name__ == "__main__":
        sys.exit(main())

except ImportError as e:
    def main():
        print("❌ Could not import required modules.")
        print(f"Error: {e}")
        print()
        print("Please ensure PySide6 is installed:")
        print("pip install PySide6")
        return 1
    
    if __name__ == "__main__":
        sys.exit(main())