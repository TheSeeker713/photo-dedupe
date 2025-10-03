"""
Step 28 - Profiling Integration
Integrates performance profiling into existing photo deduplication operations.
"""

import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from functools import wraps

from core.profiler import (
    get_profiler, 
    time_scan_operation, 
    time_decode_operation,
    time_hashing_operation,
    time_grouping_operation,
    time_ui_paint_operation
)


def profile_operation(operation_name: str, include_metadata: bool = True):
    """Decorator to automatically profile function execution."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            metadata = {}
            
            if include_metadata:
                # Try to extract useful metadata from args
                if args:
                    if hasattr(args[0], '__class__'):
                        metadata['class'] = args[0].__class__.__name__
                    if len(args) > 1:
                        if isinstance(args[1], (str, Path)):
                            metadata['path'] = str(args[1])
                        elif isinstance(args[1], (list, tuple)):
                            metadata['count'] = len(args[1])
            
            profiler = get_profiler()
            with profiler.time_operation(operation_name, **metadata):
                return func(*args, **kwargs)
        return wrapper
    return decorator


class ProfiledImageScanner:
    """Image scanner with built-in performance profiling."""
    
    def __init__(self):
        self.profiler = get_profiler()
    
    @profile_operation('scan_directory')
    def scan_directory(self, directory: Path) -> List[Path]:
        """Scan directory for image files with profiling."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        image_files = []
        
        with time_scan_operation({'directory': str(directory)}):
            for file_path in directory.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    image_files.append(file_path)
        
        return image_files
    
    @profile_operation('decode_image')
    def decode_image(self, image_path: Path) -> Optional[Dict[str, Any]]:
        """Decode image with profiling."""
        try:
            from PIL import Image
            
            with time_decode_operation({'path': str(image_path), 'size': image_path.stat().st_size}):
                with Image.open(image_path) as img:
                    return {
                        'path': image_path,
                        'size': img.size,
                        'mode': img.mode,
                        'format': img.format,
                        'file_size': image_path.stat().st_size
                    }
        except Exception as e:
            return None
    
    @profile_operation('compute_hashes')
    def compute_hashes(self, image_path: Path) -> Optional[Dict[str, str]]:
        """Compute image hashes with profiling."""
        try:
            from PIL import Image
            import imagehash
            
            with time_hashing_operation({'path': str(image_path)}):
                with Image.open(image_path) as img:
                    # Compute multiple hash types
                    hashes = {
                        'average': str(imagehash.average_hash(img)),
                        'perceptual': str(imagehash.phash(img)),
                        'difference': str(imagehash.dhash(img)),
                        'wavelet': str(imagehash.whash(img)),
                    }
                    return hashes
        except Exception as e:
            return None
    
    @profile_operation('extract_features')
    def extract_features(self, image_path: Path) -> Optional[Dict[str, Any]]:
        """Extract ORB features with profiling."""
        try:
            import cv2
            import numpy as np
            
            with time_hashing_operation({'path': str(image_path), 'feature_type': 'orb'}):
                # Read image
                img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
                if img is None:
                    return None
                
                # Create ORB detector
                orb = cv2.ORB_create(nfeatures=1000)
                
                # Find keypoints and descriptors
                keypoints, descriptors = orb.detectAndCompute(img, None)
                
                return {
                    'keypoints_count': len(keypoints),
                    'descriptors': descriptors,
                    'image_size': img.shape
                }
        except Exception as e:
            return None


