#!/usr/bin/env python3
"""Test ExifExtractor with debug output."""

import tempfile
from pathlib import Path
from PIL import Image
import piexif
import sys

def test_exif_extractor_with_debug():
    """Test ExifExtractor with detailed debug output."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        img_path = temp_path / "test_debug_exif.jpg"
        
        # Create test image
        print(f"Creating test image...")
        img = Image.new('RGB', (400, 300), color='red')
        
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
        
        # Import our module and test
        sys.path.insert(0, str(Path(__file__).parent))
        from exif import ExifExtractor, ExifData
        
        # Create a debug version of extract_exif_pil
        @classmethod
        def debug_extract_exif_pil(cls, image_path: Path) -> ExifData:
            """Debug version of extract_exif_pil."""
            print("DEBUG: Starting PIL EXIF extraction")
            exif_data = ExifData()
            
            # Check PIL availability
            try:
                from PIL import Image as PILImage
                print("DEBUG: PIL import successful")
            except ImportError:
                print("DEBUG: PIL not available")
                return exif_data
            
            try:
                print(f"DEBUG: Opening image {image_path}")
                with PILImage.open(image_path) as img:
                    print(f"DEBUG: Image opened, size: {img.size}")
                    
                    # Get dimensions
                    exif_data.width, exif_data.height = img.size
                    print(f"DEBUG: Dimensions set: {exif_data.width} x {exif_data.height}")
                    
                    # Get EXIF
                    exif_dict = img.getexif()
                    print(f"DEBUG: EXIF dict available: {bool(exif_dict)}")
                    
                    if not exif_dict:
                        print("DEBUG: No EXIF data found, returning")
                        return exif_data
                    
                    print(f"DEBUG: EXIF keys: {list(exif_dict.keys())}")
                    
                    # Extract orientation
                    orientation = exif_dict.get(274, 1)
                    print(f"DEBUG: Raw orientation value: {orientation}")
                    exif_data.orientation = orientation if 1 <= orientation <= 8 else 1
                    print(f"DEBUG: Final orientation: {exif_data.orientation}")
                    
                    # Extract camera info
                    make = exif_dict.get(271)
                    model = exif_dict.get(272)
                    print(f"DEBUG: Raw make: {make}")
                    print(f"DEBUG: Raw model: {model}")
                    
                    if make:
                        exif_data.camera_make = str(make).strip()
                        print(f"DEBUG: Processed make: {exif_data.camera_make}")
                    if model:
                        exif_data.camera_model = str(model).strip()
                        print(f"DEBUG: Processed model: {exif_data.camera_model}")
                    
                    if exif_data.camera_make and exif_data.camera_model:
                        model_clean = exif_data.camera_model
                        if model_clean.startswith(exif_data.camera_make):
                            model_clean = model_clean[len(exif_data.camera_make):].strip()
                        exif_data.camera_full = f"{exif_data.camera_make} {model_clean}"
                        print(f"DEBUG: Camera full: {exif_data.camera_full}")
                    
                    print("DEBUG: PIL extraction completed successfully")
            
            except Exception as e:
                print(f"DEBUG: Exception in PIL extraction: {e}")
                import traceback
                traceback.print_exc()
            
            return exif_data
        
        # Monkey patch for debug
        ExifExtractor.debug_extract_exif_pil = debug_extract_exif_pil
        
        print("Testing debug PIL extraction:")
        result = ExifExtractor.debug_extract_exif_pil(img_path)
        
        print(f"\nFinal result:")
        print(f"  Width: {result.width}")
        print(f"  Height: {result.height}")
        print(f"  Orientation: {result.orientation}")
        print(f"  Camera: {result.camera_full}")
        
        print("\nTesting actual extraction method:")
        actual_result = ExifExtractor.extract_exif_pil(img_path)
        print(f"  Width: {actual_result.width}")
        print(f"  Height: {actual_result.height}")
        print(f"  Orientation: {actual_result.orientation}")
        print(f"  Camera: {actual_result.camera_full}")

if __name__ == "__main__":
    test_exif_extractor_with_debug()