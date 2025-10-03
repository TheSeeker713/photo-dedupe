"""
Test Dataset Generator for Step 25 - Test dataset & validation routine.

This module creates a comprehensive mini dataset with various duplicate scenarios:
- Exact duplicates (identical files)
- Resized versions (different dimensions)
- Lightly filtered (brightness/contrast adjustments)
- Cropped versions (partial image content)
- HEIC/JPG pairs (same content, different formats)
- Wrong EXIF (incorrect metadata)
- Burst sequences (rapid succession photos)
"""

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

try:
    from PIL import Image, ImageEnhance, ImageFilter
    from PIL.ExifTags import TAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

try:
    import pillow_heif
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False


@dataclass
class TestFileSpec:
    """Specification for a test file in the dataset."""
    filename: str
    source_image: str  # Base image to derive from
    width: int
    height: int
    format: str = "JPEG"
    quality: int = 95
    
    # Transformations
    brightness: float = 1.0  # 1.0 = no change
    contrast: float = 1.0
    crop_box: Optional[Tuple[int, int, int, int]] = None  # (left, top, right, bottom)
    
    # EXIF manipulation
    fake_camera: Optional[str] = None
    fake_datetime: Optional[datetime] = None
    fake_gps: Optional[Tuple[float, float]] = None
    
    # File properties
    is_duplicate_of: Optional[str] = None  # Reference to original
    duplicate_type: str = "exact"  # exact, resized, filtered, cropped, format, exif, burst
    expected_group: str = "group1"  # Expected duplicate group


@dataclass
class ValidationExpectation:
    """Expected results for validation."""
    total_files: int
    expected_groups: Dict[str, List[str]]  # group_name -> [file1, file2, ...]
    expected_originals: Dict[str, str]  # group_name -> original_filename
    expected_deletion_candidates: List[str]
    burst_sequences: List[List[str]]  # [[file1, file2, file3], ...]


