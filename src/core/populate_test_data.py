#!/usr/bin/env python3
"""
Quick script to populate database with test data for search index demo.
"""

import sys
import tempfile
from pathlib import Path
from PIL import Image

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from store.db import DatabaseManager
from core.features import FeatureExtractor
from app.settings import Settings


def create_test_image(path, size=(100, 100), color=(255, 0, 0)):
    """Create a simple test image."""
    img = Image.new('RGB', size, color)
    img.save(path, 'JPEG')
    return path


def populate_test_data():
    """Populate database with test data."""
    print("Populating database with test data...")
    
    # Initialize components
    settings = Settings()
    db_manager = DatabaseManager()
    feature_extractor = FeatureExtractor(db_manager.db_path, settings)
    
    # Create temporary test images
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test images
        test_images = [
            ("red.jpg", (100, 100), (255, 0, 0)),      # Red image
            ("red_copy.jpg", (100, 100), (255, 0, 0)), # Exact copy
            ("green.jpg", (100, 100), (0, 255, 0)),    # Green image  
            ("blue.jpg", (100, 100), (0, 0, 255)),     # Blue image
            ("red_large.jpg", (200, 200), (255, 0, 0)), # Red but larger
        ]
        
        files_added = 0
        
        for filename, size, color in test_images:
            file_path = temp_path / filename
            create_test_image(file_path, size, color)
            
            # Add to database
            try:
                import hashlib
                import time
                
                path_hash = hashlib.sha256(str(file_path).encode()).hexdigest()[:16]
                current_time = time.time()
                
                with db_manager.get_connection() as conn:
                    cursor = conn.execute("""
                        INSERT INTO files (path, path_hash, size, mtime, ctime, last_seen_at, created_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (str(file_path), path_hash, file_path.stat().st_size, 
                         file_path.stat().st_mtime, file_path.stat().st_ctime,
                         current_time, current_time))
                    file_id = cursor.lastrowid
                
                # Extract features
                print(f"  Processing {filename}...")
                success = feature_extractor.process_file(file_id, file_path)
                
                if success:
                    files_added += 1
                    print(f"    ✓ Features extracted")
                else:
                    print(f"    ✗ Failed to extract features")
            
            except Exception as e:
                print(f"    ✗ Error processing {filename}: {e}")
        
        print(f"\n✓ Added {files_added} files with features to database")
        return files_added


if __name__ == "__main__":
    populate_test_data()