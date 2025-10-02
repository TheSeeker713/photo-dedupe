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

from core.exif import ExifExtractor, ExifData, create_oriented_thumbnail


def create_test_image_with_real_orientation(path: Path, orientation: int = 1) -> None:
    """Create a test image with actual EXIF orientation tag."""
    if not PIL_AVAILABLE or not PIEXIF_AVAILABLE:
        print("PIL or piexif not available, cannot create test images with EXIF")
        return
    
    # Create a distinctive test image
    img = Image.new('RGB', (400, 300), color='lightgray')
    draw = ImageDraw.Draw(img)
    
    # Draw corner markers to clearly show orientation
    # Top-left: Red square
    draw.rectangle([(10, 10), (60, 60)], fill='red')
    draw.text((15, 25), "TL", fill='white')
    
    # Top-right: Blue square  
    draw.rectangle([(340, 10), (390, 60)], fill='blue')
    draw.text((355, 25), "TR", fill='white')
    
    # Bottom-left: Green square
    draw.rectangle([(10, 240), (60, 290)], fill='green')
    draw.text((15, 255), "BL", fill='white')
    
    # Bottom-right: Yellow square
    draw.rectangle([(340, 240), (390, 290)], fill='yellow')
    draw.text((355, 255), "BR", fill='black')
    
    # Center text showing orientation
    draw.text((170, 140), f"Orient {orientation}", fill='black')
    draw.text((150, 160), f"400x300", fill='black')
    
    # Create EXIF data with orientation
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: "TestCamera",
            piexif.ImageIFD.Model: "Model X",
            piexif.ImageIFD.Orientation: orientation,
            piexif.ImageIFD.XResolution: (72, 1),
            piexif.ImageIFD.YResolution: (72, 1),
            piexif.ImageIFD.ResolutionUnit: 2,
        },
        "Exif": {
            piexif.ExifIFD.DateTimeOriginal: "2023:10:02 14:30:45",
            piexif.ExifIFD.DateTimeDigitized: "2023:10:02 14:30:45",
            piexif.ExifIFD.ISOSpeedRatings: 200,
            piexif.ExifIFD.FocalLength: (50, 1),
            piexif.ExifIFD.FNumber: (28, 10),  # f/2.8
            piexif.ExifIFD.ExposureTime: (1, 125),  # 1/125s
        },
        "GPS": {},
        "1st": {},
        "thumbnail": None
    }
    
    # Convert EXIF dict to bytes
    exif_bytes = piexif.dump(exif_dict)
    
    # Save image with EXIF
    img.save(path, 'JPEG', quality=90, exif=exif_bytes)
    print(f"Created {path.name} with EXIF orientation {orientation}")


def demo_real_exif_extraction():
    """Demonstrate EXIF extraction with real EXIF data."""
    print("=== Real EXIF Extraction Demo ===\n")
    
    if not PIL_AVAILABLE:
        print("PIL not available - cannot run demo")
        return
    
    if not PIEXIF_AVAILABLE:
        print("piexif not available - cannot create test images with real EXIF")
        return
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "real_exif_test"
        test_dir.mkdir()
        
        # Create test images with real EXIF orientation tags
        orientations = [1, 3, 6, 8]  # Normal, 180°, 270°, 90°
        test_images = []
        
        print("Creating test images with real EXIF orientation tags:")
        for orientation in orientations:
            img_path = test_dir / f"real_exif_{orientation}.jpg"
            create_test_image_with_real_orientation(img_path, orientation)
            test_images.append((img_path, orientation))
        print()
        
        # Test EXIF extraction on each image
        print("Extracting EXIF data from images with real orientation tags:")
        for img_path, expected_orientation in test_images:
            print(f"\nFile: {img_path.name}")
            
            # Extract EXIF data
            exif_data = ExifExtractor.extract_exif(img_path)
            
            print(f"  Expected orientation: {expected_orientation}")
            print(f"  Extracted orientation: {exif_data.orientation}")
            print(f"  Original dimensions: {exif_data.width}x{exif_data.height}")
            
            # Get oriented dimensions
            oriented_w, oriented_h = ExifExtractor.get_oriented_dimensions(img_path)
            print(f"  Oriented dimensions: {oriented_w}x{oriented_h}")
            
            # Show if dimensions were corrected
            if exif_data.width and exif_data.height and oriented_w and oriented_h:
                if (exif_data.width, exif_data.height) != (oriented_w, oriented_h):
                    print(f"  ✓ Dimensions corrected: {exif_data.width}x{exif_data.height} → {oriented_w}x{oriented_h}")
                else:
                    print(f"  → No dimension change needed")
            
            # Show other extracted EXIF fields
            if exif_data.datetime_original_raw:
                print(f"  DateTime Original: {exif_data.datetime_original_raw}")
            if exif_data.camera_full:
                print(f"  Camera: {exif_data.camera_full}")
            if exif_data.iso_speed:
                print(f"  ISO: {exif_data.iso_speed}")
            if exif_data.focal_length:
                print(f"  Focal Length: {exif_data.focal_length}mm")
            if exif_data.f_number:
                print(f"  F-Number: f/{exif_data.f_number}")
            if exif_data.exposure_time:
                print(f"  Exposure Time: {exif_data.exposure_time}")
        
        print()
        
        # Test creating oriented thumbnails
        print("Creating oriented thumbnails:")
        for img_path, orientation in test_images:
            print(f"\nProcessing {img_path.name} (orientation {orientation}):")
            
            # Create thumbnail with orientation applied
            thumb = create_oriented_thumbnail(img_path, size=(150, 150))
            if thumb:
                thumb_path = test_dir / f"thumb_{img_path.stem}.jpg"
                thumb.save(thumb_path)
                print(f"  ✓ Created oriented thumbnail: {thumb.size[0]}x{thumb.size[1]}")
                
                # For rotated images, thumbnail dimensions should be swapped
                if orientation in [5, 6, 7, 8]:  # 90° or 270° rotations
                    print(f"  → Thumbnail shows corrected orientation (rotated from original)")
                else:
                    print(f"  → Thumbnail preserves original orientation")
            else:
                print(f"  ✗ Failed to create thumbnail")
        
        print("\n" + "="*50)
        print("ORIENTATION CORRECTION SUMMARY:")
        print("="*50)
        
        for img_path, orientation in test_images:
            exif_data = ExifExtractor.extract_exif(img_path)
            oriented_w, oriented_h = ExifExtractor.get_oriented_dimensions(img_path)
            
            rotation_info = ""
            if orientation in ExifExtractor.ORIENTATION_TRANSFORMS:
                rotate, mirror_h, mirror_v = ExifExtractor.ORIENTATION_TRANSFORMS[orientation]
                if rotate != 0:
                    rotation_info += f" rotated {rotate}°"
                if mirror_h:
                    rotation_info += f" mirrored horizontally"
                if mirror_v:
                    rotation_info += f" mirrored vertically"
            
            print(f"Orientation {orientation}: {exif_data.width}x{exif_data.height} → {oriented_w}x{oriented_h}{rotation_info}")
        
        print("\nReal EXIF extraction demo completed successfully!")


if __name__ == "__main__":
    demo_real_exif_extraction()