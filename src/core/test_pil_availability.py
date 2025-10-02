#!/usr/bin/env python3
"""Test PIL availability in our exif module."""

import sys
from pathlib import Path

def test_pil_availability():
    """Test if PIL is available in our exif module."""
    
    sys.path.insert(0, str(Path(__file__).parent))
    from exif import PIL_AVAILABLE, ExifTags
    
    print(f"PIL_AVAILABLE: {PIL_AVAILABLE}")
    print(f"ExifTags: {ExifTags}")
    
    if PIL_AVAILABLE:
        print("✓ PIL should be available")
        try:
            from PIL import Image, ExifTags as PILExifTags
            print(f"✓ Direct PIL import successful")
            print(f"  Image: {Image}")
            print(f"  ExifTags: {PILExifTags}")
        except ImportError as e:
            print(f"✗ Direct PIL import failed: {e}")
    else:
        print("✗ PIL marked as not available")

if __name__ == "__main__":
    test_pil_availability()