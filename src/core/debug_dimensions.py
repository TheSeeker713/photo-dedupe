#!/usr/bin/env python3
"""Debug dimension extraction issues."""

import tempfile
from pathlib import Path
from PIL import Image
import piexif
import sys

def debug_dimension_extraction():
    """Debug why dimensions aren't being extracted properly."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        img_path = temp_path / "test_debug.jpg"
        
        # Create a simple test image
        print(f"Creating test image at: {img_path}")
        img = Image.new('RGB', (400, 300), color='red')
        
        # Add minimal EXIF data
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: "TestCamera",
                piexif.ImageIFD.Model: "ModelX",
                piexif.ImageIFD.Orientation: 6,  # 270° rotation
            },
            "Exif": {},
            "GPS": {},
            "1st": {},
            "thumbnail": None
        }
        
        exif_bytes = piexif.dump(exif_dict)
        img.save(str(img_path), exif=exif_bytes, format='JPEG', quality=95)
        print(f"✓ Image created with dimensions {img.size} and orientation=6")
        print()
        
        # Test 1: Basic PIL image opening
        print("1. Testing basic PIL image opening:")
        with Image.open(img_path) as test_img:
            print(f"   Image size: {test_img.size}")
            print(f"   Image mode: {test_img.mode}")
            print(f"   Image format: {test_img.format}")
        print()
        
        # Test 2: PIL EXIF extraction
        print("2. Testing PIL EXIF extraction:")
        with Image.open(img_path) as test_img:
            exif_data = test_img.getexif()
            print(f"   EXIF dict available: {bool(exif_data)}")
            print(f"   EXIF keys: {list(exif_data.keys())}")
            
            if exif_data:
                # Look for orientation
                orientation = exif_data.get(274)  # Orientation tag
                print(f"   Orientation (tag 274): {orientation}")
                
                # Look for dimensions in EXIF
                width_tag = exif_data.get(256)  # ImageWidth
                height_tag = exif_data.get(257)  # ImageLength
                print(f"   EXIF Width (tag 256): {width_tag}")
                print(f"   EXIF Height (tag 257): {height_tag}")
        print()
        
        # Test 3: piexif extraction
        print("3. Testing piexif extraction:")
        try:
            piexif_dict = piexif.load(str(img_path))
            print(f"   piexif dict keys: {list(piexif_dict.keys())}")
            
            ifd0 = piexif_dict.get('0th', {})
            print(f"   IFD0 keys: {list(ifd0.keys())}")
            
            orientation = ifd0.get(piexif.ImageIFD.Orientation)
            make = ifd0.get(piexif.ImageIFD.Make)
            model = ifd0.get(piexif.ImageIFD.Model)
            
            print(f"   Orientation: {orientation}")
            print(f"   Make: {make}")
            print(f"   Model: {model}")
            
        except Exception as e:
            print(f"   piexif error: {e}")
        print()
        
        # Test 4: Our ExifExtractor methods
        print("4. Testing our ExifExtractor methods:")
        sys.path.insert(0, str(Path(__file__).parent))
        from exif import ExifExtractor
        
        print("   Testing extract_exif_pil:")
        pil_result = ExifExtractor.extract_exif_pil(img_path)
        print(f"     Width: {pil_result.width}")
        print(f"     Height: {pil_result.height}")
        print(f"     Orientation: {pil_result.orientation}")
        print(f"     Camera: {pil_result.camera_full}")
        
        print("   Testing extract_exif_piexif:")
        piexif_result = ExifExtractor.extract_exif_piexif(img_path)
        print(f"     Width: {piexif_result.width}")
        print(f"     Height: {piexif_result.height}")
        print(f"     Orientation: {piexif_result.orientation}")
        print(f"     Camera: {piexif_result.camera_full}")
        
        print("   Testing combined extract_exif:")
        combined_result = ExifExtractor.extract_exif(img_path)
        print(f"     Width: {combined_result.width}")
        print(f"     Height: {combined_result.height}")
        print(f"     Orientation: {combined_result.orientation}")
        print(f"     Camera: {combined_result.camera_full}")

if __name__ == "__main__":
    debug_dimension_extraction()