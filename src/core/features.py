from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import struct
import logging

# Core dependencies
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

# Fast hashing
try:
    import xxhash
    XXHASH_AVAILABLE = True
except ImportError:
    XXHASH_AVAILABLE = False

# Perceptual hashing
try:
    import imagehash
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False

# ORB features for accurate detection
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None
    np = None

# HEIF support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False

# Import local modules with fallback
try:
    from app.settings import Settings
    from core.exif import ExifExtractor
except ImportError:
    try:
        from ..app.settings import Settings
        from ..core.exif import ExifExtractor
    except ImportError:
        Settings = None
        ExifExtractor = None

# Configure logging
logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Comprehensive feature extraction pipeline for duplicate detection."""
    
    # Supported image formats
    SUPPORTED_FORMATS = {
        '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'
    }
    
    if HEIF_AVAILABLE:
        SUPPORTED_FORMATS.update({'.heic', '.heif'})
    
    # Hash algorithm configurations
    PHASH_SIZE = 8  # 8x8 = 64-bit perceptual hash
    DHASH_SIZE = 8  # 8x8 = 64-bit difference hash
    WHASH_SIZE = 8  # 8x8 = 64-bit wavelet hash
    
    # ORB configuration for accurate detection
    ORB_MAX_FEATURES = 500
    ORB_SCALE_FACTOR = 1.2
    ORB_N_LEVELS = 8
    
    # Low-end mode configurations
    LOW_END_MAX_DECODE_SIZE = (1024, 1024)  # Smaller decode size for low-end
    LOW_END_PHASH_ONLY = True  # Only compute pHash in low-end mode
    
    def __init__(self, db_path: Path, settings):
        """Initialize feature extractor with database and settings."""
        self.db_path = db_path
        self.settings = settings
        
        # Get performance configuration
        perf_config = settings._data.get("Performance", {})
        current_preset = perf_config.get("current_preset", "Balanced")
        self.current_preset = current_preset
        
        # Check if we're in low-end mode
        self.low_end_mode = (current_preset == "Ultra-Lite")
        
        # Get hashing configuration
        hashing_config = settings._data.get("Hashing", {})
        self.use_perceptual_hash = hashing_config.get("use_perceptual_hash", True)
        self.enable_orb_fallback = hashing_config.get("enable_orb_fallback", True)
        
        # Thresholds for duplicate detection
        thresholds = hashing_config.get("near_dupe_thresholds", {})
        if self.low_end_mode:
            # Stricter thresholds for low-end mode
            self.phash_threshold = thresholds.get("phash", 6)  # Stricter than default 8
            self.dhash_threshold = thresholds.get("dhash", 6)  # Stricter than default 8
            self.ahash_threshold = thresholds.get("ahash", 8)  # Stricter than default 10
        else:
            self.phash_threshold = thresholds.get("phash", 8)
            self.dhash_threshold = thresholds.get("dhash", 8) 
            self.ahash_threshold = thresholds.get("ahash", 10)
        
        # ORB only available in Accurate preset
        self.use_orb = (current_preset == "Accurate" and 
                       self.enable_orb_fallback and 
                       OPENCV_AVAILABLE)
        
        # Initialize ORB detector if needed
        self.orb_detector = None
        if self.use_orb:
            try:
                self.orb_detector = cv2.ORB_create(
                    nfeatures=self.ORB_MAX_FEATURES,
                    scaleFactor=self.ORB_SCALE_FACTOR,
                    nlevels=self.ORB_N_LEVELS
                )
            except Exception as e:
                logger.warning(f"Failed to initialize ORB detector: {e}")
                self.use_orb = False
        
        logger.info(f"FeatureExtractor initialized: preset={current_preset}, "
                   f"low_end={self.low_end_mode}, orb={self.use_orb}")
    
    def compute_file_hash(self, file_path: Path) -> Optional[str]:
        """Compute fast file hash for exact duplicate detection."""
        try:
            if XXHASH_AVAILABLE:
                # Use xxhash for speed
                hasher = xxhash.xxh64()
                with open(file_path, 'rb') as f:
                    while chunk := f.read(65536):  # 64KB chunks
                        hasher.update(chunk)
                return hasher.hexdigest()
            else:
                # Fallback to blake2b (faster than SHA-256)
                hasher = hashlib.blake2b()
                with open(file_path, 'rb') as f:
                    while chunk := f.read(65536):
                        hasher.update(chunk)
                return hasher.hexdigest()
        
        except Exception as e:
            logger.error(f"Failed to compute file hash for {file_path}: {e}")
            return None
    
    def compute_sha256(self, file_path: Path) -> Optional[str]:
        """Compute SHA-256 hash for confirmation."""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            return hasher.hexdigest()
        
        except Exception as e:
            logger.error(f"Failed to compute SHA-256 for {file_path}: {e}")
            return None
    
    def _load_and_prepare_image(self, file_path: Path) -> Optional[Image.Image]:
        """Load image and prepare for feature extraction."""
        if not PIL_AVAILABLE:
            logger.error("PIL not available for image processing")
            return None
        
        try:
            with Image.open(file_path) as img:
                # Apply EXIF orientation correction
                if ExifExtractor:
                    exif_data = ExifExtractor.extract_exif(file_path)
                    if exif_data.orientation != 1:
                        img = ExifExtractor.apply_orientation(img)
                
                # Convert to RGB if needed
                if img.mode not in ('RGB', 'L'):
                    if img.mode == 'RGBA':
                        # Create white background for transparent images
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    else:
                        img = img.convert('RGB')
                
                # Resize for low-end mode to reduce memory usage
                if self.low_end_mode:
                    if img.size[0] > self.LOW_END_MAX_DECODE_SIZE[0] or img.size[1] > self.LOW_END_MAX_DECODE_SIZE[1]:
                        img.thumbnail(self.LOW_END_MAX_DECODE_SIZE, Image.Resampling.LANCZOS)
                
                # Return a copy since we're using 'with' statement
                return img.copy()
        
        except Exception as e:
            logger.error(f"Failed to load image {file_path}: {e}")
            return None
    
    def compute_perceptual_hashes(self, file_path: Path) -> Dict[str, Optional[str]]:
        """Compute perceptual hashes (pHash, dHash, wHash)."""
        hashes = {
            'phash': None,
            'dhash': None,
            'whash': None
        }
        
        if not IMAGEHASH_AVAILABLE:
            logger.warning("imagehash library not available")
            return hashes
        
        img = self._load_and_prepare_image(file_path)
        if not img:
            return hashes
        
        try:
            # Always compute pHash (primary perceptual hash)
            if self.use_perceptual_hash:
                phash = imagehash.phash(img, hash_size=self.PHASH_SIZE)
                hashes['phash'] = str(phash)
            
            # In low-end mode, only compute pHash for suspects
            if not (self.low_end_mode and self.LOW_END_PHASH_ONLY):
                # Compute additional hashes for better accuracy
                dhash = imagehash.dhash(img, hash_size=self.DHASH_SIZE)
                hashes['dhash'] = str(dhash)
                
                # Wavelet hash for additional robustness
                try:
                    whash = imagehash.whash(img, hash_size=self.WHASH_SIZE)
                    hashes['whash'] = str(whash)
                except Exception as e:
                    logger.warning(f"Failed to compute wHash for {file_path}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to compute perceptual hashes for {file_path}: {e}")
        
        return hashes
    
    def compute_orb_features(self, file_path: Path) -> Optional[bytes]:
        """Compute ORB keypoints signature for hard cases (Accurate preset only)."""
        if not self.use_orb or not OPENCV_AVAILABLE:
            return None
        
        img = self._load_and_prepare_image(file_path)
        if not img:
            return None
        
        try:
            # Convert PIL image to OpenCV format
            img_array = np.array(img)
            if len(img_array.shape) == 3:
                # Convert RGB to BGR for OpenCV
                img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                # Convert to grayscale for ORB
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            else:
                gray = img_array
            
            # Detect ORB keypoints and descriptors
            keypoints, descriptors = self.orb_detector.detectAndCompute(gray, None)
            
            if descriptors is None or len(descriptors) == 0:
                logger.debug(f"No ORB features found for {file_path}")
                return None
            
            # Create a compact signature from descriptors
            # Use statistical features of the descriptor set
            desc_mean = np.mean(descriptors, axis=0).astype(np.uint8)
            desc_std = np.std(descriptors, axis=0).astype(np.uint8)
            
            # Combine mean and std into signature
            signature = np.concatenate([desc_mean, desc_std])
            
            # Add number of keypoints as metadata
            num_keypoints = min(len(keypoints), 65535)  # Limit to uint16 range
            
            # Pack into binary format: [num_keypoints:2][signature:64]
            packed = struct.pack('>H', num_keypoints) + signature.tobytes()
            
            return packed
        
        except Exception as e:
            logger.error(f"Failed to compute ORB features for {file_path}: {e}")
            return None
    
    def extract_all_features(self, file_path: Path) -> Dict[str, Any]:
        """Extract all features for a file."""
        features = {
            'file_hash': None,
            'sha256': None,
            'phash': None,
            'dhash': None,
            'whash': None,
            'orb_features': None,
            'extraction_time': time.time(),
            'errors': []
        }
        
        if not self.is_supported_format(file_path):
            features['errors'].append(f"Unsupported format: {file_path.suffix}")
            return features
        
        logger.debug(f"Extracting features for {file_path}")
        start_time = time.time()
        
        # Fast file hash (always compute)
        features['file_hash'] = self.compute_file_hash(file_path)
        if not features['file_hash']:
            features['errors'].append("Failed to compute file hash")
        
        # SHA-256 confirmation (optional, for high-value duplicates)
        if not self.low_end_mode:
            features['sha256'] = self.compute_sha256(file_path)
        
        # Perceptual hashes
        if self.use_perceptual_hash:
            perceptual_hashes = self.compute_perceptual_hashes(file_path)
            features.update(perceptual_hashes)
            
            if not any(perceptual_hashes.values()):
                features['errors'].append("Failed to compute any perceptual hashes")
        
        # ORB features (Accurate preset only)
        if self.use_orb:
            features['orb_features'] = self.compute_orb_features(file_path)
        
        # Record extraction time
        features['extraction_time'] = time.time() - start_time
        
        logger.debug(f"Feature extraction completed for {file_path} in {features['extraction_time']:.3f}s")
        
        return features
    
    def store_features(self, file_id: int, features: Dict[str, Any]) -> bool:
        """Store extracted features in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO features 
                    (file_id, fast_hash, sha256, phash, dhash, whash, orb_sig, feature_ver)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_id,
                    features.get('file_hash'),  # maps to fast_hash column
                    features.get('sha256'),
                    features.get('phash'),
                    features.get('dhash'),
                    features.get('whash'),
                    features.get('orb_features'),  # maps to orb_sig column
                    1  # feature_ver
                ))
                
                return True
        
        except sqlite3.Error as e:
            logger.error(f"Failed to store features for file_id {file_id}: {e}")
            return False
    
    def process_file(self, file_id: int, file_path: Path) -> bool:
        """Extract and store features for a single file."""
        try:
            # Extract features
            features = self.extract_all_features(file_path)
            
            # Log any errors but don't crash
            if features['errors']:
                for error in features['errors']:
                    logger.warning(f"Feature extraction error for {file_path}: {error}")
            
            # Store features in database
            success = self.store_features(file_id, features)
            
            if success:
                logger.debug(f"Successfully processed features for {file_path}")
            else:
                logger.error(f"Failed to store features for {file_path}")
            
            return success
        
        except Exception as e:
            logger.error(f"Unexpected error processing {file_path}: {e}")
            return False
    
    def process_files_batch(self, file_records: List[Tuple[int, Path]], 
                           progress_callback=None) -> int:
        """Process features for a batch of files."""
        processed_count = 0
        total_files = len(file_records)
        
        logger.info(f"Processing features for {total_files} files")
        
        for i, (file_id, file_path) in enumerate(file_records):
            if self.process_file(file_id, file_path):
                processed_count += 1
            
            # Progress callback
            if progress_callback:
                progress_callback(i + 1, total_files, file_path)
        
        logger.info(f"Feature extraction completed: {processed_count}/{total_files} files processed")
        return processed_count
    
    def get_files_needing_features(self) -> List[Tuple[int, Path]]:
        """Get list of files that need feature extraction."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT f.id, f.path
                    FROM files f
                    LEFT JOIN features feat ON f.id = feat.file_id
                    WHERE feat.file_id IS NULL
                    ORDER BY f.id
                """)
                
                return [(row[0], Path(row[1])) for row in cursor.fetchall()]
        
        except sqlite3.Error as e:
            logger.error(f"Failed to get files needing features: {e}")
            return []
    
    def compute_hash_distance(self, hash1: str, hash2: str) -> int:
        """Compute Hamming distance between two perceptual hashes."""
        if not hash1 or not hash2 or len(hash1) != len(hash2):
            return float('inf')
        
        try:
            # Convert hex strings to integers and compute XOR
            val1 = int(hash1, 16)
            val2 = int(hash2, 16)
            
            # Count set bits in XOR (Hamming distance)
            return bin(val1 ^ val2).count('1')
        
        except ValueError:
            return float('inf')
    
    def are_hashes_similar(self, hash1: str, hash2: str, hash_type: str) -> bool:
        """Check if two hashes indicate similar images."""
        distance = self.compute_hash_distance(hash1, hash2)
        
        if hash_type == 'phash':
            return distance <= self.phash_threshold
        elif hash_type == 'dhash':
            return distance <= self.dhash_threshold
        elif hash_type == 'whash':
            return distance <= self.ahash_threshold  # Use ahash threshold for whash
        
        return False
    
    def is_supported_format(self, file_path: Path) -> bool:
        """Check if file format is supported for feature extraction."""
        return file_path.suffix.lower() in self.SUPPORTED_FORMATS
    
    def get_feature_stats(self) -> Dict[str, Any]:
        """Get statistics about feature extraction."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_features,
                        COUNT(fast_hash) as files_with_hash,
                        COUNT(phash) as files_with_phash,
                        COUNT(dhash) as files_with_dhash,
                        COUNT(whash) as files_with_whash,
                        COUNT(orb_sig) as files_with_orb
                    FROM features
                """)
                
                result = cursor.fetchone()
                if result:
                    return {
                        'total_features': result[0],
                        'files_with_hash': result[1],
                        'files_with_phash': result[2],
                        'files_with_dhash': result[3],
                        'files_with_whash': result[4],
                        'files_with_orb': result[5],
                        'avg_extraction_time': 0,  # Not stored in current schema
                        'low_end_mode': self.low_end_mode,
                        'use_orb': self.use_orb,
                        'current_preset': self.current_preset
                    }
        
        except sqlite3.Error as e:
            logger.error(f"Failed to get feature stats: {e}")
        
        return {}