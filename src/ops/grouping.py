from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from app.settings import Settings
    from core.search_index import NearDuplicateSearchIndex
    from store.db import DatabaseManager

# Import local modules for runtime
try:
    from app.settings import Settings
    from core.search_index import NearDuplicateSearchIndex
    from store.db import DatabaseManager
except ImportError:
    try:
        from ..app.settings import Settings
        from ..core.search_index import NearDuplicateSearchIndex
        from ..store.db import DatabaseManager
    except ImportError:
        Settings = None
        NearDuplicateSearchIndex = None
        DatabaseManager = None

# Configure logging
logger = logging.getLogger(__name__)


class GroupTier(Enum):
    """Duplicate group tier classification."""
    EXACT = "exact"      # Same size + same fast hash + SHA256 confirmation
    NEAR = "near"        # pHash within threshold + dimension sanity check


class FileFormat(Enum):
    """File format with quality priority."""
    RAW = ("raw", 1)        # Highest quality
    TIFF = ("tiff", 2)      # Lossless
    PNG = ("png", 3)        # Lossless compressed
    JPEG = ("jpeg", 4)      # Lossy compressed
    WEBP = ("webp", 5)      # Modern lossy
    OTHER = ("other", 6)    # Unknown/other formats
    
    def __init__(self, format_name: str, priority: int):
        self.format_name = format_name
        self.priority = priority
    
    @classmethod
    def from_extension(cls, ext: str) -> 'FileFormat':
        """Get format from file extension."""
        ext_lower = ext.lower().lstrip('.')
        
        # RAW formats
        raw_exts = {'raw', 'cr2', 'cr3', 'nef', 'orf', 'arw', 'dng', 'raf', 'rw2'}
        if ext_lower in raw_exts:
            return cls.RAW
        
        # Standard formats
        format_map = {
            'tiff': cls.TIFF, 'tif': cls.TIFF,
            'png': cls.PNG,
            'jpg': cls.JPEG, 'jpeg': cls.JPEG,
            'webp': cls.WEBP,
        }
        
        return format_map.get(ext_lower, cls.OTHER)


@dataclass
class FileRecord:
    """File record with all metadata for grouping."""
    id: int
    path: str
    size: int
    mtime: float
    dims_w: Optional[int]
    dims_h: Optional[int]
    exif_dt: Optional[float]
    format: Optional[str]
    
    # Hash values
    fast_hash: Optional[str] = None
    sha256: Optional[str] = None
    phash: Optional[str] = None
    dhash: Optional[str] = None
    whash: Optional[str] = None
    
    # Computed properties
    resolution: int = field(init=False)
    file_format: FileFormat = field(init=False)
    exif_datetime: Optional[datetime] = field(init=False)
    
    def __post_init__(self):
        """Compute derived properties."""
        # Calculate resolution
        if self.dims_w and self.dims_h:
            self.resolution = self.dims_w * self.dims_h
        else:
            self.resolution = 0
        
        # Determine file format
        if self.format:
            self.file_format = FileFormat.from_extension(self.format)
        else:
            # Fallback to path extension
            path_obj = Path(self.path)
            self.file_format = FileFormat.from_extension(path_obj.suffix)
        
        # Parse EXIF datetime
        if self.exif_dt:
            try:
                self.exif_datetime = datetime.fromtimestamp(self.exif_dt)
            except (ValueError, OSError):
                self.exif_datetime = None
        else:
            self.exif_datetime = None


