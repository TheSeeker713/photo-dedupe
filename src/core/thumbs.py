from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Optional, Tuple, Union, List

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False

try:
    from app.settings import Settings
    from core.exif import ExifExtractor
except ImportError:
    # Try relative imports if direct imports fail
    try:
        from ..app.settings import Settings
        from ..core.exif import ExifExtractor
    except ImportError:
        # If both fail, we're probably in a different context
        Settings = None
        ExifExtractor = None


class ThumbnailGenerator:
    """Thumbnail generation pipeline with configurable sizes and on-demand mode."""
    
    # Thumbnail size presets based on performance settings
    SIZE_PRESETS = {
        "Ultra-Lite": 192,   # 192px longest side
        "Balanced": 256,     # 256px longest side  
        "Accurate": 320,     # 320px longest side
    }
    
    # Decode size presets for Ultra-Lite optimization (Step 21)
    DECODE_SIZE_PRESETS = {
        "Ultra-Lite": 128,   # 128px decode size for efficiency
        "Balanced": 256,     # 256px decode size
        "Accurate": 320,     # 320px decode size
    }
    
    # Supported input formats
    SUPPORTED_FORMATS = {
        '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'
    }
    
    # Add HEIC support if available
    if HEIF_AVAILABLE:
        SUPPORTED_FORMATS.update({'.heic', '.heif'})
    
    def __init__(self, db_path: Path, settings):
        """Initialize thumbnail generator with database and settings."""
        self.db_path = db_path
        self.settings = settings
        
        # Get cache directory and create thumbs subdirectory
        cache_config = settings._data.get("Cache", {})
        cache_dir = cache_config.get("cache_dir")
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # Fallback to default cache location
            try:
                from platformdirs import user_cache_dir
                self.cache_dir = Path(user_cache_dir(settings.APP_NAME))
            except ImportError:
                import os
                self.cache_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".cache")) / settings.APP_NAME
        
        self.thumbs_dir = self.cache_dir / "thumbs"
        self.thumbs_dir.mkdir(parents=True, exist_ok=True)
        
        # Get thumbnail settings
        self.on_demand_mode = cache_config.get("on_demand_thumbs", True)
        
        # Determine thumbnail size from current performance preset
        performance_config = settings._data.get("Performance", {})
        current_preset = performance_config.get("current_preset", "Balanced")
        self.target_size = self.SIZE_PRESETS.get(current_preset, self.SIZE_PRESETS["Balanced"])
        self.decode_size = self.DECODE_SIZE_PRESETS.get(current_preset, self.DECODE_SIZE_PRESETS["Balanced"])
        
        # Check if Ultra-Lite mode is active for format restrictions
        self.is_ultra_lite = current_preset == "Ultra-Lite"
        
        # Ultra-Lite RAW/TIFF formats to skip
        self.raw_extensions = {'.cr2', '.nef', '.arw', '.dng', '.rw2', '.orf', '.pef', '.srw'}
        self.tiff_extensions = {'.tif', '.tiff'}
        
        # Quality settings
        self.webp_quality = 85
        self.png_compress_level = 6
    
    def should_skip_format(self, file_path: Path) -> bool:
        """Check if file format should be skipped in Ultra-Lite mode."""
        if not self.is_ultra_lite:
            return False
        
        file_ext = file_path.suffix.lower()
        should_skip = file_ext in self.raw_extensions or file_ext in self.tiff_extensions
        
        return should_skip
    
    def _get_hashed_filename(self, file_path: Path, size: int) -> str:
        """Generate hashed filename for thumbnail to avoid exposing original names."""
        # Include file path, size, and modification time for uniqueness
        try:
            mtime = file_path.stat().st_mtime
        except (OSError, FileNotFoundError):
            mtime = 0
        
        hash_input = f"{file_path.as_posix()}:{size}:{mtime}".encode('utf-8')
        hash_digest = hashlib.sha256(hash_input).hexdigest()[:16]  # 16 chars should be sufficient
        
        return f"thumb_{hash_digest}.webp"
    
    def _calculate_thumbnail_size(self, original_w: int, original_h: int, target_size: int) -> Tuple[int, int]:
        """Calculate thumbnail dimensions maintaining aspect ratio."""
        # Determine which dimension is larger
        if original_w >= original_h:
            # Landscape or square - scale based on width
            scale = target_size / original_w
            thumb_w = target_size
            thumb_h = max(1, int(original_h * scale))
        else:
            # Portrait - scale based on height
            scale = target_size / original_h
            thumb_h = target_size
            thumb_w = max(1, int(original_w * scale))
        
        return thumb_w, thumb_h
    
    def _create_thumbnail(self, image_path: Path, output_path: Path, target_size: int) -> Optional[Tuple[int, int]]:
        """Create a single thumbnail with orientation correction and Ultra-Lite optimization."""
        if not PIL_AVAILABLE:
            print(f"Warning: PIL not available, cannot create thumbnail for {image_path}")
            return None
        
        # Check if format should be skipped in Ultra-Lite mode
        if self.should_skip_format(image_path):
            return None
        
        try:
            # Open and process image with orientation correction
            with Image.open(image_path) as img:
                # Get EXIF data for orientation
                exif_data = ExifExtractor.extract_exif(image_path)
                
                # Apply orientation correction if needed
                if exif_data.orientation != 1:
                    img = ExifExtractor.apply_orientation(img)
                
                # Ultra-Lite optimization: Pre-scale large images to decode size
                if self.is_ultra_lite:
                    original_w, original_h = img.size
                    max_dimension = max(original_w, original_h)
                    
                    # If image is significantly larger than decode size, pre-scale it
                    if max_dimension > self.decode_size * 2:
                        decode_w, decode_h = self._calculate_thumbnail_size(
                            original_w, original_h, self.decode_size * 2
                        )
                        img = img.resize((decode_w, decode_h), Image.Resampling.LANCZOS)
                
                # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
                if img.mode not in ('RGB', 'L'):
                    if img.mode == 'RGBA':
                        # Create white background for transparent images
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    else:
                        img = img.convert('RGB')
                
                # Calculate thumbnail dimensions
                original_w, original_h = img.size
                thumb_w, thumb_h = self._calculate_thumbnail_size(original_w, original_h, target_size)
                
                # Create high-quality thumbnail
                # Use LANCZOS for high quality downscaling
                thumbnail = img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                
                # Save as WebP for efficient storage
                thumbnail.save(
                    output_path,
                    'WEBP',
                    quality=self.webp_quality,
                    method=6,  # High quality compression method
                    optimize=True
                )
                
                return thumb_w, thumb_h
                
        except Exception as e:
            print(f"Warning: Failed to create thumbnail for {image_path}: {e}")
            return None
    
    def get_or_create_thumbnail(self, file_id: int, file_path: Path) -> Optional[Path]:
        """Get existing thumbnail or create new one if needed."""
        # Check if thumbnail already exists in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT thumb_path, thumb_w, thumb_h FROM thumbs WHERE file_id = ?",
                (file_id,)
            )
            result = cursor.fetchone()
            
            if result:
                thumb_path_str, thumb_w, thumb_h = result
                thumb_path = Path(thumb_path_str)
                
                # Verify thumbnail file still exists
                if thumb_path.exists():
                    # Update last_used_at
                    conn.execute(
                        "UPDATE thumbs SET last_used_at = ? WHERE file_id = ?",
                        (time.time(), file_id)
                    )
                    return thumb_path
                else:
                    # Thumbnail file missing, remove from database
                    conn.execute("DELETE FROM thumbs WHERE file_id = ?", (file_id,))
        
        # Create new thumbnail
        return self._create_and_store_thumbnail(file_id, file_path)
    
    def _create_and_store_thumbnail(self, file_id: int, file_path: Path) -> Optional[Path]:
        """Create thumbnail and store metadata in database."""
        # Check if file format is supported
        if file_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            return None
        
        # Generate hashed filename
        thumb_filename = self._get_hashed_filename(file_path, self.target_size)
        thumb_path = self.thumbs_dir / thumb_filename
        
        # Create thumbnail
        dimensions = self._create_thumbnail(file_path, thumb_path, self.target_size)
        if not dimensions:
            return None
        
        thumb_w, thumb_h = dimensions
        
        # Store in database
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = time.time()
                conn.execute("""
                    INSERT OR REPLACE INTO thumbs 
                    (file_id, thumb_path, thumb_w, thumb_h, created_at, last_used_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (file_id, str(thumb_path), thumb_w, thumb_h, now, now))
                
            return thumb_path
            
        except sqlite3.Error as e:
            print(f"Warning: Failed to store thumbnail metadata: {e}")
            # Clean up thumbnail file if database insert failed
            if thumb_path.exists():
                try:
                    thumb_path.unlink()
                except OSError:
                    pass
            return None
    
    def precompute_thumbnails(self, file_ids: List[int], progress_callback=None) -> int:
        """Precompute thumbnails for a list of file IDs."""
        if self.on_demand_mode:
            print("Info: On-demand mode enabled, skipping precomputation")
            return 0
        
        created_count = 0
        
        # Get file information from database
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ','.join(['?'] * len(file_ids))
            cursor = conn.execute(
                f"SELECT id, file_path FROM files WHERE id IN ({placeholders})",
                file_ids
            )
            files = cursor.fetchall()
        
        total_files = len(files)
        
        for i, (file_id, file_path_str) in enumerate(files):
            file_path = Path(file_path_str)
            
            # Check if thumbnail already exists
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT thumb_path FROM thumbs WHERE file_id = ?",
                    (file_id,)
                )
                if cursor.fetchone():
                    continue  # Thumbnail already exists
            
            # Create thumbnail
            if self._create_and_store_thumbnail(file_id, file_path):
                created_count += 1
            
            # Progress callback
            if progress_callback:
                progress_callback(i + 1, total_files, file_path)
        
        return created_count
    
    def cleanup_orphaned_thumbnails(self) -> int:
        """Remove thumbnail files that no longer have database entries."""
        removed_count = 0
        
        if not self.thumbs_dir.exists():
            return 0
        
        # Get all thumbnail paths from database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT thumb_path FROM thumbs")
            db_thumbs = {Path(row[0]) for row in cursor.fetchall()}
        
        # Check all files in thumbs directory
        for thumb_file in self.thumbs_dir.iterdir():
            if thumb_file.is_file() and thumb_file not in db_thumbs:
                try:
                    thumb_file.unlink()
                    removed_count += 1
                except OSError as e:
                    print(f"Warning: Failed to remove orphaned thumbnail {thumb_file}: {e}")
        
        return removed_count
    
    def get_thumbnail_stats(self) -> dict:
        """Get thumbnail cache statistics."""
        stats = {
            'total_thumbnails': 0,
            'total_size_mb': 0.0,
            'cache_dir': str(self.thumbs_dir),
            'target_size': self.target_size,
            'on_demand_mode': self.on_demand_mode
        }
        
        if not self.thumbs_dir.exists():
            return stats
        
        # Count thumbnails and calculate total size
        total_size = 0
        count = 0
        
        for thumb_file in self.thumbs_dir.iterdir():
            if thumb_file.is_file():
                try:
                    total_size += thumb_file.stat().st_size
                    count += 1
                except OSError:
                    pass
        
        stats['total_thumbnails'] = count
        stats['total_size_mb'] = total_size / (1024 * 1024)
        
        return stats
    
    def is_supported_format(self, file_path: Path) -> bool:
        """Check if file format is supported for thumbnail generation."""
        return file_path.suffix.lower() in self.SUPPORTED_FORMATS