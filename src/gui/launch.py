#!/usr/bin/env python3
"""
Step 15: GUI Shell Launch Script
Convenience script to launch the photo deduplication GUI application.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    """Launch the GUI application."""
    try:
        from gui.main_window import main as run_gui
        return run_gui()
    except ImportError as e:
        print(f"Error importing GUI modules: {e}")
        print("Make sure PySide6 is installed: pip install PySide6")
        return 1
    except Exception as e:
        print(f"Error launching GUI: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())