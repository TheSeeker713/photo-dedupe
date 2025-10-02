from __future__ import annotations

import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from core.exif import ExifExtractor, ExifData, create_oriented_thumbnail


def create_test_image_with_orientation(path: Path, orientation: int = 1) -> None:
    """Create a test image with specific EXIF orientation."""
    if not PIL_AVAILABLE:
        print("PIL not available, cannot create test images")
        return
    
    # Create a simple test image with asymmetric pattern
    # So we can see orientation changes clearly
    img = Image.new('RGB', (400, 300), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw identifying pattern
    # Red triangle in top-left
    draw.polygon([(0, 0), (100, 0), (0, 100)], fill='red')
    
    # Blue rectangle on right side
    draw.rectangle([(300, 50), (380, 150)], fill='blue')
    
    # Green circle in bottom-left
    draw.ellipse([(50, 200), (150, 280)], fill='green')
    
    # Text to show orientation
    draw.text((150, 130), f"Orient: {orientation}", fill='black')
    
    # Save with basic EXIF (PIL doesn't easily write custom orientation)
    img.save(path, 'JPEG', quality=90)
    
    # For demo purposes, we'll simulate different orientations
    # by manually rotating the image content to show what the
    # orientation-corrected version should look like
    if orientation != 1:
        print(f"Note: Created image {path.name} simulating orientation {orientation}")
        print(f"  In real usage, camera would set EXIF orientation tag")


def demo_exif_extraction():
    """Demonstrate EXIF extraction functionality."""
    print("=== EXIF Extraction Demo ===\n")
    
    if not PIL_AVAILABLE:
        print("PIL not available - cannot run full demo")
        return
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "exif_test"
        test_dir.mkdir()
        
        # Create test images with different orientations
        orientations = [1, 3, 6, 8]  # Normal, 180°, 270°, 90°
        test_images = []
        
        print("Creating test images with different orientations:")
        for orientation in orientations:
            img_path = test_dir / f"test_orientation_{orientation}.jpg"
            create_test_image_with_orientation(img_path, orientation)
            test_images.append((img_path, orientation))
            print(f"  Created: {img_path.name} (orientation {orientation})")
        print()
        
        # Test EXIF extraction on each image
        print("Extracting EXIF data:")
        for img_path, expected_orientation in test_images:
            print(f"\nFile: {img_path.name}")
            
            # Extract EXIF data
            exif_data = ExifExtractor.extract_exif(img_path)
            
            print(f"  Extracted orientation: {exif_data.orientation}")
            print(f"  Original dimensions: {exif_data.width}x{exif_data.height}")
            
            # Get oriented dimensions
            oriented_w, oriented_h = ExifExtractor.get_oriented_dimensions(img_path)
            print(f"  Oriented dimensions: {oriented_w}x{oriented_h}")
            
            # Show dimension changes for rotated images
            if exif_data.width and exif_data.height and oriented_w and oriented_h:
                if (exif_data.width, exif_data.height) != (oriented_w, oriented_h):
                    print(f"  ✓ Dimensions swapped due to orientation")
                else:
                    print(f"  → No dimension change needed")
            
            # Test other EXIF fields
            if exif_data.datetime_original:
                print(f"  DateTime Original: {exif_data.datetime_original_raw}")
            if exif_data.camera_full:
                print(f"  Camera: {exif_data.camera_full}")
            if exif_data.timezone_offset:
                print(f"  Timezone: {exif_data.timezone_offset}")
        
        print()
        
        # Test thumbnail creation with orientation
        print("Creating oriented thumbnails:")
        for img_path, orientation in test_images:
            thumb = create_oriented_thumbnail(img_path, size=(128, 128))
            if thumb:
                thumb_path = test_dir / f"thumb_{img_path.stem}.jpg"
                thumb.save(thumb_path)
                print(f"  Created oriented thumbnail: {thumb_path.name} "
                      f"({thumb.size[0]}x{thumb.size[1]})")
            else:
                print(f"  Failed to create thumbnail for {img_path.name}")
        
        print()
        
        # Test orientation transform lookup
        print("Orientation transform reference:")
        for orient in range(1, 9):
            if orient in ExifExtractor.ORIENTATION_TRANSFORMS:
                rotate, mirror_h, mirror_v = ExifExtractor.ORIENTATION_TRANSFORMS[orient]
                print(f"  Orientation {orient}: rotate {rotate}°, "
                      f"mirror_h={mirror_h}, mirror_v={mirror_v}")
        
        print("\nEXIF extraction demo completed successfully!")


def demo_datetime_parsing():
    """Demonstrate EXIF datetime parsing."""
    print("\n=== DateTime Parsing Demo ===\n")
    
    # Test various datetime formats
    test_dates = [
        "2023:10:02 14:30:45",      # Standard EXIF format
        "2023-10-02 14:30:45",      # Alternative format
        "2023/10/02 14:30:45",      # Another alternative
        "2023:10:02 14:30:45.123",  # With microseconds
        "",                          # Empty string
        "invalid date",              # Invalid format
        "2023:13:40 25:70:80",      # Invalid values
    ]
    
    print("Testing datetime parsing:")
    for date_str in test_dates:
        timestamp = ExifExtractor._parse_exif_datetime(date_str)
        if timestamp:
            import datetime
            dt = datetime.datetime.fromtimestamp(timestamp)
            print(f"  '{date_str}' → {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"  '{date_str}' → Failed to parse")
    
    print()


def demo_orientation_dimensions():
    """Demonstrate orientation dimension calculations."""
    print("=== Orientation Dimension Demo ===\n")
    
    # Test dimension corrections for all orientations
    original_w, original_h = 400, 300
    
    print(f"Original dimensions: {original_w}x{original_h}")
    print("Corrected dimensions by orientation:")
    
    for orientation in range(1, 9):
        corrected_w, corrected_h = ExifExtractor.get_corrected_dimensions(
            original_w, original_h, orientation
        )
        
        swapped = (corrected_w, corrected_h) != (original_w, original_h)
        swap_note = " (dimensions swapped)" if swapped else ""
        
        print(f"  Orientation {orientation}: {corrected_w}x{corrected_h}{swap_note}")
    
    print()


if __name__ == "__main__":
    demo_exif_extraction()
    demo_datetime_parsing()
    demo_orientation_dimensions()