@dataclass
class DuplicateGroup:
    """A group of duplicate files with original selection."""
    id: str
    tier: GroupTier
    original_id: int
    duplicate_ids: List[int]
    confidence_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def all_file_ids(self) -> List[int]:
        """Get all file IDs in the group."""
        return [self.original_id] + self.duplicate_ids
    
    @property
    def total_files(self) -> int:
        """Get total number of files in group."""
        return len(self.all_file_ids)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get group summary statistics."""
        return {
            'group_id': self.id,
            'tier': self.tier.value,
            'total_files': self.total_files,
            'original_id': self.original_id,
            'duplicate_count': len(self.duplicate_ids),
            'confidence_score': self.confidence_score,
            'metadata': self.metadata
        }


class GroupingEngine:
    """Two-tier duplicate grouping engine with deterministic original selection."""
    
    # Distance thresholds by performance preset
    PHASH_THRESHOLDS = {
        "Ultra-Lite": 6,
        "Balanced": 8,
        "Accurate": 12,
    }
    
    # Dimension tolerance for near-duplicate detection
    DIMENSION_TOLERANCE = 0.1  # ±10%
    
    def __init__(self, db_path: Path, settings: 'Settings'):
        """Initialize grouping engine."""
        self.db_path = db_path
        self.settings = settings
        self.db_manager = DatabaseManager(db_path)
        
        # Initialize manual override manager
        try:
            from ops.manual_override import ManualOverrideManager
            self.override_manager = ManualOverrideManager(db_path)
        except Exception as e:
            logger.warning(f"Failed to initialize manual override manager: {e}")
            self.override_manager = None
        
        # Get current performance preset
        perf_config = settings._data.get("Performance", {})
        self.current_preset = perf_config.get("current_preset", "Balanced")
        self.phash_threshold = self.PHASH_THRESHOLDS[self.current_preset]
        
        # Get grouping settings
        grouping_config = settings._data.get("Grouping", {})
        self.enable_sha256_confirmation = grouping_config.get("enable_sha256_confirmation", True)
        self.strict_mode_exif_match = grouping_config.get("strict_mode_exif_match", False)
        self.dimension_tolerance = grouping_config.get("dimension_tolerance", self.DIMENSION_TOLERANCE)
        
        # Initialize search index
        try:
            self.search_index = NearDuplicateSearchIndex(db_path, settings)
        except Exception as e:
            logger.warning(f"Failed to initialize search index: {e}")
            self.search_index = None
        
        # Statistics
        self.stats = {
            'files_processed': 0,
            'exact_groups_found': 0,
            'near_groups_found': 0,
            'total_duplicates': 0,
            'processing_time': 0.0,
            'manual_overrides_detected': 0,
            'conflicts_found': 0
        }
        
        logger.info(f"GroupingEngine initialized: preset={self.current_preset}, "
                   f"phash_threshold={self.phash_threshold}, "
                   f"sha256_confirmation={self.enable_sha256_confirmation}")
    
    def load_file_records(self) -> List[FileRecord]:
        """Load all file records with features from database."""
        logger.info("Loading file records for grouping...")
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    f.id, f.path, f.size, f.mtime, f.dims_w, f.dims_h, 
                    f.exif_dt, f.format,
                    feat.fast_hash, feat.sha256, feat.phash, feat.dhash, feat.whash
                FROM files f
                LEFT JOIN features feat ON f.id = feat.file_id
                WHERE f.status = 'active'
                ORDER BY f.id
            """)
            
            records = []
            for row in cursor.fetchall():
                record = FileRecord(
                    id=row[0], path=row[1], size=row[2], mtime=row[3],
                    dims_w=row[4], dims_h=row[5], exif_dt=row[6], format=row[7],
                    fast_hash=row[8], sha256=row[9], phash=row[10], 
                    dhash=row[11], whash=row[12]
                )
                records.append(record)
        
        logger.info(f"Loaded {len(records)} file records")
        return records
    
    def find_exact_duplicates(self, file_records: List[FileRecord]) -> List[DuplicateGroup]:
        """Find Tier 1 exact duplicates: same size + same fast hash + SHA256 confirmation."""
        logger.info("Finding exact duplicates (Tier 1)...")
        
        # Group by size and fast hash
        size_hash_groups: Dict[Tuple[int, str], List[FileRecord]] = {}
        
        for record in file_records:
            if not record.fast_hash:
                continue  # Skip files without fast hash
            
            key = (record.size, record.fast_hash)
            if key not in size_hash_groups:
                size_hash_groups[key] = []
            size_hash_groups[key].append(record)
        
        # Find groups with multiple files
        exact_groups = []
        group_id_counter = 1
        
        for (size, fast_hash), group_files in size_hash_groups.items():
            if len(group_files) < 2:
                continue  # Not a duplicate group
            
            # SHA256 confirmation if enabled
            if self.enable_sha256_confirmation:
                confirmed_groups = self._confirm_with_sha256(group_files)
                for confirmed_files in confirmed_groups:
                    if len(confirmed_files) >= 2:
                        original_id, duplicate_ids, conflict_info = self._select_original(confirmed_files)
                        group = DuplicateGroup(
                            id=f"exact_{group_id_counter}",
                            tier=GroupTier.EXACT,
                            original_id=original_id,
                            duplicate_ids=duplicate_ids,
                            confidence_score=1.0,  # Exact matches have 100% confidence
                            metadata={
                                'size': size,
                                'fast_hash': fast_hash,
                                'sha256_confirmed': True
                            }
                        )
                        exact_groups.append(group)
                        group_id_counter += 1
            else:
                # No SHA256 confirmation - use fast hash only
                original_id, duplicate_ids, conflict_info = self._select_original(group_files)
                group = DuplicateGroup(
                    id=f"exact_{group_id_counter}",
                    tier=GroupTier.EXACT,
                    original_id=original_id,
                    duplicate_ids=duplicate_ids,
                    confidence_score=0.95,  # High confidence without SHA256
                    metadata={
                        'size': size,
                        'fast_hash': fast_hash,
                        'sha256_confirmed': False
                    }
                )
                exact_groups.append(group)
                group_id_counter += 1
        
        logger.info(f"Found {len(exact_groups)} exact duplicate groups")
        return exact_groups
    
    def find_near_duplicates(self, file_records: List[FileRecord], 
                           exact_group_files: Set[int]) -> List[DuplicateGroup]:
        """Find Tier 2 near duplicates: pHash within threshold + dimension sanity check."""
        logger.info("Finding near duplicates (Tier 2)...")
        
        if not self.search_index:
            logger.warning("Search index not available, skipping near duplicates")
            return []
        
        # Build search index if needed
        if not self.search_index.is_index_built():
            logger.info("Building search index for near duplicate detection...")
            self.search_index.build_index()
        
        # Filter out files already in exact groups
        candidates = [r for r in file_records 
                     if r.id not in exact_group_files and r.phash]
        
        logger.info(f"Checking {len(candidates)} files for near duplicates")
        
        near_groups = []
        processed_files = set()
        group_id_counter = 1
        
        for record in candidates:
            if record.id in processed_files:
                continue
            
            # Find near-duplicate candidates
            similar_files = self.search_index.find_near_duplicates(
                record.id, self.phash_threshold
            )
            
            if not similar_files:
                continue
            
            # Filter candidates by dimension sanity check
            valid_candidates = []
            for candidate_info in similar_files:
                candidate_id = candidate_info['file_id']
                
                # Skip if already processed or in exact groups
                if (candidate_id in processed_files or 
                    candidate_id in exact_group_files):
                    continue
                
                # Find candidate record
                candidate_record = next(
                    (r for r in candidates if r.id == candidate_id), None
                )
                if not candidate_record:
                    continue
                
                # Dimension sanity check
                if self._dimensions_compatible(record, candidate_record):
                    # EXIF datetime match check in strict mode
                    if (self.strict_mode_exif_match and 
                        not self._exif_datetime_match(record, candidate_record)):
                        continue
                    
                    valid_candidates.append(candidate_record)
            
            # Create group if we have valid candidates
            if valid_candidates:
                group_files = [record] + valid_candidates
                original_id, duplicate_ids, conflict_info = self._select_original(group_files)
                
                # Calculate confidence score based on pHash distances
                min_distance = min(c['min_distance'] for c in similar_files 
                                 if c['file_id'] in [f.id for f in valid_candidates])
                confidence_score = max(0.1, 1.0 - (min_distance / self.phash_threshold))
                
                group = DuplicateGroup(
                    id=f"near_{group_id_counter}",
                    tier=GroupTier.NEAR,
                    original_id=original_id,
                    duplicate_ids=duplicate_ids,
                    confidence_score=confidence_score,
                    metadata={
                        'phash_threshold': self.phash_threshold,
                        'min_distance': min_distance,
                        'dimension_tolerance': self.dimension_tolerance,
                        'strict_exif_mode': self.strict_mode_exif_match
                    }
                )
                near_groups.append(group)
                group_id_counter += 1
                
                # Mark all files as processed
                for file_record in group_files:
                    processed_files.add(file_record.id)
        
        logger.info(f"Found {len(near_groups)} near duplicate groups")
        return near_groups
    
    def _confirm_with_sha256(self, files: List[FileRecord]) -> List[List[FileRecord]]:
        """Confirm duplicates using SHA256 hash comparison."""
        sha256_groups: Dict[str, List[FileRecord]] = {}
        
        for file_record in files:
            if not file_record.sha256:
                continue  # Skip files without SHA256
            
            if file_record.sha256 not in sha256_groups:
                sha256_groups[file_record.sha256] = []
            sha256_groups[file_record.sha256].append(file_record)
        
        # Return groups with 2+ files
        return [group for group in sha256_groups.values() if len(group) >= 2]
    
    def _dimensions_compatible(self, file1: FileRecord, file2: FileRecord) -> bool:
        """Check if file dimensions are compatible within tolerance."""
        if not (file1.dims_w and file1.dims_h and file2.dims_w and file2.dims_h):
            return True  # Allow if dimensions unknown
        
        # Calculate dimension ratios
        ratio1 = file1.dims_w / file1.dims_h
        ratio2 = file2.dims_w / file2.dims_h
        
        # Check aspect ratio similarity (within tolerance)
        ratio_diff = abs(ratio1 - ratio2) / max(ratio1, ratio2)
        if ratio_diff > self.dimension_tolerance:
            return False
        
        # Check resolution similarity (within tolerance)
        res_diff = abs(file1.resolution - file2.resolution) / max(file1.resolution, file2.resolution)
        if res_diff > self.dimension_tolerance:
            return False
        
        return True
    
    def _exif_datetime_match(self, file1: FileRecord, file2: FileRecord) -> bool:
        """Check if EXIF DateTimeOriginal matches between files."""
        if not (file1.exif_datetime and file2.exif_datetime):
            return True  # Allow if EXIF data missing
        
        # Allow up to 60 seconds difference (for burst photos)
        time_diff = abs((file1.exif_datetime - file2.exif_datetime).total_seconds())
        return time_diff <= 60
    
    def _select_original(self, files: List[FileRecord], group_id: Optional[int] = None) -> Tuple[int, List[int], Optional[dict]]:
        """Select original file using deterministic rules, checking for manual overrides."""
        if len(files) < 2:
            return files[0].id, [], None
        
        # Sort by original selection criteria
        sorted_files = sorted(files, key=self._original_sort_key)
        auto_original = sorted_files[0]
        auto_duplicates = [f.id for f in sorted_files[1:]]
        
        # Check for existing manual override if group_id is provided
        conflict_info = None
        final_original_id = auto_original.id
        final_duplicates = auto_duplicates
        
        if group_id and self.override_manager:
            override = self.override_manager.get_override_for_group(group_id)
            if override and override.is_active:
                # Apply manual override
                override_file_id = override.original_file_id
                
                # Verify the override file is still in the group
                override_file = next((f for f in files if f.id == override_file_id), None)
                if override_file:
                    # Apply the override
                    final_original_id = override_file_id
                    final_duplicates = [f.id for f in files if f.id != override_file_id]
                    
                    # Check if override differs from auto selection
                    if override_file_id != auto_original.id:
                        conflict_info = {
                            'group_id': group_id,
                            'auto_original_id': auto_original.id,
                            'manual_original_id': override_file_id,
                            'override_type': override.override_type.value,
                            'override_reason': override.reason.value,
                            'created_at': override.created_at,
                            'notes': override.notes
                        }
                        self.stats['conflicts_found'] += 1
                        logger.info(f"Applied manual override for group {group_id}: "
                                  f"auto={auto_original.id} -> manual={override_file_id}")
                else:
                    # Override file disappeared - deactivate override
                    logger.warning(f"Manual override file {override_file_id} not found in group {group_id}, "
                                 f"reverting to automatic selection")
                    self.override_manager.remove_override(group_id)
                    self.stats['conflicts_found'] += 1
        
        logger.debug(f"Selected original: {final_original_id} from {len(files)} files "
                    f"(auto: {auto_original.id}, manual override: {conflict_info is not None})")
        
        return final_original_id, final_duplicates, conflict_info
    
    def check_override_conflicts(self) -> List[dict]:
        """Check for conflicts between manual overrides and current automatic selection."""
        if not self.override_manager:
            return []
        
        conflicts = []
        overrides = self.override_manager.get_all_overrides(active_only=True)
        
        for override in overrides:
            try:
                # Load all files in this group
                with self.db_manager.get_connection() as conn:
                    cursor = conn.execute("""
                        SELECT f.id, f.path, f.size, f.fast_hash, f.sha256_hash, f.phash,
                               f.width, f.height, f.exif_datetime, f.status
                        FROM files f
                        JOIN group_members gm ON f.id = gm.file_id
                        WHERE gm.group_id = ? AND f.status = 'active'
                    """, (override.group_id,))
                    
                    file_data = cursor.fetchall()
                    if not file_data:
                        continue
                    
                    # Convert to FileRecord objects
                    file_records = []
                    for row in file_data:
                        file_format = FileFormat.from_extension(Path(row[1]).suffix)
                        resolution = (row[6] or 0) * (row[7] or 0)
                        exif_datetime = datetime.fromisoformat(row[8]) if row[8] else None
                        
                        file_record = FileRecord(
                            id=row[0],
                            path=row[1],
                            size=row[2],
                            fast_hash=row[3],
                            sha256_hash=row[4],
                            phash=row[5],
                            width=row[6],
                            height=row[7],
                            resolution=resolution,
                            exif_datetime=exif_datetime,
                            file_format=file_format
                        )
                        file_records.append(file_record)
                    
                    if len(file_records) < 2:
                        continue
                    
                    # Get what automatic selection would choose
                    auto_original_id, _, _ = self._select_original(file_records)
                    
                    # Check if it differs from manual override
                    if auto_original_id != override.original_file_id:
                        auto_file = next((f for f in file_records if f.id == auto_original_id), None)
                        manual_file = next((f for f in file_records if f.id == override.original_file_id), None)
                        
                        if auto_file and manual_file:
                            conflicts.append({
                                'group_id': override.group_id,
                                'auto_original_id': auto_original_id,
                                'auto_original_path': auto_file.path,
                                'manual_original_id': override.original_file_id,
                                'manual_original_path': manual_file.path,
                                'override_type': override.override_type.value,
                                'override_reason': override.reason.value,
                                'override_created': override.created_at,
                                'override_notes': override.notes,
                                'confidence_score': 0.8  # High confidence in conflict detection
                            })
            
            except Exception as e:
                logger.error(f"Error checking override conflict for group {override.group_id}: {e}")
                continue
        
        if conflicts:
            logger.info(f"Found {len(conflicts)} manual override conflicts")
            self.stats['manual_overrides_detected'] = len(conflicts)
        
        return conflicts
    
    def apply_manual_override(self, group_id: int, new_original_id: int, 
                            override_type: str = "single_group",
                            reason: str = "user_preference", 
                            notes: str = "") -> bool:
        """Apply a manual override for original selection."""
        if not self.override_manager:
            logger.error("Manual override manager not available")
            return False
        
        try:
            from ops.manual_override import OverrideType, OverrideReason, ManualOverride
            import time
            
            # Validate override type and reason
            try:
                override_type_enum = OverrideType(override_type)
                reason_enum = OverrideReason(reason)
            except ValueError as e:
                logger.error(f"Invalid override type or reason: {e}")
                return False
            
            # Get current original for this group
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT file_id FROM group_members 
                    WHERE group_id = ? AND role = 'original'
                """, (group_id,))
                
                current_original = cursor.fetchone()
                if not current_original:
                    logger.error(f"No original found for group {group_id}")
                    return False
                
                auto_original_id = current_original[0]
                
                # Verify new original exists in group
                cursor = conn.execute("""
                    SELECT file_id FROM group_members 
                    WHERE group_id = ? AND file_id = ?
                """, (group_id, new_original_id))
                
                if not cursor.fetchone():
                    logger.error(f"File {new_original_id} not found in group {group_id}")
                    return False
            
            # Create override record
            override = ManualOverride(
                id=None,
                group_id=group_id,
                original_file_id=new_original_id,
                auto_original_id=auto_original_id,
                override_type=override_type_enum,
                reason=reason_enum,
                created_at=time.time(),
                notes=notes
            )
            
            # Record the override
            override_id = self.override_manager.record_override(override)
            
            logger.info(f"Applied manual override {override_id} for group {group_id}: "
                       f"auto={auto_original_id} -> manual={new_original_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply manual override: {e}")
            return False
    
    def remove_manual_override(self, group_id: int) -> bool:
        """Remove manual override for a group (revert to automatic selection)."""
        if not self.override_manager:
            logger.error("Manual override manager not available")
            return False
        
        try:
            success = self.override_manager.remove_override(group_id)
            if success:
                logger.info(f"Removed manual override for group {group_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to remove manual override: {e}")
            return False
    
    def _original_sort_key(self, file_record: FileRecord):
        """Sort key for original selection: resolution > EXIF time > size > format priority."""
        return (
            -file_record.resolution,  # Highest resolution first (negative for descending)
            file_record.exif_datetime or datetime.max,  # Earliest EXIF time (None becomes latest)
            -file_record.size,  # Largest file size first (negative for descending)
            file_record.file_format.priority,  # Better format first (lower priority number)
            file_record.path  # Consistent tie-breaker
        )
    
    def process_all_files(self) -> Tuple[List[DuplicateGroup], Dict[str, Any]]:
        """Process all files and create duplicate groups."""
        logger.info("Starting duplicate group processing...")
        start_time = time.time()
        
        # Load file records
        file_records = self.load_file_records()
        self.stats['files_processed'] = len(file_records)
        
        # Find exact duplicates (Tier 1)
        exact_groups = self.find_exact_duplicates(file_records)
        self.stats['exact_groups_found'] = len(exact_groups)
        
        # Get file IDs in exact groups
        exact_group_files = set()
        for group in exact_groups:
            exact_group_files.update(group.all_file_ids)
        
        # Find near duplicates (Tier 2)
        near_groups = self.find_near_duplicates(file_records, exact_group_files)
        self.stats['near_groups_found'] = len(near_groups)
        
        # Calculate total duplicates
        total_duplicates = sum(len(g.duplicate_ids) for g in exact_groups + near_groups)
        self.stats['total_duplicates'] = total_duplicates
        
        # Record processing time
        self.stats['processing_time'] = time.time() - start_time
        
        all_groups = exact_groups + near_groups
        
        logger.info(f"Grouping completed in {self.stats['processing_time']:.2f}s: "
                   f"{len(exact_groups)} exact groups, {len(near_groups)} near groups, "
                   f"{total_duplicates} total duplicates")
        
        return all_groups, self.stats
    
    def store_groups(self, groups: List[DuplicateGroup]) -> int:
        """Store duplicate groups in database."""
        logger.info(f"Storing {len(groups)} duplicate groups...")
        
        with self.db_manager.get_connection() as conn:
            # Clear existing groups
            conn.execute("DELETE FROM groups")
            
            groups_stored = 0
            for group in groups:
                try:
                    # Insert group record
                    cursor = conn.execute("""
                        INSERT INTO groups (reason, score_summary, created_at)
                        VALUES (?, ?, ?)
                    """, (
                        f"{group.tier.value}_duplicates", 
                        f"confidence:{group.confidence_score:.3f}|files:{group.total_files}",
                        time.time()
                    ))
                    
                    group_db_id = cursor.lastrowid
                    
                    # Insert original file association
                    conn.execute("""
                        INSERT INTO group_members (group_id, file_id, role, similarity_score)
                        VALUES (?, ?, ?, ?)
                    """, (group_db_id, group.original_id, 'original', 1.0))
                    
                    # Insert duplicate file associations
                    for duplicate_id in group.duplicate_ids:
                        conn.execute("""
                            INSERT INTO group_members (group_id, file_id, role, similarity_score)
                            VALUES (?, ?, ?, ?)
                        """, (group_db_id, duplicate_id, 'duplicate', group.confidence_score))
                    
                    groups_stored += 1
                
                except Exception as e:
                    logger.error(f"Failed to store group {group.id}: {e}")
        
        logger.info(f"Stored {groups_stored} groups successfully")
        return groups_stored
    
    def get_group_summary(self, groups: List[DuplicateGroup]) -> Dict[str, Any]:
        """Get comprehensive summary of all groups."""
        if not groups:
            return {
                'total_groups': 0,
                'exact_groups': 0,
                'near_groups': 0,
                'total_files': 0,
                'total_duplicates': 0,
                'space_savings_estimate': 0,
                'confidence_distribution': {}
            }
        
        exact_groups = [g for g in groups if g.tier == GroupTier.EXACT]
        near_groups = [g for g in groups if g.tier == GroupTier.NEAR]
        
        total_files = sum(g.total_files for g in groups)
        total_duplicates = sum(len(g.duplicate_ids) for g in groups)
        
        # Estimate space savings (sum of duplicate file sizes)
        space_savings = 0
        try:
            with self.db_manager.get_connection() as conn:
                duplicate_ids = []
                for group in groups:
                    duplicate_ids.extend(group.duplicate_ids)
                
                if duplicate_ids:
                    placeholders = ','.join('?' * len(duplicate_ids))
                    cursor = conn.execute(f"""
                        SELECT SUM(size) FROM files 
                        WHERE id IN ({placeholders})
                    """, duplicate_ids)
                    space_savings = cursor.fetchone()[0] or 0
        except Exception as e:
            logger.error(f"Failed to calculate space savings: {e}")
        
        # Confidence distribution
        confidence_buckets = {'high': 0, 'medium': 0, 'low': 0}
        for group in groups:
            if group.confidence_score >= 0.8:
                confidence_buckets['high'] += 1
            elif group.confidence_score >= 0.5:
                confidence_buckets['medium'] += 1
            else:
                confidence_buckets['low'] += 1
        
        return {
            'total_groups': len(groups),
            'exact_groups': len(exact_groups),
            'near_groups': len(near_groups),
            'total_files': total_files,
            'total_duplicates': total_duplicates,
            'space_savings_estimate': space_savings,
            'confidence_distribution': confidence_buckets,
            'processing_stats': self.stats
        }