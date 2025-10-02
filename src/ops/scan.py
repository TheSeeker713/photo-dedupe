from __future__ import annotations

import fnmatch
import hashlib
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False

from store.db import DatabaseManager


class FileScanner:
    """File system scanner for photo-dedupe.
    
    Scans directories for image files, applies filtering rules, and updates the database
    with file metadata. Includes change detection to skip unnecessary reprocessing.
    """
    
    # Common system cache directories to ignore
    SYSTEM_CACHE_DIRS = {
        '.thumbnails', 'thumbnails', '.cache', 'cache',
        '__pycache__', '.git', '.svn', '.hg',
        'System Volume Information', '$RECYCLE.BIN',
        '.Trash', '.Trashes', 'lost+found',
        'node_modules', '.vscode', '.idea'
    }
    
    # Common image extensions
    DEFAULT_INCLUDE_PATTERNS = [
        '*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.tiff', '*.tif',
        '*.webp', '*.heic', '*.heif', '*.raw', '*.cr2', '*.nef', '*.arw',
        '*.dng', '*.rw2', '*.orf', '*.pef', '*.srw'
    ]
    
    # Minimum image size (both width and height must be >= this)
    MIN_IMAGE_SIZE = 256
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.stats = {
            'total_files_found': 0,
            'files_processed': 0,
            'files_skipped_no_change': 0,
            'files_skipped_too_small': 0,
            'files_skipped_filtered': 0,
            'files_skipped_cache_dir': 0,
            'files_added': 0,
            'files_updated': 0,
            'errors': 0,
            'scan_start_time': 0,
            'scan_end_time': 0,
        }
    
    def _compute_path_hash(self, file_path: Path) -> str:
        """Compute a stable hash for the file path."""
        # Use absolute path to ensure consistency
        abs_path = str(file_path.resolve())
        return hashlib.blake2b(abs_path.encode('utf-8'), digest_size=16).hexdigest()
    
    def _matches_patterns(self, filename: str, patterns: List[str]) -> bool:
        """Check if filename matches any of the given patterns."""
        filename_lower = filename.lower()
        for pattern in patterns:
            if fnmatch.fnmatch(filename_lower, pattern.lower()):
                return True
        return False
    
    def _is_cache_directory(self, dir_path: Path) -> bool:
        """Check if directory is a system cache directory."""
        dir_name = dir_path.name.lower()
        return dir_name in self.SYSTEM_CACHE_DIRS
    
    def _should_skip_directory(self, dir_path: Path) -> bool:
        """Check if directory should be skipped entirely."""
        # Skip cache directories
        if self._is_cache_directory(dir_path):
            return True
        
        # Skip if any parent directory is a cache directory
        for parent in dir_path.parents:
            if self._is_cache_directory(parent):
                return True
        
        return False
    
    def _get_file_stats(self, file_path: Path) -> Optional[Tuple[int, float, float]]:
        """Get file size, mtime, and ctime. Returns None if file doesn't exist."""
        try:
            stat = file_path.stat()
            return stat.st_size, stat.st_mtime, stat.st_ctime
        except (OSError, FileNotFoundError):
            return None
    
    def _get_image_dimensions(self, file_path: Path) -> Optional[Tuple[int, int]]:
        """Get image dimensions. Returns None if not an image or can't read."""
        if not PIL_AVAILABLE:
            return None
        
        try:
            with Image.open(file_path) as img:
                return img.size  # (width, height)
        except Exception:
            return None
    
    def _extract_exif_datetime(self, file_path: Path) -> Optional[float]:
        """Extract datetime from EXIF data. Returns timestamp or None."""
        if not PIEXIF_AVAILABLE:
            return None
        
        try:
            exif_dict = piexif.load(str(file_path))
            exif_ifd = exif_dict.get('Exif', {})
            
            # Try to get DateTimeOriginal first, then DateTime
            for tag in [piexif.ExifIFD.DateTimeOriginal, piexif.ExifIFD.DateTime]:
                if tag in exif_ifd:
                    date_str = exif_ifd[tag].decode('ascii')
                    # Parse format: "2023:10:02 14:30:00"
                    dt = time.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                    return time.mktime(dt)
        except Exception:
            pass
        
        return None
    
    def _extract_camera_model(self, file_path: Path) -> Optional[str]:
        """Extract camera model from EXIF data."""
        if not PIEXIF_AVAILABLE:
            return None
        
        try:
            exif_dict = piexif.load(str(file_path))
            ifd0 = exif_dict.get('0th', {})
            
            # Try to get Make and Model
            make = ifd0.get(piexif.ImageIFD.Make, b'').decode('ascii', errors='ignore').strip()
            model = ifd0.get(piexif.ImageIFD.Model, b'').decode('ascii', errors='ignore').strip()
            
            if make and model:
                return f"{make} {model}"
            elif model:
                return model
            elif make:
                return make
        except Exception:
            pass
        
        return None
    
    def _get_image_format(self, file_path: Path) -> str:
        """Get image format from file extension."""
        suffix = file_path.suffix.lower()
        format_map = {
            '.jpg': 'JPEG', '.jpeg': 'JPEG',
            '.png': 'PNG', '.gif': 'GIF', '.bmp': 'BMP',
            '.tiff': 'TIFF', '.tif': 'TIFF',
            '.webp': 'WEBP', '.heic': 'HEIC', '.heif': 'HEIF',
            '.raw': 'RAW', '.cr2': 'CR2', '.nef': 'NEF',
            '.arw': 'ARW', '.dng': 'DNG', '.rw2': 'RW2',
            '.orf': 'ORF', '.pef': 'PEF', '.srw': 'SRW'
        }
        return format_map.get(suffix, suffix.upper().lstrip('.'))
    
    def _process_file(self, file_path: Path) -> bool:
        """Process a single file and update database. Returns True if processed."""
        try:
            # Get file stats
            file_stats = self._get_file_stats(file_path)
            if not file_stats:
                self.stats['errors'] += 1
                return False
            
            size, mtime, ctime = file_stats
            path_hash = self._compute_path_hash(file_path)
            
            # Check if file exists in database and if it has changed
            existing_file = self.db.find_file_by_path(file_path)
            
            if existing_file:
                # Check if file has changed (size or mtime)
                if (existing_file['size'] == size and 
                    abs(existing_file['mtime'] - mtime) < 1.0):  # Allow 1 second tolerance
                    
                    # File unchanged, just update last_seen_at
                    with self.db.get_connection() as conn:
                        conn.execute("""
                            UPDATE files SET last_seen_at = ? WHERE id = ?
                        """, (time.time(), existing_file['id']))
                    
                    self.stats['files_skipped_no_change'] += 1
                    return True
            
            # Get image dimensions
            dimensions = self._get_image_dimensions(file_path)
            if dimensions:
                width, height = dimensions
                # Skip if image too small
                if width < self.MIN_IMAGE_SIZE or height < self.MIN_IMAGE_SIZE:
                    self.stats['files_skipped_too_small'] += 1
                    return False
            else:
                width, height = None, None
            
            # Extract metadata
            exif_dt = self._extract_exif_datetime(file_path)
            camera_model = self._extract_camera_model(file_path)
            format_str = self._get_image_format(file_path)
            
            if existing_file:
                # Update existing file
                with self.db.get_connection() as conn:
                    conn.execute("""
                        UPDATE files SET 
                            size = ?, mtime = ?, ctime = ?, dims_w = ?, dims_h = ?,
                            exif_dt = ?, camera_model = ?, format = ?,
                            last_seen_at = ?, status = 'active'
                        WHERE id = ?
                    """, (size, mtime, ctime, width, height, exif_dt, 
                          camera_model, format_str, time.time(), existing_file['id']))
                
                self.stats['files_updated'] += 1
            else:
                # Add new file
                self.db.add_file(
                    file_path=file_path,
                    size=size,
                    mtime=mtime,
                    ctime=ctime,
                    dims_w=width,
                    dims_h=height,
                    exif_dt=exif_dt,
                    camera_model=camera_model,
                    format=format_str
                )
                
                self.stats['files_added'] += 1
            
            self.stats['files_processed'] += 1
            return True
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def scan_directory(self, 
                      directory: Path,
                      recursive: bool = True,
                      include_patterns: Optional[List[str]] = None,
                      exclude_patterns: Optional[List[str]] = None) -> Dict[str, int]:
        """Scan a directory for image files and update the database.
        
        Args:
            directory: Directory to scan
            recursive: Whether to scan subdirectories
            include_patterns: File patterns to include (default: common image extensions)
            exclude_patterns: File patterns to exclude
            
        Returns:
            Dictionary with scan statistics
        """
        if include_patterns is None:
            include_patterns = self.DEFAULT_INCLUDE_PATTERNS
        
        if exclude_patterns is None:
            exclude_patterns = []
        
        # Reset stats
        self.stats = {k: 0 for k in self.stats}
        self.stats['scan_start_time'] = time.time()
        
        print(f"Scanning directory: {directory}")
        print(f"Recursive: {recursive}")
        print(f"Include patterns: {include_patterns}")
        print(f"Exclude patterns: {exclude_patterns}")
        print()
        
        try:
            if recursive:
                # Use rglob for recursive scanning
                file_pattern = "**/*"
            else:
                # Use glob for non-recursive scanning
                file_pattern = "*"
            
            for file_path in directory.glob(file_pattern):
                if not file_path.is_file():
                    continue
                
                # Skip if in cache directory
                if self._should_skip_directory(file_path.parent):
                    self.stats['files_skipped_cache_dir'] += 1
                    continue
                
                filename = file_path.name
                self.stats['total_files_found'] += 1
                
                # Apply include patterns
                if not self._matches_patterns(filename, include_patterns):
                    self.stats['files_skipped_filtered'] += 1
                    continue
                
                # Apply exclude patterns
                if exclude_patterns and self._matches_patterns(filename, exclude_patterns):
                    self.stats['files_skipped_filtered'] += 1
                    continue
                
                # Process the file
                self._process_file(file_path)
                
                # Progress reporting
                if self.stats['total_files_found'] % 100 == 0:
                    print(f"Processed {self.stats['files_processed']} files, "
                          f"found {self.stats['total_files_found']} total")
        
        except Exception as e:
            print(f"Error scanning directory {directory}: {e}")
            self.stats['errors'] += 1
        
        self.stats['scan_end_time'] = time.time()
        
        # Print final stats
        duration = self.stats['scan_end_time'] - self.stats['scan_start_time']
        print(f"\nScan completed in {duration:.2f} seconds")
        self._print_stats()
        
        return dict(self.stats)
    
    def _print_stats(self) -> None:
        """Print scan statistics."""
        print("\nScan Statistics:")
        print(f"  Total files found: {self.stats['total_files_found']}")
        print(f"  Files processed: {self.stats['files_processed']}")
        print(f"  Files added: {self.stats['files_added']}")
        print(f"  Files updated: {self.stats['files_updated']}")
        print(f"  Files skipped (no change): {self.stats['files_skipped_no_change']}")
        print(f"  Files skipped (too small): {self.stats['files_skipped_too_small']}")
        print(f"  Files skipped (filtered): {self.stats['files_skipped_filtered']}")
        print(f"  Files skipped (cache dirs): {self.stats['files_skipped_cache_dir']}")
        print(f"  Errors: {self.stats['errors']}")
    
    def mark_missing_files(self, scanned_directory: Path) -> int:
        """Mark files as missing if they weren't seen in the last scan.
        
        Returns the number of files marked as missing.
        """
        scan_time = self.stats['scan_start_time']
        if scan_time == 0:
            return 0
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Find files under the scanned directory that weren't seen recently
            dir_pattern = f"{scanned_directory}%"
            cursor.execute("""
                UPDATE files 
                SET status = 'missing' 
                WHERE path LIKE ? AND last_seen_at < ? AND status = 'active'
            """, (dir_pattern, scan_time))
            
            missing_count = cursor.rowcount
            conn.commit()
            
            if missing_count > 0:
                print(f"Marked {missing_count} files as missing")
            
            return missing_count


__all__ = ["FileScanner"]