class TestDatasetGenerator:
    """Generates test datasets for validation."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Create base images directory
        self.base_images_dir = self.output_dir / "base_images"
        self.base_images_dir.mkdir(exist_ok=True)
        
        # Test dataset directory
        self.test_dir = self.output_dir / "test_dataset"
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()
    
    def create_base_images(self) -> Dict[str, Path]:
        """Create base test images of different types."""
        if not PIL_AVAILABLE:
            raise RuntimeError("PIL (Pillow) is required for test dataset generation")
        
        base_images = {}
        
        # Base image 1: Landscape photo (simulated)
        img1 = Image.new('RGB', (1920, 1080), color='blue')
        # Add some pattern to make it more realistic
        for x in range(0, 1920, 100):
            for y in range(0, 1080, 100):
                if (x + y) % 200 == 0:
                    img1.paste((255, 255, 0), (x, y, x+50, y+50))
        
        img1_path = self.base_images_dir / "landscape.jpg"
        img1.save(img1_path, "JPEG", quality=95)
        base_images['landscape'] = img1_path
        
        # Base image 2: Portrait photo
        img2 = Image.new('RGB', (1080, 1920), color='green')
        # Add circular pattern
        for x in range(0, 1080, 10):
            for y in range(0, 1920, 10):
                if ((x - 540) ** 2 + (y - 960) ** 2) % 10000 < 5000:
                    img2.paste((255, 0, 255), (x, y, x+5, y+5))
        
        img2_path = self.base_images_dir / "portrait.jpg"
        img2.save(img2_path, "JPEG", quality=95)
        base_images['portrait'] = img2_path
        
        # Base image 3: Square image for crop tests
        img3 = Image.new('RGB', (2000, 2000), color='red')
        # Add grid pattern
        for x in range(0, 2000, 200):
            for y in range(0, 2000, 200):
                img3.paste((0, 255, 255), (x, y, x+100, y+100))
        
        img3_path = self.base_images_dir / "square.jpg"
        img3.save(img3_path, "JPEG", quality=95)
        base_images['square'] = img3_path
        
        self.logger.info(f"Created {len(base_images)} base images")
        return base_images
    
    def generate_test_dataset(self) -> Tuple[List[TestFileSpec], ValidationExpectation]:
        """Generate complete test dataset with various duplicate scenarios."""
        
        # Create base images first
        base_images = self.create_base_images()
        
        test_specs = []
        
        # Group 1: Exact duplicates
        test_specs.extend([
            TestFileSpec("IMG_001_original.jpg", "landscape", 1920, 1080, 
                        expected_group="exact_dupes", duplicate_type="original"),
            TestFileSpec("IMG_001_copy.jpg", "landscape", 1920, 1080,
                        is_duplicate_of="IMG_001_original.jpg", 
                        expected_group="exact_dupes", duplicate_type="exact"),
            TestFileSpec("IMG_001_duplicate.jpg", "landscape", 1920, 1080,
                        is_duplicate_of="IMG_001_original.jpg",
                        expected_group="exact_dupes", duplicate_type="exact"),
        ])
        
        # Group 2: Resized versions
        test_specs.extend([
            TestFileSpec("IMG_002_4K.jpg", "landscape", 1920, 1080,
                        expected_group="resized_group", duplicate_type="original"),
            TestFileSpec("IMG_002_HD.jpg", "landscape", 1280, 720,
                        is_duplicate_of="IMG_002_4K.jpg",
                        expected_group="resized_group", duplicate_type="resized"),
            TestFileSpec("IMG_002_thumbnail.jpg", "landscape", 640, 360,
                        is_duplicate_of="IMG_002_4K.jpg",
                        expected_group="resized_group", duplicate_type="resized"),
        ])
        
        # Group 3: Lightly filtered versions
        test_specs.extend([
            TestFileSpec("IMG_003_original.jpg", "portrait", 1080, 1920,
                        expected_group="filtered_group", duplicate_type="original"),
            TestFileSpec("IMG_003_bright.jpg", "portrait", 1080, 1920,
                        brightness=1.3, is_duplicate_of="IMG_003_original.jpg",
                        expected_group="filtered_group", duplicate_type="filtered"),
            TestFileSpec("IMG_003_contrast.jpg", "portrait", 1080, 1920,
                        contrast=1.4, is_duplicate_of="IMG_003_original.jpg",
                        expected_group="filtered_group", duplicate_type="filtered"),
        ])
        
        # Group 4: Cropped versions
        test_specs.extend([
            TestFileSpec("IMG_004_full.jpg", "square", 2000, 2000,
                        expected_group="cropped_group", duplicate_type="original"),
            TestFileSpec("IMG_004_center_crop.jpg", "square", 1000, 1000,
                        crop_box=(500, 500, 1500, 1500), is_duplicate_of="IMG_004_full.jpg",
                        expected_group="cropped_group", duplicate_type="cropped"),
            TestFileSpec("IMG_004_corner_crop.jpg", "square", 800, 800,
                        crop_box=(0, 0, 800, 800), is_duplicate_of="IMG_004_full.jpg",
                        expected_group="cropped_group", duplicate_type="cropped"),
        ])
        
        # Group 5: Format variations (HEIC/JPG pairs) - if supported
        heic_specs = []
        if HEIF_AVAILABLE:
            heic_specs = [
                TestFileSpec("IMG_005_photo.jpg", "landscape", 1920, 1080,
                            expected_group="format_group", duplicate_type="original"),
                TestFileSpec("IMG_005_photo.heic", "landscape", 1920, 1080,
                            format="HEIF", is_duplicate_of="IMG_005_photo.jpg",
                            expected_group="format_group", duplicate_type="format"),
            ]
        else:
            # Fallback: Different JPEG qualities
            heic_specs = [
                TestFileSpec("IMG_005_high_quality.jpg", "landscape", 1920, 1080,
                            quality=95, expected_group="format_group", duplicate_type="original"),
                TestFileSpec("IMG_005_low_quality.jpg", "landscape", 1920, 1080,
                            quality=60, is_duplicate_of="IMG_005_high_quality.jpg",
                            expected_group="format_group", duplicate_type="format"),
            ]
        test_specs.extend(heic_specs)
        
        # Group 6: Wrong EXIF data
        base_time = datetime.now()
        test_specs.extend([
            TestFileSpec("IMG_006_correct_exif.jpg", "portrait", 1080, 1920,
                        fake_camera="Canon EOS R5", fake_datetime=base_time,
                        expected_group="exif_group", duplicate_type="original"),
            TestFileSpec("IMG_006_wrong_camera.jpg", "portrait", 1080, 1920,
                        fake_camera="iPhone 13 Pro", fake_datetime=base_time,
                        is_duplicate_of="IMG_006_correct_exif.jpg",
                        expected_group="exif_group", duplicate_type="exif"),
            TestFileSpec("IMG_006_wrong_time.jpg", "portrait", 1080, 1920,
                        fake_camera="Canon EOS R5", fake_datetime=base_time + timedelta(hours=2),
                        is_duplicate_of="IMG_006_correct_exif.jpg",
                        expected_group="exif_group", duplicate_type="exif"),
        ])
        
        # Group 7: Burst sequence
        burst_time = base_time + timedelta(minutes=30)
        test_specs.extend([
            TestFileSpec("IMG_007_burst_001.jpg", "landscape", 1920, 1080,
                        fake_datetime=burst_time, expected_group="burst_group", duplicate_type="burst"),
            TestFileSpec("IMG_007_burst_002.jpg", "landscape", 1920, 1080,
                        brightness=1.05,  # Slightly different exposure
                        fake_datetime=burst_time + timedelta(milliseconds=200),
                        is_duplicate_of="IMG_007_burst_001.jpg",
                        expected_group="burst_group", duplicate_type="burst"),
            TestFileSpec("IMG_007_burst_003.jpg", "landscape", 1920, 1080,
                        brightness=0.95,  # Slightly different exposure
                        fake_datetime=burst_time + timedelta(milliseconds=400),
                        is_duplicate_of="IMG_007_burst_001.jpg",
                        expected_group="burst_group", duplicate_type="burst"),
        ])
        
        # Create all test files
        for spec in test_specs:
            self._create_test_file(spec, base_images)
        
        # Define validation expectations
        expectations = ValidationExpectation(
            total_files=len(test_specs),
            expected_groups={
                "exact_dupes": ["IMG_001_original.jpg", "IMG_001_copy.jpg", "IMG_001_duplicate.jpg"],
                "resized_group": ["IMG_002_4K.jpg", "IMG_002_HD.jpg", "IMG_002_thumbnail.jpg"],
                "filtered_group": ["IMG_003_original.jpg", "IMG_003_bright.jpg", "IMG_003_contrast.jpg"],
                "cropped_group": ["IMG_004_full.jpg", "IMG_004_center_crop.jpg", "IMG_004_corner_crop.jpg"],
                "format_group": [spec.filename for spec in heic_specs],
                "exif_group": ["IMG_006_correct_exif.jpg", "IMG_006_wrong_camera.jpg", "IMG_006_wrong_time.jpg"],
                "burst_group": ["IMG_007_burst_001.jpg", "IMG_007_burst_002.jpg", "IMG_007_burst_003.jpg"],
            },
            expected_originals={
                "exact_dupes": "IMG_001_original.jpg",
                "resized_group": "IMG_002_4K.jpg",
                "filtered_group": "IMG_003_original.jpg", 
                "cropped_group": "IMG_004_full.jpg",
                "format_group": heic_specs[0].filename if heic_specs else None,
                "exif_group": "IMG_006_correct_exif.jpg",
                "burst_group": "IMG_007_burst_001.jpg",
            },
            expected_deletion_candidates=[
                "IMG_001_copy.jpg", "IMG_001_duplicate.jpg",  # Exact dupes
                "IMG_002_HD.jpg", "IMG_002_thumbnail.jpg",    # Smaller versions
                "IMG_003_bright.jpg", "IMG_003_contrast.jpg", # Filtered versions
                "IMG_004_center_crop.jpg", "IMG_004_corner_crop.jpg",  # Cropped versions
                "IMG_006_wrong_camera.jpg", "IMG_006_wrong_time.jpg",  # Wrong EXIF
                "IMG_007_burst_002.jpg", "IMG_007_burst_003.jpg",  # Burst sequence
            ],
            burst_sequences=[
                ["IMG_007_burst_001.jpg", "IMG_007_burst_002.jpg", "IMG_007_burst_003.jpg"]
            ]
        )
        
        # Add format group deletion candidate
        if len(heic_specs) > 1:
            expectations.expected_deletion_candidates.append(heic_specs[1].filename)
        
        self.logger.info(f"Generated test dataset with {len(test_specs)} files in {len(expectations.expected_groups)} groups")
        return test_specs, expectations
    
    def _create_test_file(self, spec: TestFileSpec, base_images: Dict[str, Path]) -> Path:
        """Create a single test file according to specification."""
        if not PIL_AVAILABLE:
            raise RuntimeError("PIL is required for test file creation")
        
        # Load base image
        base_path = base_images[spec.source_image]
        img = Image.open(base_path)
        
        # Apply transformations
        if spec.crop_box:
            img = img.crop(spec.crop_box)
        
        if spec.width != img.width or spec.height != img.height:
            img = img.resize((spec.width, spec.height), Image.Resampling.LANCZOS)
        
        if spec.brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(spec.brightness)
        
        if spec.contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(spec.contrast)
        
        # Prepare EXIF data
        exif_dict = {}
        if spec.fake_camera:
            exif_dict['0th'] = {
                256: spec.width,  # ImageWidth
                257: spec.height,  # ImageLength
                272: spec.fake_camera,  # Make/Model combined
            }
        
        if spec.fake_datetime:
            datetime_str = spec.fake_datetime.strftime("%Y:%m:%d %H:%M:%S")
            if '0th' not in exif_dict:
                exif_dict['0th'] = {}
            exif_dict['0th'][306] = datetime_str  # DateTime
        
        # Save file
        output_path = self.test_dir / spec.filename
        
        if spec.format.upper() == "HEIF" and HEIF_AVAILABLE:
            # Save as HEIC
            pillow_heif.register_heif_opener()
            img.save(output_path.with_suffix('.heic'), "HEIF", quality=spec.quality)
        else:
            # Save as JPEG
            save_kwargs = {"format": "JPEG", "quality": spec.quality}
            if exif_dict:
                try:
                    import piexif
                    exif_bytes = piexif.dump(exif_dict)
                    save_kwargs["exif"] = exif_bytes
                except ImportError:
                    pass  # Skip EXIF if piexif not available
            
            img.save(output_path, **save_kwargs)
        
        return output_path
    
    def get_test_directory(self) -> Path:
        """Get the path to the generated test dataset."""
        return self.test_dir
    
    def cleanup(self):
        """Clean up generated test files."""
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)