#!/usr/bin/env python3
"""Demo script for thumbnail pipeline testing."""

import tempfile
import time
from pathlib import Path
from PIL import Image
import piexif
import sys

def create_test_images(test_dir: Path) -> list[Path]:
    """Create test images with different orientations and formats."""
    test_images = []
    
    # Image 1: Standard landscape JPEG
    img1_path = test_dir / "landscape.jpg"
    img1 = Image.new('RGB', (800, 600), color='red')
    img1.save(img1_path, 'JPEG', quality=95)
    test_images.append(img1_path)
    print(f"✓ Created {img1_path.name} (800x600)")
    
    # Image 2: Portrait with EXIF orientation 6 (270° rotation)
    img2_path = test_dir / "portrait_rotated.jpg"
    img2 = Image.new('RGB', (600, 800), color='blue')
    
    # Add EXIF orientation data
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: "TestCamera",
            piexif.ImageIFD.Model: "ThumbTest",
            piexif.ImageIFD.Orientation: 6,  # 270° rotation
        },
        "Exif": {},
        "GPS": {},
        "1st": {},
        "thumbnail": None
    }
    exif_bytes = piexif.dump(exif_dict)
    img2.save(img2_path, 'JPEG', exif=exif_bytes, quality=95)
    test_images.append(img2_path)
    print(f"✓ Created {img2_path.name} (600x800, orientation=6)")
    
    # Image 3: Square PNG
    img3_path = test_dir / "square.png"
    img3 = Image.new('RGB', (500, 500), color='green')
    img3.save(img3_path, 'PNG')
    test_images.append(img3_path)
    print(f"✓ Created {img3_path.name} (500x500)")
    
    # Image 4: Very wide image
    img4_path = test_dir / "panorama.jpg"
    img4 = Image.new('RGB', (1200, 300), color='yellow')
    img4.save(img4_path, 'JPEG', quality=95)
    test_images.append(img4_path)
    print(f"✓ Created {img4_path.name} (1200x300)")
    
    return test_images

def demo_thumbnail_pipeline():
    """Test the thumbnail generation pipeline."""
    print("=== Thumbnail Pipeline Demo ===\n")
    
    # Setup paths
    sys.path.insert(0, str(Path(__file__).parent))
    from thumbs import ThumbnailGenerator
    from ..app.settings import Settings
    from ..store.db import DatabaseManager
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_images_dir = temp_path / "test_images"
        test_images_dir.mkdir()
        
        # Create test database
        db_path = temp_path / "test.db"
        
        # Initialize components
        print("1. Setting up test environment...")
        settings = Settings(config_dir=temp_path / "config")
        
        # Override cache settings for testing
        cache_config = settings.get("Cache", {})
        cache_config["cache_dir"] = str(temp_path / "cache")
        cache_config["on_demand_thumbs"] = False  # Test precomputation mode
        settings.data["Cache"] = cache_config
        settings.save()
        
        db_manager = DatabaseManager(db_path)
        db_manager.initialize()
        
        thumbnail_gen = ThumbnailGenerator(db_path, settings)
        print(f"   Cache directory: {thumbnail_gen.cache_dir}")
        print(f"   Thumbs directory: {thumbnail_gen.thumbs_dir}")
        print(f"   Target size: {thumbnail_gen.target_size}px")
        print(f"   On-demand mode: {thumbnail_gen.on_demand_mode}")
        print()
        
        # Create test images
        print("2. Creating test images...")
        test_images = create_test_images(test_images_dir)
        print()
        
        # Add images to database
        print("3. Adding images to database...")
        file_ids = []
        for img_path in test_images:
            stat = img_path.stat()
            file_id = db_manager.add_or_update_file(
                file_path=img_path,
                size_bytes=stat.st_size,
                modified_at=stat.st_mtime
            )
            file_ids.append(file_id)
            print(f"   Added {img_path.name} → file_id={file_id}")
        print()
        
        # Test individual thumbnail creation
        print("4. Testing individual thumbnail creation...")
        for i, (file_id, img_path) in enumerate(zip(file_ids, test_images)):
            thumb_path = thumbnail_gen.get_or_create_thumbnail(file_id, img_path)
            if thumb_path:
                thumb_stat = thumb_path.stat()
                print(f"   ✓ {img_path.name} → {thumb_path.name}")
                print(f"     Size: {thumb_stat.st_size:,} bytes")
                
                # Check thumbnail dimensions
                from PIL import Image as PILImage
                with PILImage.open(thumb_path) as thumb:
                    print(f"     Dimensions: {thumb.size[0]}x{thumb.size[1]}")
            else:
                print(f"   ✗ Failed to create thumbnail for {img_path.name}")
        print()
        
        # Test precomputation
        print("5. Testing batch precomputation...")
        # Clear existing thumbnails first
        for file_id in file_ids:
            db_manager.connection.execute("DELETE FROM thumbs WHERE file_id = ?", (file_id,))
        db_manager.connection.commit()
        
        def progress_callback(current, total, file_path):
            print(f"   Progress: {current}/{total} - {file_path.name}")
        
        created_count = thumbnail_gen.precompute_thumbnails(file_ids, progress_callback)
        print(f"   ✓ Created {created_count} thumbnails")
        print()
        
        # Test cache statistics
        print("6. Cache statistics...")
        stats = thumbnail_gen.get_thumbnail_stats()
        print(f"   Total thumbnails: {stats['total_thumbnails']}")
        print(f"   Total size: {stats['total_size_mb']:.2f} MB")
        print(f"   Cache directory: {stats['cache_dir']}")
        print(f"   Target size: {stats['target_size']}px")
        print()
        
        # Test on-demand mode
        print("7. Testing on-demand mode...")
        # Switch to on-demand mode
        thumbnail_gen.on_demand_mode = True
        
        # Clear one thumbnail
        test_file_id = file_ids[0]
        db_manager.connection.execute("DELETE FROM thumbs WHERE file_id = ?", (test_file_id,))
        db_manager.connection.commit()
        
        # Request thumbnail (should create on-demand)
        thumb_path = thumbnail_gen.get_or_create_thumbnail(test_file_id, test_images[0])
        if thumb_path:
            print(f"   ✓ Created on-demand thumbnail: {thumb_path.name}")
        else:
            print(f"   ✗ Failed to create on-demand thumbnail")
        print()
        
        # Test cleanup
        print("8. Testing cleanup...")
        # Create a fake orphaned thumbnail
        fake_thumb = thumbnail_gen.thumbs_dir / "fake_thumb_orphaned.webp"
        fake_thumb.write_text("fake")
        
        removed_count = thumbnail_gen.cleanup_orphaned_thumbnails()
        print(f"   ✓ Removed {removed_count} orphaned thumbnails")
        print()
        
        # Test format support
        print("9. Testing format support...")
        test_formats = ['.jpg', '.png', '.webp', '.heic', '.tiff', '.xyz']
        for fmt in test_formats:
            supported = thumbnail_gen.is_supported_format(Path(f"test{fmt}"))
            status = "✓" if supported else "✗"
            print(f"   {status} {fmt}")
        print()
        
        print("✓ Thumbnail pipeline demo completed successfully!")

if __name__ == "__main__":
    demo_thumbnail_pipeline()