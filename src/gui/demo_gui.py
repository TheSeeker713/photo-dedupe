#!/usr/bin/env python3
"""
Step 15: GUI Shell Demo
Demonstrates the PySide6 GUI application with sample data.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    """Run the GUI demo."""
    print("Starting Step 15 GUI Shell Demo...")
    print("\n=== Step 15: GUI Shell (PySide6) Demo ===")
    
    try:
        # Import and run the GUI
        from gui.main_window import main as run_gui
        
        print("Launching GUI application...")
        print("Features to test:")
        print("  ✓ Main window with toolbar")
        print("  ✓ Left pane: groups list with filters")
        print("  ✓ Right pane: preview area with overview and compare tabs")
        print("  ✓ Status bar with worker status")
        print("  ✓ Sample data rendering")
        print("  ✓ Action enabling/disabling")
        print("\nClose the window to complete the demo.")
        
        return run_gui()
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())