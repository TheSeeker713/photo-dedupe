from __future__ import annotations

import datetime
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Union

try:
    from PIL import Image, ExifTags
    PIL_AVAILABLE = True
except ImportError as e:
    PIL_AVAILABLE = False
    ExifTags = None
    print(f"DEBUG: PIL import failed: {e}")

try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False


@dataclass
class ExifData:
    """Container for extracted EXIF metadata."""
    datetime_original: Optional[float] = None  # Unix timestamp
    datetime_original_raw: Optional[str] = None  # Raw EXIF string
    datetime_digitized: Optional[float] = None
    datetime_modified: Optional[float] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    camera_full: Optional[str] = None  # "Make Model"
    orientation: int = 1  # EXIF orientation (1-8)
    iso_speed: Optional[int] = None
    focal_length: Optional[float] = None
    f_number: Optional[float] = None
    exposure_time: Optional[str] = None
    flash: Optional[bool] = None
    width: Optional[int] = None
    height: Optional[int] = None
    timezone_offset: Optional[str] = None  # e.g., "+02:00"


class ExifExtractor:
    """EXIF metadata extraction and orientation handling."""
    
    # EXIF orientation values and their meanings
    ORIENTATION_TRANSFORMS = {
        1: (0, False, False),    # Normal
        2: (0, True, False),     # Mirrored horizontal
        3: (180, False, False),  # Rotated 180°
        4: (180, True, False),   # Mirrored vertical
        5: (270, True, False),   # Mirrored horizontal + rotated 270°
        6: (270, False, False),  # Rotated 270°
        7: (90, True, False),    # Mirrored horizontal + rotated 90°
        8: (90, False, False),   # Rotated 90°
    }
    
    @staticmethod
    def _parse_exif_datetime(date_str: str) -> Optional[float]:
        """Parse EXIF datetime string to Unix timestamp."""
        if not date_str:
            return None
        
        # Clean up the string
        date_str = date_str.strip()
        if not date_str:
            return None
        
        # EXIF datetime format: "YYYY:MM:DD HH:MM:SS"
        try:
            dt = datetime.datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            return dt.timestamp()
        except ValueError:
            pass
        
        # Try alternative formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y:%m:%d %H:%M:%S.%f",  # With microseconds
        ]
        
        for fmt in formats:
            try:
                dt = datetime.datetime.strptime(date_str, fmt)
                return dt.timestamp()
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def _extract_timezone_from_offset(offset_str: str) -> Optional[str]:
        """Extract timezone offset from EXIF OffsetTimeOriginal."""
        if not offset_str:
            return None
        
        # Format: "+HH:MM" or "-HH:MM"
        match = re.match(r'^([+-]\d{2}:\d{2})$', offset_str.strip())
        if match:
            return match.group(1)
        
        return None
    
    @classmethod
    def extract_exif_pil(cls, image_path: Path) -> ExifData:
        """Extract EXIF data using PIL."""
        exif_data = ExifData()
        
        if not PIL_AVAILABLE:
            return exif_data
        
        try:
            with Image.open(image_path) as img:
                # Get basic image dimensions
                exif_data.width, exif_data.height = img.size
                
                # Get EXIF data
                exif_dict = img.getexif()
                if not exif_dict:
                    return exif_data
                
                # Extract orientation (tag 274)
                orientation = exif_dict.get(274, 1)  # EXIF Orientation tag
                exif_data.orientation = orientation if 1 <= orientation <= 8 else 1
                
                # Extract datetime fields  
                datetime_original = exif_dict.get(36867)  # DateTimeOriginal tag
                if datetime_original:
                    exif_data.datetime_original_raw = str(datetime_original)
                    exif_data.datetime_original = cls._parse_exif_datetime(str(datetime_original))
                
                datetime_digitized = exif_dict.get(36868)  # DateTimeDigitized tag
                if datetime_digitized:
                    exif_data.datetime_digitized = cls._parse_exif_datetime(str(datetime_digitized))
                
                datetime_modified = exif_dict.get(306)  # DateTime tag
                if datetime_modified:
                    exif_data.datetime_modified = cls._parse_exif_datetime(str(datetime_modified))
                
                # Extract camera info
                make = exif_dict.get(271)  # Make tag
                model = exif_dict.get(272)  # Model tag
                
                if make:
                    exif_data.camera_make = str(make).strip()
                if model:
                    exif_data.camera_model = str(model).strip()
                
                if exif_data.camera_make and exif_data.camera_model:
                    # Remove duplicate make from model if present
                    model_clean = exif_data.camera_model
                    if model_clean.startswith(exif_data.camera_make):
                        model_clean = model_clean[len(exif_data.camera_make):].strip()
                    exif_data.camera_full = f"{exif_data.camera_make} {model_clean}"
                elif exif_data.camera_model:
                    exif_data.camera_full = exif_data.camera_model
                elif exif_data.camera_make:
                    exif_data.camera_full = exif_data.camera_make
                
                # Extract camera settings
                iso = exif_dict.get(34855)  # ISOSpeedRatings tag
                if iso:
                    exif_data.iso_speed = int(iso)
                
                focal_length = exif_dict.get(37386)  # FocalLength tag
                if focal_length:
                    exif_data.focal_length = float(focal_length)
                
                f_number = exif_dict.get(33437)  # FNumber tag
                if f_number:
                    exif_data.f_number = float(f_number)
                
                exposure_time = exif_dict.get(33434)  # ExposureTime tag
                if exposure_time:
                    exif_data.exposure_time = str(exposure_time)
                
                flash = exif_dict.get(37385)  # Flash tag
                if flash is not None:
                    exif_data.flash = bool(flash & 0x01)  # Flash fired bit
                
                # Try to get timezone offset
                offset_original = exif_dict.get(36881)  # OffsetTimeOriginal tag
                if offset_original:
                    exif_data.timezone_offset = cls._extract_timezone_from_offset(str(offset_original))
        
        except Exception as e:
            print(f"Warning: Failed to extract EXIF from {image_path}: {e}")
        
        return exif_data
    
    @classmethod
    def extract_exif_piexif(cls, image_path: Path) -> ExifData:
        """Extract EXIF data using piexif (fallback method)."""
        exif_data = ExifData()
        
        if not PIEXIF_AVAILABLE:
            return exif_data
        
        try:
            exif_dict = piexif.load(str(image_path))
            
            # Extract orientation from IFD0
            ifd0 = exif_dict.get('0th', {})
            orientation = ifd0.get(piexif.ImageIFD.Orientation, 1)
            exif_data.orientation = orientation if 1 <= orientation <= 8 else 1
            
            # Extract datetime from Exif IFD
            exif_ifd = exif_dict.get('Exif', {})
            
            datetime_original = exif_ifd.get(piexif.ExifIFD.DateTimeOriginal)
            if datetime_original:
                date_str = datetime_original.decode('ascii', errors='ignore')
                exif_data.datetime_original_raw = date_str
                exif_data.datetime_original = cls._parse_exif_datetime(date_str)
            
            datetime_digitized = exif_ifd.get(piexif.ExifIFD.DateTimeDigitized)
            if datetime_digitized:
                date_str = datetime_digitized.decode('ascii', errors='ignore')
                exif_data.datetime_digitized = cls._parse_exif_datetime(date_str)
            
            # Extract camera info from IFD0
            make = ifd0.get(piexif.ImageIFD.Make)
            model = ifd0.get(piexif.ImageIFD.Model)
            
            if make:
                exif_data.camera_make = make.decode('ascii', errors='ignore').strip()
            if model:
                exif_data.camera_model = model.decode('ascii', errors='ignore').strip()
            
            if exif_data.camera_make and exif_data.camera_model:
                model_clean = exif_data.camera_model
                if model_clean.startswith(exif_data.camera_make):
                    model_clean = model_clean[len(exif_data.camera_make):].strip()
                exif_data.camera_full = f"{exif_data.camera_make} {model_clean}"
            elif exif_data.camera_model:
                exif_data.camera_full = exif_data.camera_model
        
        except Exception as e:
            print(f"Warning: Failed to extract EXIF with piexif from {image_path}: {e}")
        
        return exif_data
    
    @classmethod
    def extract_exif(cls, image_path: Path) -> ExifData:
        """Extract EXIF data using the best available method."""
        # Try PIL first (more comprehensive), fall back to piexif
        exif_data = cls.extract_exif_pil(image_path)
        
        # If PIL didn't get orientation, try piexif
        if exif_data.orientation == 1 and PIEXIF_AVAILABLE:
            piexif_data = cls.extract_exif_piexif(image_path)
            if piexif_data.orientation != 1:
                exif_data.orientation = piexif_data.orientation
            
            # Fill in missing camera info from piexif if needed
            if not exif_data.camera_full and piexif_data.camera_full:
                exif_data.camera_make = piexif_data.camera_make
                exif_data.camera_model = piexif_data.camera_model
                exif_data.camera_full = piexif_data.camera_full
        
        return exif_data
    
    @classmethod
    def get_corrected_dimensions(cls, width: int, height: int, orientation: int) -> Tuple[int, int]:
        """Get dimensions after applying orientation correction."""
        if orientation in [5, 6, 7, 8]:  # Rotations that swap width/height
            return height, width
        return width, height
    
    @classmethod
    def apply_orientation(cls, image: 'Image.Image') -> 'Image.Image':
        """Apply EXIF orientation to correct image rotation."""
        if not PIL_AVAILABLE:
            return image
        
        try:
            exif_dict = image.getexif()
            if not exif_dict:
                return image
            
            orientation = exif_dict.get(274, 1)  # Orientation tag
            if orientation == 1:
                return image  # No rotation needed
            
            if orientation in cls.ORIENTATION_TRANSFORMS:
                rotate, mirror_h, mirror_v = cls.ORIENTATION_TRANSFORMS[orientation]
                
                # Apply rotation
                if rotate != 0:
                    image = image.rotate(-rotate, expand=True)
                
                # Apply mirroring
                if mirror_h:
                    image = image.transpose(Image.FLIP_LEFT_RIGHT)
                if mirror_v:
                    image = image.transpose(Image.FLIP_TOP_BOTTOM)
            
            return image
        
        except Exception as e:
            print(f"Warning: Failed to apply orientation: {e}")
            return image
    
    @classmethod
    def load_image_with_orientation(cls, image_path: Path) -> Optional['Image.Image']:
        """Load image and apply orientation correction."""
        if not PIL_AVAILABLE:
            return None
        
        try:
            with Image.open(image_path) as img:
                # Make a copy since we'll be modifying it
                img_copy = img.copy()
                return cls.apply_orientation(img_copy)
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            return None
    
    @classmethod
    def get_oriented_dimensions(cls, image_path: Path) -> Tuple[Optional[int], Optional[int]]:
        """Get image dimensions after orientation correction."""
        if not PIL_AVAILABLE:
            return None, None
        
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                
                # Get orientation
                exif_dict = img.getexif()
                orientation = exif_dict.get(274, 1) if exif_dict else 1
                
                # Apply orientation to dimensions
                return cls.get_corrected_dimensions(width, height, orientation)
        
        except Exception as e:
            print(f"Error getting dimensions for {image_path}: {e}")
            return None, None


def create_oriented_thumbnail(image_path: Path, size: Tuple[int, int] = (256, 256)) -> Optional['Image.Image']:
    """Create thumbnail with proper orientation applied."""
    if not PIL_AVAILABLE:
        return None
    
    try:
        oriented_image = ExifExtractor.load_image_with_orientation(image_path)
        if oriented_image:
            # Create thumbnail maintaining aspect ratio
            oriented_image.thumbnail(size, Image.Resampling.LANCZOS)
            return oriented_image
        else:
            # Fallback: try to load image without orientation correction
            with Image.open(image_path) as img:
                img_copy = img.copy()
                img_copy.thumbnail(size, Image.Resampling.LANCZOS)
                return img_copy
    except Exception as e:
        print(f"Error creating oriented thumbnail for {image_path}: {e}")
    
    return None


__all__ = ["ExifData", "ExifExtractor", "create_oriented_thumbnail"]