#!/usr/bin/env python3
"""Simple test script for thumbnail pipeline."""

import tempfile
import time
from pathlib import Path
from PIL import Image
import piexif
import sys

def demo_thumbnail_simple():
    """Simple test of thumbnail generation."""
    print("=== Simple Thumbnail Pipeline Test ===\n")
    
    # Add src to path
    src_path = Path(__file__).parent.parent
    sys.path.insert(0, str(src_path))
    
    from app.settings import Settings
    from store.db import DatabaseManager
    from core.thumbs import ThumbnailGenerator
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_dir = temp_path / "test_images"
        test_dir.mkdir()
        
        print("1. Creating test image...")
        # Create a simple test image
        img_path = test_dir / "test.jpg"
        img = Image.new('RGB', (800, 600), color='red')
        
        # Add EXIF orientation
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Orientation: 6,  # 270° rotation
            },
            "Exif": {},
            "GPS": {},
            "1st": {},
            "thumbnail": None
        }
        exif_bytes = piexif.dump(exif_dict)
        img.save(img_path, 'JPEG', exif=exif_bytes, quality=95)
        print(f"   ✓ Created {img_path} (800x600, orientation=6)")
        print()
        
        print("2. Setting up components...")
        # Setup database
        db_path = temp_path / "test.db"
        settings = Settings(config_dir=temp_path / "config")
        
        # Configure cache for testing
        cache_config = settings._data.get("Cache", {})
        cache_config["cache_dir"] = str(temp_path / "cache")
        cache_config["on_demand_thumbs"] = True
        settings._data["Cache"] = cache_config
        settings.save()
        
        db_manager = DatabaseManager(db_path)
        # Database initializes automatically in constructor
        
        thumbnail_gen = ThumbnailGenerator(db_path, settings)
        print(f"   Cache dir: {thumbnail_gen.cache_dir}")
        print(f"   Thumbs dir: {thumbnail_gen.thumbs_dir}")
        print(f"   Target size: {thumbnail_gen.target_size}px")
        print()
        
        print("3. Adding file to database...")
        stat = img_path.stat()
        file_id = db_manager.add_file(
            file_path=img_path,
            size=stat.st_size,
            mtime=stat.st_mtime,
            ctime=stat.st_ctime
        )
        print(f"   File ID: {file_id}")
        print()
        
        print("4. Creating thumbnail...")
        thumb_path = thumbnail_gen.get_or_create_thumbnail(file_id, img_path)
        
        if thumb_path and thumb_path.exists():
            print(f"   ✓ Thumbnail created: {thumb_path.name}")
            
            # Check thumbnail
            with Image.open(thumb_path) as thumb:
                print(f"   Dimensions: {thumb.size[0]}x{thumb.size[1]}")
                print(f"   Format: {thumb.format}")
            
            thumb_size = thumb_path.stat().st_size
            print(f"   File size: {thumb_size:,} bytes")
            
            # Check database entry
            conn = db_manager.get_connection()
            try:
                cursor = conn.execute(
                    "SELECT thumb_w, thumb_h, created_at FROM thumbs WHERE file_id = ?",
                    (file_id,)
                )
                result = cursor.fetchone()
                if result:
                    print(f"   DB entry: {result[0]}x{result[1]}, created at {result[2]}")
                else:
                    print("   ✗ No database entry found")
            finally:
                conn.close()
        else:
            print("   ✗ Failed to create thumbnail")
        print()
        
        print("5. Testing second access (should use cache)...")
        thumb_path2 = thumbnail_gen.get_or_create_thumbnail(file_id, img_path)
        if thumb_path2 == thumb_path:
            print("   ✓ Used cached thumbnail")
        else:
            print("   ✗ Created new thumbnail instead of using cache")
        print()
        
        print("6. Testing stats...")
        stats = thumbnail_gen.get_thumbnail_stats()
        print(f"   Total thumbnails: {stats['total_thumbnails']}")
        print(f"   Total size: {stats['total_size_mb']:.3f} MB")
        print()
        
        print("✓ Simple thumbnail test completed!")

if __name__ == "__main__":
    demo_thumbnail_simple()