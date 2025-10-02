from __future__ import annotations

import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False

from core.exif import ExifExtractor, ExifData


def demo_exif_core_functionality():
    """Demonstrate core EXIF functionality."""
    print("=== Core EXIF Functionality Demo ===\n")
    
    # Test datetime parsing
    print("1. Testing datetime parsing:")
    test_dates = [
        "2023:10:02 14:30:45",
        "2023-10-02 14:30:45", 
        "2023:10:02 14:30:45.123",
        "invalid",
        ""
    ]
    
    for date_str in test_dates:
        timestamp = ExifExtractor._parse_exif_datetime(date_str)
        status = "✓ Parsed" if timestamp else "✗ Failed"
        print(f"  '{date_str}' → {status}")
    print()
    
    # Test dimension correction for all orientations
    print("2. Testing orientation dimension correction:")
    original_w, original_h = 400, 300
    print(f"Original dimensions: {original_w}x{original_h}")
    
    for orientation in range(1, 9):
        corrected_w, corrected_h = ExifExtractor.get_corrected_dimensions(
            original_w, original_h, orientation
        )
        swapped = (corrected_w, corrected_h) != (original_w, original_h)
        marker = "↔" if swapped else "→"
        print(f"  Orientation {orientation}: {original_w}x{original_h} {marker} {corrected_w}x{corrected_h}")
    print()
    
    # Test orientation transforms
    print("3. Testing orientation transforms:")
    for orientation in range(1, 9):
        if orientation in ExifExtractor.ORIENTATION_TRANSFORMS:
            rotate, mirror_h, mirror_v = ExifExtractor.ORIENTATION_TRANSFORMS[orientation]
            transforms = []
            if rotate != 0:
                transforms.append(f"rotate {rotate}°")
            if mirror_h:
                transforms.append("mirror horizontal")
            if mirror_v:
                transforms.append("mirror vertical")
            
            transform_str = ", ".join(transforms) if transforms else "no transform"
            print(f"  Orientation {orientation}: {transform_str}")
    print()
    
    # Test timezone extraction
    print("4. Testing timezone extraction:")
    test_timezones = ["+02:00", "-05:00", "+00:00", "invalid", ""]
    for tz_str in test_timezones:
        extracted = ExifExtractor._extract_timezone_from_offset(tz_str)
        status = f"→ {extracted}" if extracted else "→ Failed"
        print(f"  '{tz_str}' {status}")
    print()


def demo_image_creation_and_extraction():
    """Create a test image and extract EXIF if possible."""
    print("=== Image Creation and EXIF Extraction ===\n")
    
    if not PIL_AVAILABLE:
        print("PIL not available - skipping image tests")
        return
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "exif_test"
        test_dir.mkdir()
        
        # Create a simple test image
        print("Creating test image...")
        img_path = test_dir / "test_image.jpg"
        
        # Create image with distinctive pattern
        img = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(img)
        
        # Red square in top-left corner
        draw.rectangle([(10, 10), (60, 60)], fill='red')
        draw.text((15, 30), "TL", fill='white')
        
        # Blue circle in bottom-right
        draw.ellipse([(340, 240), (390, 290)], fill='blue')
        draw.text((355, 260), "BR", fill='white')
        
        # Center text
        draw.text((180, 140), "Test Image", fill='black')
        draw.text((170, 160), "400x300", fill='black')
        
        # Add EXIF if piexif is available
        if PIEXIF_AVAILABLE:
            print("Adding EXIF data with piexif...")
            exif_dict = {
                "0th": {
                    piexif.ImageIFD.Make: "TestCamera",
                    piexif.ImageIFD.Model: "ModelX",
                    piexif.ImageIFD.Orientation: 6,  # 270° rotation
                },
                "Exif": {
                    piexif.ExifIFD.DateTimeOriginal: "2023:10:02 14:30:45",
                    piexif.ExifIFD.ISOSpeedRatings: 200,
                    piexif.ExifIFD.FocalLength: (50, 1),
                },
                "GPS": {},
                "1st": {},
                "thumbnail": None
            }
            
            exif_bytes = piexif.dump(exif_dict)
            img.save(img_path, 'JPEG', quality=90, exif=exif_bytes)
            print("✓ Saved with EXIF orientation=6 (270° rotation)")
        else:
            img.save(img_path, 'JPEG', quality=90)
            print("✓ Saved without EXIF (piexif not available)")
        
        print(f"Image saved to: {img_path}")
        print(f"File size: {img_path.stat().st_size} bytes")
        print()
        
        # Extract EXIF from the created image
        print("Extracting EXIF data:")
        exif_data = ExifExtractor.extract_exif(img_path)
        
        print(f"  Dimensions: {exif_data.width}x{exif_data.height}")
        print(f"  Orientation: {exif_data.orientation}")
        print(f"  Camera Make: {exif_data.camera_make or 'None'}")
        print(f"  Camera Model: {exif_data.camera_model or 'None'}")
        print(f"  Camera Full: {exif_data.camera_full or 'None'}")
        print(f"  DateTime Original: {exif_data.datetime_original_raw or 'None'}")
        print(f"  ISO Speed: {exif_data.iso_speed or 'None'}")
        print(f"  Focal Length: {exif_data.focal_length or 'None'}")
        print()
        
        # Test oriented dimensions
        print("Testing oriented dimensions:")
        oriented_w, oriented_h = ExifExtractor.get_oriented_dimensions(img_path)
        print(f"  Original: {exif_data.width}x{exif_data.height}")
        print(f"  Oriented: {oriented_w}x{oriented_h}")
        
        if (exif_data.width, exif_data.height) != (oriented_w, oriented_h):
            print(f"  ✓ Dimensions were corrected for orientation {exif_data.orientation}")
        else:
            print(f"  → No dimension correction needed")
        print()
        
        print("EXIF extraction test completed!")


if __name__ == "__main__":
    demo_exif_core_functionality()
    demo_image_creation_and_extraction()