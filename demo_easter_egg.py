#!/usr/bin/env python3
"""
Demo: Easter Egg Mini-Game
Test the secret mini-game hidden in the settings dialog.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
    from PySide6.QtCore import Qt
    
    from gui.settings_dialog import show_settings_dialog
    from gui.easter_egg import show_easter_egg
    
    class EasterEggDemo(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("🎮 Easter Egg Demo - Photo Deduplication Tool")
            self.setGeometry(100, 100, 400, 200)
            
            # Central widget
            central_widget = QWidget()
            layout = QVBoxLayout(central_widget)
            
            # Instructions
            instructions = """
🎮 SECRET EASTER EGG DEMO 🎮

Test the hidden mini-game in the photo deduplication tool!

Option 1: Settings Dialog Method (Secret!)
- Click "Open Settings" below
- Go to the "About" tab  
- Look for a tiny diamond symbol (⋄) in the bottom right
- Click the tiny symbol to activate the game!

Option 2: Direct Launch
- Click "Launch Game Directly" for immediate access

The Game:
- Use arrow keys to move PacDupe
- Eat all yellow dots (duplicates) to win
- Space bar pauses/resumes
- Get a hilarious victory message when you win!
            """
            
            from PySide6.QtWidgets import QTextEdit
            text_widget = QTextEdit()
            text_widget.setPlainText(instructions)
            text_widget.setReadOnly(True)
            layout.addWidget(text_widget)
            
            # Buttons
            settings_button = QPushButton("🔧 Open Settings (Find the Hidden Game!)")
            settings_button.clicked.connect(self.open_settings)
            layout.addWidget(settings_button)
            
            direct_button = QPushButton("🎮 Launch Game Directly")
            direct_button.clicked.connect(self.launch_game_direct)
            layout.addWidget(direct_button)
            
            # Apply theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: white;
                }
                QPushButton {
                    background-color: #444;
                    color: white;
                    border: 2px solid #666;
                    border-radius: 5px;
                    padding: 10px;
                    font-size: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #555;
                    border-color: #888;
                }
                QPushButton:pressed {
                    background-color: #333;
                }
                QTextEdit {
                    background-color: #333;
                    color: #ccc;
                    border: 1px solid #555;
                    border-radius: 5px;
                    font-family: 'Courier New', monospace;
                    font-size: 11px;
                }
            """)
            
            self.setCentralWidget(central_widget)
        
        def open_settings(self):
            """Open the settings dialog with the hidden easter egg."""
            print("Opening settings dialog...")
            print("💡 HINT: Look for a tiny diamond (⋄) symbol in the About tab!")
            show_settings_dialog(self)
        
        def launch_game_direct(self):
            """Launch the easter egg game directly."""
            print("Launching PacDupe mini-game directly...")
            show_easter_egg(self)
    
    def main():
        """Run the easter egg demo."""
        print("🎮 Easter Egg Demo Starting...")
        print("This demo shows the secret mini-game hidden in the photo deduplication tool!")
        print()
        
        app = QApplication(sys.argv)
        
        # Set application-wide dark theme
        app.setStyle('Fusion')
        from PySide6.QtGui import QPalette
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, "#2b2b2b")
        palette.setColor(QPalette.ColorRole.WindowText, "#ffffff")
        palette.setColor(QPalette.ColorRole.Base, "#333333")
        palette.setColor(QPalette.ColorRole.AlternateBase, "#555555")
        palette.setColor(QPalette.ColorRole.ToolTipBase, "#000000")
        palette.setColor(QPalette.ColorRole.ToolTipText, "#ffffff")
        palette.setColor(QPalette.ColorRole.Text, "#ffffff")
        palette.setColor(QPalette.ColorRole.Button, "#444444")
        palette.setColor(QPalette.ColorRole.ButtonText, "#ffffff")
        palette.setColor(QPalette.ColorRole.BrightText, "#ff0000")
        palette.setColor(QPalette.ColorRole.Link, "#42a5f5")
        palette.setColor(QPalette.ColorRole.Highlight, "#42a5f5")
        palette.setColor(QPalette.ColorRole.HighlightedText, "#000000")
        app.setPalette(palette)
        
        demo = EasterEggDemo()
        demo.show()
        
        print("Demo window opened!")
        print("🔍 To find the easter egg:")
        print("1. Click 'Open Settings'")
        print("2. Go to 'About' tab")
        print("3. Look for tiny ⋄ symbol in bottom right")
        print("4. Click it to play PacDupe!")
        print()
        
        return app.exec()

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