from __future__ import annotations

import tempfile
import time
from pathlib import Path

from ops.scan import FileScanner
from store.db import DatabaseManager


def demo_change_detection():
    """Demonstrate change detection functionality."""
    print("=== Change Detection Demo ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "change_test"
        test_dir.mkdir()
        
        # Create initial test file
        test_file = test_dir / "test_photo.jpg"
        test_file.write_bytes(b"original content " * 1000)  # ~17KB
        print(f"Created test file: {test_file}")
        print(f"Initial size: {test_file.stat().st_size} bytes")
        print()
        
        # Initialize database and scanner
        db_path = test_dir / "change_demo.db"
        db = DatabaseManager(db_path=db_path)
        scanner = FileScanner(db)
        
        # First scan
        print("=== Initial Scan ===")
        stats1 = scanner.scan_directory(test_dir, recursive=False)
        print(f"Files added: {stats1['files_added']}")
        print()
        
        # Show file record
        file_record = db.find_file_by_path(test_file)
        print("Initial file record:")
        print(f"  Size: {file_record['size']}")
        print(f"  MTime: {file_record['mtime']}")
        print(f"  Format: {file_record['format']}")
        print()
        
        # Wait and modify file (change size)
        print("Modifying file (changing size)...")
        time.sleep(2)  # Ensure different mtime
        test_file.write_bytes(b"modified content " * 2000)  # ~34KB (doubled)
        print(f"New size: {test_file.stat().st_size} bytes")
        print()
        
        # Second scan - should detect change
        print("=== Scan After Size Change ===")
        scanner2 = FileScanner(db)  # Fresh scanner for clean stats
        stats2 = scanner2.scan_directory(test_dir, recursive=False)
        print(f"Files updated: {stats2['files_updated']}")
        print(f"Files skipped (no change): {stats2['files_skipped_no_change']}")
        print()
        
        # Show updated record
        file_record2 = db.find_file_by_path(test_file)
        print("Updated file record:")
        print(f"  Size: {file_record2['size']} (was {file_record['size']})")
        print(f"  MTime: {file_record2['mtime']} (was {file_record['mtime']})")
        print()
        
        # Third scan without changes - should skip
        print("=== Scan Without Changes ===")
        scanner3 = FileScanner(db)
        stats3 = scanner3.scan_directory(test_dir, recursive=False)
        print(f"Files updated: {stats3['files_updated']}")
        print(f"Files skipped (no change): {stats3['files_skipped_no_change']}")
        print()
        
        # Test mtime-only change
        print("Touching file (mtime change only)...")
        time.sleep(2)
        test_file.touch()  # Update mtime without changing content/size
        print()
        
        print("=== Scan After Touch (mtime change) ===")
        scanner4 = FileScanner(db)
        stats4 = scanner4.scan_directory(test_dir, recursive=False)
        print(f"Files updated: {stats4['files_updated']}")
        print(f"Files skipped (no change): {stats4['files_skipped_no_change']}")
        print()
        
        print("Change detection demo completed successfully!")


if __name__ == "__main__":
    demo_change_detection()