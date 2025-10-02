#!/usr/bin/env python3
"""Simple direct test of PIL extraction."""

import tempfile
from pathlib import Path
from PIL import Image
import piexif

def test_pil_extraction_directly():
    """Test PIL extraction step by step."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        img_path = temp_path / "test_simple.jpg"
        
        # Create a test image
        print(f"Creating test image...")
        img = Image.new('RGB', (400, 300), color='red')
        
        # Add EXIF data
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: "TestCamera",
                piexif.ImageIFD.Model: "ModelX",
                piexif.ImageIFD.Orientation: 6,
            },
            "Exif": {},
            "GPS": {},
            "1st": {},
            "thumbnail": None
        }
        
        exif_bytes = piexif.dump(exif_dict)
        img.save(str(img_path), exif=exif_bytes, format='JPEG', quality=95)
        print(f"✓ Saved to: {img_path}")
        print()
        
        # Now test our extraction logic step by step
        print("Testing PIL extraction step by step:")
        
        try:
            with Image.open(img_path) as test_img:
                print(f"1. Image opened successfully")
                print(f"   Size: {test_img.size}")
                
                # Test 1: Get dimensions
                width, height = test_img.size
                print(f"2. Dimensions extracted: {width} x {height}")
                
                # Test 2: Get EXIF dict
                exif_data = test_img.getexif()
                print(f"3. EXIF dict: {bool(exif_data)}")
                
                if exif_data:
                    print(f"   EXIF keys: {list(exif_data.keys())}")
                    
                    # Test 3: Get orientation
                    orientation = exif_data.get(274, 1)
                    print(f"4. Orientation (tag 274): {orientation}")
                    
                    # Test 4: Get camera info
                    make = exif_data.get(271)  # Make
                    model = exif_data.get(272)  # Model
                    print(f"5. Make (tag 271): {make}")
                    print(f"   Model (tag 272): {model}")
                    
                    # Test 5: Process camera info
                    camera_make = str(make).strip() if make else None
                    camera_model = str(model).strip() if model else None
                    print(f"6. Processed make: {camera_make}")
                    print(f"   Processed model: {camera_model}")
                    
                    if camera_make and camera_model:
                        camera_full = f"{camera_make} {camera_model}"
                        print(f"7. Camera full: {camera_full}")
                    
                else:
                    print("   No EXIF data found")
                    
        except Exception as e:
            print(f"ERROR in extraction: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        print("✓ Direct PIL test completed")

if __name__ == "__main__":
    test_pil_extraction_directly()