class ProfiledDuplicateGrouper:
    """Duplicate grouper with built-in performance profiling."""
    
    def __init__(self):
        self.profiler = get_profiler()
    
    @profile_operation('group_by_hash')
    def group_by_hash(self, images_data: List[Dict[str, Any]], hash_type: str = 'perceptual') -> Dict[str, List[int]]:
        """Group images by hash with profiling."""
        groups = {}
        
        with time_grouping_operation({'count': len(images_data), 'hash_type': hash_type}):
            for i, img_data in enumerate(images_data):
                hashes = img_data.get('hashes', {})
                hash_value = hashes.get(hash_type)
                
                if hash_value:
                    if hash_value not in groups:
                        groups[hash_value] = []
                    groups[hash_value].append(i)
        
        # Return only groups with duplicates
        return {k: v for k, v in groups.items() if len(v) > 1}
    
    @profile_operation('group_by_similarity')
    def group_by_similarity(self, images_data: List[Dict[str, Any]], threshold: float = 0.1) -> List[List[int]]:
        """Group images by similarity with profiling."""
        groups = []
        used_indices = set()
        
        with time_grouping_operation({'count': len(images_data), 'threshold': threshold}):
            for i, img1 in enumerate(images_data):
                if i in used_indices:
                    continue
                
                group = [i]
                used_indices.add(i)
                
                for j, img2 in enumerate(images_data):
                    if j <= i or j in used_indices:
                        continue
                    
                    if self._images_similar(img1, img2, threshold):
                        group.append(j)
                        used_indices.add(j)
                
                if len(group) > 1:
                    groups.append(group)
        
        return groups
    
    def _images_similar(self, img1: Dict[str, Any], img2: Dict[str, Any], threshold: float) -> bool:
        """Check if two images are similar."""
        # Simple size-based similarity for demo
        size1 = img1.get('file_size', 0)
        size2 = img2.get('file_size', 0)
        
        if size1 > 0 and size2 > 0:
            ratio = abs(size1 - size2) / max(size1, size2)
            return ratio <= threshold
        
        return False


class ProfiledUIRenderer:
    """UI renderer with built-in performance profiling."""
    
    def __init__(self):
        self.profiler = get_profiler()
    
    @profile_operation('render_image_grid')
    def render_image_grid(self, images: List[Dict[str, Any]], grid_size: tuple = (200, 200)):
        """Render image grid with profiling."""
        with time_ui_paint_operation({'count': len(images), 'grid_size': grid_size}):
            # Simulate rendering time
            time.sleep(0.01 * len(images))
            return f"Rendered {len(images)} images in grid"
    
    @profile_operation('render_thumbnail')
    def render_thumbnail(self, image_path: Path, size: tuple = (128, 128)):
        """Render thumbnail with profiling."""
        try:
            from PIL import Image
            
            with time_ui_paint_operation({'path': str(image_path), 'size': size}):
                with Image.open(image_path) as img:
                    thumbnail = img.copy()
                    thumbnail.thumbnail(size, Image.Resampling.LANCZOS)
                    return thumbnail
        except Exception as e:
            return None
    
    @profile_operation('update_progress')
    def update_progress(self, current: int, total: int, message: str = ""):
        """Update progress display with profiling."""
        with time_ui_paint_operation({'current': current, 'total': total}):
            # Simulate UI update
            progress = (current / total) * 100 if total > 0 else 0
            return f"Progress: {progress:.1f}% - {message}"


# Convenience functions for easy integration
def create_profiled_scanner() -> ProfiledImageScanner:
    """Create a profiled image scanner."""
    return ProfiledImageScanner()


def create_profiled_grouper() -> ProfiledDuplicateGrouper:
    """Create a profiled duplicate grouper."""
    return ProfiledDuplicateGrouper()


def create_profiled_renderer() -> ProfiledUIRenderer:
    """Create a profiled UI renderer."""
    return ProfiledUIRenderer()


# Integration helper for existing code
def instrument_existing_functions():
    """Instrument existing functions with profiling (example)."""
    # This function shows how to add profiling to existing code
    # without modifying the original functions
    
    profiler = get_profiler()
    
    # Example: Add profiling to an existing function
    original_function = None  # Would be imported from existing module
    
    def profiled_wrapper(*args, **kwargs):
        with profiler.time_operation('existing_function'):
            return original_function(*args, **kwargs)
    
    # Replace the original function
    # module.function_name = profiled_wrapper
    
    return profiled_wrapper