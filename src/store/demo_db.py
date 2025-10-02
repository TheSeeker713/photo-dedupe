from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from store.db import DatabaseManager


def demo_database():
    """Demonstrate database functionality."""
    print("=== Database Manager Demo ===\n")
    
    # Use a temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "demo.db"
        
        # Initialize database
        print(f"Initializing database at: {db_path}")
        db = DatabaseManager(db_path=db_path)
        print("Database initialized successfully")
        print()
        
        # Show initial stats
        print("Initial database stats:")
        stats = db.get_database_stats()
        print(json.dumps(stats, indent=2))
        print()
        
        # Add some test files
        print("Adding test files...")
        
        # File 1: Photo
        file1_id = db.add_file(
            file_path=Path("C:/photos/IMG_001.jpg"),
            size=2048576,
            mtime=time.time() - 3600,  # 1 hour ago
            ctime=time.time() - 7200,  # 2 hours ago
            dims_w=1920,
            dims_h=1080,
            exif_dt=time.time() - 3600,
            camera_model="Canon EOS R5",
            format="JPEG",
            orientation=1
        )
        print(f"Added file 1, ID: {file1_id}")
        
        # File 2: Similar photo
        file2_id = db.add_file(
            file_path=Path("C:/photos/IMG_001_copy.jpg"),
            size=2048576,  # Same size
            mtime=time.time() - 1800,  # 30 min ago
            ctime=time.time() - 1800,
            dims_w=1920,
            dims_h=1080,
            camera_model="Canon EOS R5",
            format="JPEG"
        )
        print(f"Added file 2, ID: {file2_id}")
        
        # File 3: Different photo
        file3_id = db.add_file(
            file_path=Path("C:/photos/IMG_002.jpg"),
            size=1024768,
            mtime=time.time() - 900,  # 15 min ago
            ctime=time.time() - 900,
            dims_w=1280,
            dims_h=720,
            format="JPEG"
        )
        print(f"Added file 3, ID: {file3_id}")
        print()
        
        # Add features for files
        print("Adding file features...")
        
        # File 1 and 2 have same fast hash (duplicates)
        same_fast_hash = "abc123def456"
        db.update_file_features(
            file1_id,
            fast_hash=same_fast_hash,
            sha256="sha256_file1_hash",
            phash="phash123",
            dhash="dhash123"
        )
        
        db.update_file_features(
            file2_id,
            fast_hash=same_fast_hash,  # Same fast hash
            sha256="sha256_file2_hash",  # Different SHA256 (slight variation)
            phash="phash124",  # Similar phash
            dhash="dhash124"
        )
        
        # File 3 is different
        db.update_file_features(
            file3_id,
            fast_hash="xyz789uvw012",
            sha256="sha256_file3_hash",
            phash="phash999",
            dhash="dhash999"
        )
        print("Features added")
        print()
        
        # Find similar files
        print("Finding similar files by fast hash:")
        similar_files = db.find_similar_files(fast_hash=same_fast_hash)
        for file_row in similar_files:
            print(f"  File ID {file_row['id']}: {file_row['path']} "
                  f"(size: {file_row['size']}, fast_hash: {file_row['fast_hash']})")
        print()
        
        # Create a duplicate group
        print("Creating duplicate group...")
        group_id = db.create_duplicate_group(
            reason="identical_fast_hash",
            score_summary="Fast hash match with similar perceptual hashes"
        )
        print(f"Created group ID: {group_id}")
        
        # Add files to group
        db.add_to_group(group_id, file1_id, role="original", similarity_score=1.0)
        db.add_to_group(group_id, file2_id, role="duplicate", similarity_score=0.95)
        print("Added files to duplicate group")
        print()
        
        # Test file lookup
        print("Testing file lookup by path...")
        found_file = db.find_file_by_path(Path("C:/photos/IMG_001.jpg"))
        if found_file:
            print(f"Found file: ID {found_file['id']}, "
                  f"size {found_file['size']}, format {found_file['format']}")
        else:
            print("File not found")
        print()
        
        # Show final stats
        print("Final database stats:")
        final_stats = db.get_database_stats()
        print(json.dumps(final_stats, indent=2))
        print()
        
        # Test database maintenance
        print("Running database analysis...")
        db.analyze_database()
        print("Analysis complete")
        print()
        
        print("Database demo completed successfully!")


if __name__ == "__main__":
    demo_database()