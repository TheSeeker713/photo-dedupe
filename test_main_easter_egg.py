#!/usr/bin/env python3
"""
Test: Main Window with Easter Egg Integration
Test the easter egg integration in the main photo deduplication application.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from PySide6.QtWidgets import QApplication
    from gui.main_window import MainWindow
    IMPORTS_OK = True
except ImportError as import_error:
    IMPORTS_OK = False
    ERROR_MSG = str(import_error)

def main():
    """Test the main application with easter egg integration."""
    if not IMPORTS_OK:
        print("❌ Could not import required modules.")
        print(f"Error: {ERROR_MSG}")
        print()
        print("Please ensure PySide6 is installed:")
        print("pip install PySide6")
        return 1
        
    print("🎮 Testing Easter Egg Integration in Main Application...")
    print()
    print("Main application starting with easter egg functionality integrated!")
    print("🔍 To find the easter egg in the main app:")
    print("1. Click the '⚙️ Settings' button in the toolbar")
    print("2. Navigate to the 'About' tab")
    print("3. Look for a tiny diamond symbol (⋄) in the bottom right corner")
    print("4. Click the tiny symbol to launch PacDupe mini-game!")
    print()
    print("🎮 Game Controls:")
    print("- Arrow keys: Move PacDupe")
    print("- Space: Pause/Resume")
    print("- Goal: Eat all yellow dots to win!")
    print()
    
    app = QApplication(sys.argv)
    
    # Set dark theme
    app.setStyle('Fusion')
    
    # Create main window
    window = MainWindow()
    window.show()
    
    print("✅ Main application window opened!")
    print("The easter egg is now integrated and ready to discover! 🎊")
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())