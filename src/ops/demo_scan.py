from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from ops.scan import FileScanner
from store.db import DatabaseManager


def create_sample_files(test_dir: Path) -> None:
    """Create sample image files for testing."""
    
    # Create directory structure
    images_dir = test_dir / "images"
    subdir = images_dir / "vacation" 
    cache_dir = images_dir / ".thumbnails"
    
    images_dir.mkdir()
    subdir.mkdir()
    cache_dir.mkdir()
    
    # Create fake image files with different sizes
    sample_files = [
        # Regular images
        ("images/photo1.jpg", 1024 * 500),  # 500KB
        ("images/photo2.JPG", 1024 * 750),  # 750KB  
        ("images/screenshot.png", 1024 * 100),  # 100KB
        ("images/vacation/beach.jpg", 1024 * 800),  # 800KB
        ("images/vacation/sunset.heic", 1024 * 600),  # 600KB
        
        # Files to be filtered/skipped
        ("images/tiny.jpg", 100),  # Too small
        ("images/document.pdf", 1024 * 50),  # Wrong extension
        ("images/.thumbnails/thumb1.jpg", 1024 * 10),  # Cache directory
        
        # Different formats
        ("images/raw_photo.cr2", 1024 * 2000),  # RAW file
        ("images/animation.gif", 1024 * 200),  # GIF
    ]
    
    print("Creating sample files:")
    for rel_path, size in sample_files:
        file_path = test_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file with fake content
        content = b"fake image data " * (size // 16 + 1)
        file_path.write_bytes(content[:size])
        
        # Set different modification times
        mtime = time.time() - (len(sample_files) - sample_files.index((rel_path, size))) * 3600
        os.utime(file_path, (mtime, mtime))
        
        print(f"  Created: {rel_path} ({size} bytes)")
    
    print()


def demo_scanner():
    """Demonstrate file scanner functionality."""
    print("=== File Scanner Demo ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test_photos"
        test_dir.mkdir()
        
        # Create sample files
        create_sample_files(test_dir)
        
        # Initialize database
        db_path = test_dir / "scanner_demo.db"
        db = DatabaseManager(db_path=db_path)
        scanner = FileScanner(db)
        
        print("Initial database stats:")
        initial_stats = db.get_database_stats()
        print(f"  Files in database: {initial_stats['files_count']}")
        print()
        
        # First scan - should add all valid files
        print("=== First Scan (recursive) ===")
        scan_stats = scanner.scan_directory(
            directory=test_dir / "images",
            recursive=True,
            include_patterns=["*.jpg", "*.jpeg", "*.png", "*.heic", "*.cr2", "*.gif"],
            exclude_patterns=["thumb*"]
        )
        
        print("\nFirst scan results:")
        for key, value in scan_stats.items():
            if not key.endswith('_time'):
                print(f"  {key}: {value}")
        print()
        
        # Check database after first scan
        print("Database stats after first scan:")
        mid_stats = db.get_database_stats()
        print(f"  Files in database: {mid_stats['files_count']}")
        
        # Show some file records
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT path, size, format, dims_w, dims_h, status 
                FROM files 
                ORDER BY path
                LIMIT 5
            """)
            
            print("\nSample file records:")
            for row in cursor.fetchall():
                print(f"  {row['path']}: {row['format']}, {row['size']} bytes, "
                      f"{row['dims_w']}x{row['dims_h']}, status={row['status']}")
        print()
        
        # Second scan - should skip unchanged files
        print("=== Second Scan (should skip unchanged files) ===")
        time.sleep(1)  # Ensure different scan time
        scan_stats2 = scanner.scan_directory(
            directory=test_dir / "images",
            recursive=True,
            include_patterns=["*.jpg", "*.jpeg", "*.png", "*.heic", "*.cr2", "*.gif"]
        )
        
        print("\nSecond scan results:")
        for key, value in scan_stats2.items():
            if not key.endswith('_time'):
                print(f"  {key}: {value}")
        print()
        
        # Test non-recursive scan
        print("=== Non-recursive Scan (images directory only) ===")
        scanner_nr = FileScanner(db)  # Fresh scanner for clean stats
        scan_stats3 = scanner_nr.scan_directory(
            directory=test_dir / "images",
            recursive=False,  # Non-recursive
            include_patterns=["*.jpg", "*.jpeg", "*.png", "*.heic", "*.cr2", "*.gif"]
        )
        
        print("\nNon-recursive scan results:")
        for key, value in scan_stats3.items():
            if not key.endswith('_time'):
                print(f"  {key}: {value}")
        print()
        
        # Final database stats
        print("Final database stats:")
        final_stats = db.get_database_stats()
        print(f"  Files in database: {final_stats['files_count']}")
        print(f"  Database size: {final_stats['db_size_mb']:.2f} MB")
        
        print("\nScanner demo completed successfully!")


if __name__ == "__main__":
    import os  # Import os for utime function
    demo_scanner()