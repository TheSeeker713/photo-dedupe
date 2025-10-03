#!/usr/bin/env python3
"""
Step 19 Demo: Comprehensive Settings Dialog
Demonstrates the complete settings system with all features.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    PYSIDE6_AVAILABLE = True
except ImportError:
    print("❌ PySide6 not available - GUI demo cannot run")
    PYSIDE6_AVAILABLE = False
    sys.exit(1)

from gui.comprehensive_settings import show_comprehensive_settings_dialog, ComprehensiveSettingsDialog

class Step19Demo(QMainWindow):
    """Demonstration of Step 19 comprehensive settings dialog."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Step 19: Comprehensive Settings Dialog Demo")
        self.setGeometry(200, 200, 500, 350)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                padding: 10px;
            }
            QPushButton {
                background-color: #444;
                color: white;
                border: 1px solid #666;
                border-radius: 5px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #555;
                border-color: #777;
            }
            QPushButton:pressed {
                background-color: #333;
            }
        """)
        
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("🔧 Step 19: Comprehensive Settings Dialog")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #0078d4;
                padding: 20px;
                border-bottom: 2px solid #444;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title)
        
        # Description
        description = QLabel(
            "Experience the complete settings system with:\n\n"
            "✨ Multi-tab interface (General, Performance, Hashing, Cache, Delete, About)\n"
            "⚡ Performance presets (Ultra-Lite, Balanced, Accurate, Custom)\n"
            "🎚️ Advanced sliders and controls with real-time feedback\n"
            "💾 Cache management with background clearing\n"
            "🔒 Security and safety options\n"
            "🎯 Intelligent preset switching and validation\n"
            "🎮 Hidden easter egg in the About tab\n\n"
            "This is a professional-grade settings interface with comprehensive configuration options."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("""
            QLabel {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 20px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(description)
        
        # Open settings button
        self.settings_button = QPushButton("🔧 Open Comprehensive Settings")
        self.settings_button.clicked.connect(self.open_comprehensive_settings)
        layout.addWidget(self.settings_button)
        
        # Feature highlights
        features = QLabel(
            "💡 Pro Tips:\n"
            "• Try switching between performance presets\n"
            "• Look for help tooltips on controls\n"
            "• Explore the cache management features\n"
            "• Find the tiny easter egg button in About tab"
        )
        features.setAlignment(Qt.AlignCenter)
        features.setStyleSheet("""
            QLabel {
                background-color: #2a4a2a;
                border: 1px solid #4a6a4a;
                border-radius: 5px;
                padding: 15px;
                color: #aaffaa;
                font-style: italic;
            }
        """)
        layout.addWidget(features)
        
        layout.addStretch()
        self.setCentralWidget(central_widget)
    
    def open_comprehensive_settings(self):
        """Open the comprehensive settings dialog."""
        try:
            # Create and show the dialog
            dialog = ComprehensiveSettingsDialog(self)
            
            # Connect to settings changes
            dialog.settings_changed.connect(self.on_settings_changed)
            
            result = dialog.exec()
            
            if result == dialog.Accepted:
                print("✅ Settings accepted and applied")
            else:
                print("❌ Settings dialog cancelled")
                
        except Exception as e:
            print(f"❌ Error opening settings: {e}")
            import traceback
            traceback.print_exc()
    
    def on_settings_changed(self, settings):
        """Handle settings changes."""
        print("🔄 Settings changed:")
        for section, values in settings.items():
            print(f"  📁 {section}:")
            for key, value in values.items():
                print(f"    • {key}: {value}")

def main():
    """Run the Step 19 demonstration."""
    print("🚀 Starting Step 19: Comprehensive Settings Dialog Demo")
    print("=" * 60)
    
    if not PYSIDE6_AVAILABLE:
        print("❌ This demo requires PySide6 to be installed")
        return
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for better dark theme support
    
    # Create and show the demo window
    demo = Step19Demo()
    demo.show()
    
    print("✅ Demo window opened - click 'Open Comprehensive Settings' to test")
    print("🎯 Features to test:")
    print("   • Performance preset switching")
    print("   • Slider controls with real-time feedback") 
    print("   • Cache management and clearing")
    print("   • Help tooltips on hover")
    print("   • Easter egg button in About tab")
    print("   • Settings persistence and validation")
    
    # Run the application
    result = app.exec()
    
    print("\n🏁 Step 19 demo completed")
    return result

if __name__ == "__main__":
    sys.exit(main())