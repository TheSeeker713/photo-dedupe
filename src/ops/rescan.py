"""
Step 23 - Rescan & Delta Updates System

This module provides efficient incremental rescanning that only processes
new or changed files, plus a full rebuild option that preserves user data.

Features:
- Delta update scanning (size/mtime comparison)
- Fast path for thumbnail and feature reuse
- Full rebuild with selective data preservation
- Manual override preservation during rebuild
- Performance monitoring and statistics
"""

import logging
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from enum import Enum

try:
    from PySide6.QtCore import QObject, Signal
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QObject = object
    Signal = lambda *args, **kwargs: None

logger = logging.getLogger(__name__)


class RescanMode(Enum):
    """Rescan operation modes."""
    DELTA_ONLY = "delta_only"          # Only process new/changed files
    MISSING_FEATURES = "missing_features"  # Process files missing features/thumbs
    FULL_REBUILD = "full_rebuild"      # Complete rebuild preserving user data


@dataclass
class RescanStats:
    """Statistics for rescan operations."""
    mode: RescanMode
    start_time: float
    end_time: Optional[float] = None
    
    # File scanning
    files_scanned: int = 0
    files_new: int = 0
    files_changed: int = 0
    files_unchanged: int = 0
    files_missing: int = 0
    
    # Processing
    files_processed: int = 0
    features_extracted: int = 0
    thumbnails_created: int = 0
    features_reused: int = 0
    thumbnails_reused: int = 0
    
    # Rebuild specific
    groups_preserved: int = 0
    overrides_preserved: int = 0
    features_cleared: int = 0
    thumbnails_cleared: int = 0
    
    # Performance
    scan_duration: float = 0.0
    processing_duration: float = 0.0
    total_duration: float = 0.0
    
    # Errors
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def files_total(self) -> int:
        return self.files_new + self.files_changed + self.files_unchanged
    
    @property
    def speed_files_per_second(self) -> float:
        if self.total_duration > 0:
            return self.files_processed / self.total_duration
        return 0.0
    
    @property
    def efficiency_ratio(self) -> float:
        """Ratio of reused vs. newly processed items."""
        total_items = self.features_extracted + self.features_reused + self.thumbnails_created + self.thumbnails_reused
        if total_items > 0:
            reused_items = self.features_reused + self.thumbnails_reused
            return reused_items / total_items
        return 0.0


@dataclass
class ChangeDetectionResult:
    """Result of file change detection."""
    file_id: int
    file_path: Path
    is_new: bool
    is_changed: bool
    needs_features: bool
    needs_thumbnail: bool
    old_size: Optional[int] = None
    new_size: Optional[int] = None
    old_mtime: Optional[float] = None
    new_mtime: Optional[float] = None


class RescanManager:
    """Manages incremental rescanning and full rebuilds."""
    
    def __init__(self, db_path: Path, settings):
        self.db_path = db_path
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        try:
            from store.db import DatabaseManager
            from ops.scan import FileScanner
            from core.features import FeatureExtractor
            from core.thumbs import ThumbnailGenerator
            
            self.db_manager = DatabaseManager(db_path)
            self.file_scanner = FileScanner(self.db_manager)
            self.feature_extractor = FeatureExtractor(db_path, settings)
            self.thumbnail_generator = ThumbnailGenerator(db_path, settings)
            
        except Exception as e:
            self.logger.error(f"Failed to initialize rescan components: {e}")
            raise
        
        # Statistics
        self.current_stats: Optional[RescanStats] = None
    
    def perform_delta_rescan(self, scan_paths: List[Path], 
                           progress_callback=None) -> RescanStats:
        """Perform delta rescan - only process new/changed files."""
        self.logger.info("Starting delta rescan...")
        
        stats = RescanStats(
            mode=RescanMode.DELTA_ONLY,
            start_time=time.time()
        )
        self.current_stats = stats
        
        try:
            # Phase 1: Scan filesystem and detect changes
            self.logger.info("Phase 1: Scanning filesystem for changes...")
            scan_start = time.time()
            
            changes = self._detect_file_changes(scan_paths, progress_callback)
            
            stats.scan_duration = time.time() - scan_start
            stats.files_scanned = len(changes)
            stats.files_new = sum(1 for c in changes if c.is_new)
            stats.files_changed = sum(1 for c in changes if c.is_changed and not c.is_new)
            stats.files_unchanged = stats.files_scanned - stats.files_new - stats.files_changed
            
            self.logger.info(f"Scan complete: {stats.files_new} new, {stats.files_changed} changed, "
                           f"{stats.files_unchanged} unchanged files")
            
            # Phase 2: Process changed files
            self.logger.info("Phase 2: Processing new and changed files...")
            process_start = time.time()
            
            files_to_process = [c for c in changes if c.is_new or c.is_changed or c.needs_features or c.needs_thumbnail]
            
            if files_to_process:
                self._process_file_changes(files_to_process, stats, progress_callback)
            
            stats.processing_duration = time.time() - process_start
            
            # Phase 3: Mark missing files
            self._mark_missing_files(changes, stats)
            
            # Update statistics
            stats.end_time = time.time()
            stats.total_duration = stats.end_time - stats.start_time
            
            self.logger.info(f"Delta rescan completed in {stats.total_duration:.2f}s: "
                           f"{stats.files_processed} files processed, "
                           f"{stats.features_reused} features reused, "
                           f"{stats.thumbnails_reused} thumbnails reused")
            
            return stats
            
        except Exception as e:
            error_msg = f"Delta rescan failed: {str(e)}"
            stats.errors.append(error_msg)
            self.logger.error(error_msg)
            raise
    
    def perform_missing_features_rescan(self, progress_callback=None) -> RescanStats:
        """Rescan to process files missing features or thumbnails."""
        self.logger.info("Starting missing features rescan...")
        
        stats = RescanStats(
            mode=RescanMode.MISSING_FEATURES,
            start_time=time.time()
        )
        self.current_stats = stats
        
        try:
            # Find files missing features or thumbnails
            files_needing_work = self._find_files_needing_processing()
            
            stats.files_scanned = len(files_needing_work)
            stats.files_processed = len(files_needing_work)
            
            if files_needing_work:
                self.logger.info(f"Processing {len(files_needing_work)} files with missing features/thumbnails")
                self._process_missing_features(files_needing_work, stats, progress_callback)
            else:
                self.logger.info("No files need feature or thumbnail processing")
            
            stats.end_time = time.time()
            stats.total_duration = stats.end_time - stats.start_time
            
            return stats
            
        except Exception as e:
            error_msg = f"Missing features rescan failed: {str(e)}"
            stats.errors.append(error_msg)
            self.logger.error(error_msg)
            raise
    
    def perform_full_rebuild(self, scan_paths: List[Path], 
                           preserve_overrides: bool = True,
                           preserve_groups: bool = True,
                           progress_callback=None) -> RescanStats:
        """Perform full rebuild while preserving user data."""
        self.logger.info("Starting full rebuild...")
        
        stats = RescanStats(
            mode=RescanMode.FULL_REBUILD,
            start_time=time.time()
        )
        self.current_stats = stats
        
        try:
            # Phase 1: Backup user data
            if preserve_overrides or preserve_groups:
                self.logger.info("Phase 1: Backing up user data...")
                backup_data = self._backup_user_data(preserve_overrides, preserve_groups)
            else:
                backup_data = None
            
            # Phase 2: Clear features and thumbnails
            self.logger.info("Phase 2: Clearing features and thumbnails...")
            cleared_stats = self._clear_computed_data()
            stats.features_cleared = cleared_stats['features_cleared']
            stats.thumbnails_cleared = cleared_stats['thumbnails_cleared']
            
            # Phase 3: Full filesystem scan
            self.logger.info("Phase 3: Full filesystem scan...")
            scan_start = time.time()
            
            # Reset file scanner stats
            self.file_scanner.stats = {key: 0 for key in self.file_scanner.stats}
            
            # Perform full scan
            for scan_path in scan_paths:
                self.file_scanner.scan_directory(scan_path, progress_callback=progress_callback)
            
            stats.scan_duration = time.time() - scan_start
            stats.files_scanned = self.file_scanner.stats['files_processed']
            stats.files_new = self.file_scanner.stats['files_added']
            stats.files_changed = self.file_scanner.stats['files_updated']
            
            # Phase 4: Process all files for features and thumbnails
            self.logger.info("Phase 4: Processing all files...")
            process_start = time.time()
            
            all_files = self._get_all_active_files()
            if all_files:
                self._process_all_files_rebuild(all_files, stats, progress_callback)
            
            stats.processing_duration = time.time() - process_start
            
            # Phase 5: Restore user data
            if backup_data:
                self.logger.info("Phase 5: Restoring user data...")
                restore_stats = self._restore_user_data(backup_data)
                stats.groups_preserved = restore_stats['groups_restored']
                stats.overrides_preserved = restore_stats['overrides_restored']
            
            stats.end_time = time.time()
            stats.total_duration = stats.end_time - stats.start_time
            
            self.logger.info(f"Full rebuild completed in {stats.total_duration:.2f}s: "
                           f"{stats.files_processed} files processed, "
                           f"{stats.groups_preserved} groups preserved, "
                           f"{stats.overrides_preserved} overrides preserved")
            
            return stats
            
        except Exception as e:
            error_msg = f"Full rebuild failed: {str(e)}"
            stats.errors.append(error_msg)
            self.logger.error(error_msg)
            raise
    
    def _detect_file_changes(self, scan_paths: List[Path], 
                           progress_callback=None) -> List[ChangeDetectionResult]:
        """Detect file changes by comparing filesystem to database."""
        changes = []
        
        with self.db_manager.get_connection() as conn:
            # Get all existing files from database
            cursor = conn.execute("""
                SELECT id, path, size, mtime, status
                FROM files
                WHERE status = 'active'
            """)
            
            existing_files = {}
            for row in cursor.fetchall():
                file_path = Path(row[1])
                existing_files[file_path] = {
                    'id': row[0],
                    'size': row[2],
                    'mtime': row[3],
                    'status': row[4]
                }
            
            # Track seen files to detect missing ones later
            seen_files = set()
            
            # Scan filesystem
            file_count = 0
            for scan_path in scan_paths:
                for file_path in self._walk_image_files(scan_path):
                    if progress_callback and file_count % 100 == 0:
                        progress_callback(f"Scanning: {file_path.name}", file_count)
                    
                    seen_files.add(file_path)
                    file_count += 1
                    
                    try:
                        stat = file_path.stat()
                        current_size = stat.st_size
                        current_mtime = stat.st_mtime
                        
                        if file_path in existing_files:
                            # Existing file - check for changes
                            existing = existing_files[file_path]
                            
                            size_changed = existing['size'] != current_size
                            mtime_changed = abs(existing['mtime'] - current_mtime) >= 1.0
                            
                            is_changed = size_changed or mtime_changed
                            
                            # Check if features/thumbnails exist
                            needs_features = self._file_needs_features(existing['id'])
                            needs_thumbnail = self._file_needs_thumbnail(existing['id'])
                            
                            changes.append(ChangeDetectionResult(
                                file_id=existing['id'],
                                file_path=file_path,
                                is_new=False,
                                is_changed=is_changed,
                                needs_features=needs_features,
                                needs_thumbnail=needs_thumbnail,
                                old_size=existing['size'],
                                new_size=current_size,
                                old_mtime=existing['mtime'],
                                new_mtime=current_mtime
                            ))
                        else:
                            # New file
                            changes.append(ChangeDetectionResult(
                                file_id=-1,  # Will be assigned during processing
                                file_path=file_path,
                                is_new=True,
                                is_changed=False,
                                needs_features=True,
                                needs_thumbnail=True,
                                new_size=current_size,
                                new_mtime=current_mtime
                            ))
                    
                    except (OSError, IOError) as e:
                        self.logger.warning(f"Failed to stat file {file_path}: {e}")
                        continue
            
            # Identify missing files
            missing_files = set(existing_files.keys()) - seen_files
            for missing_path in missing_files:
                existing = existing_files[missing_path]
                changes.append(ChangeDetectionResult(
                    file_id=existing['id'],
                    file_path=missing_path,
                    is_new=False,
                    is_changed=False,
                    needs_features=False,
                    needs_thumbnail=False,
                    old_size=existing['size'],
                    old_mtime=existing['mtime']
                ))
        
        return changes
    
    def _walk_image_files(self, root_path: Path):
        """Walk directory tree and yield image files."""
        include_patterns = self.file_scanner.DEFAULT_INCLUDE_PATTERNS
        
        for item in root_path.rglob("*"):
            if item.is_file():
                if self.file_scanner._matches_patterns(item.name, include_patterns):
                    if not self.file_scanner._should_skip_directory(item.parent):
                        yield item
    
    def _file_needs_features(self, file_id: int) -> bool:
        """Check if file needs feature extraction."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM features WHERE file_id = ?
            """, (file_id,))
            return cursor.fetchone()[0] == 0
    
    def _file_needs_thumbnail(self, file_id: int) -> bool:
        """Check if file needs thumbnail generation."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM thumbs WHERE file_id = ?
            """, (file_id,))
            return cursor.fetchone()[0] == 0
    
    def _process_file_changes(self, changes: List[ChangeDetectionResult], 
                            stats: RescanStats, progress_callback=None):
        """Process files that are new or changed."""
        processed_count = 0
        
        for change in changes:
            if progress_callback:
                progress_callback(f"Processing: {change.file_path.name}", processed_count)
            
            try:
                # Handle new files
                if change.is_new:
                    file_id = self._add_new_file(change.file_path)
                    change.file_id = file_id
                    stats.files_new += 1
                elif change.is_changed:
                    self._update_changed_file(change)
                    stats.files_changed += 1
                
                # Process features
                if change.needs_features or change.is_changed:
                    if self.feature_extractor.process_file(change.file_id, change.file_path):
                        stats.features_extracted += 1
                    else:
                        stats.errors.append(f"Failed to extract features for {change.file_path}")
                else:
                    stats.features_reused += 1
                
                # Process thumbnails
                if change.needs_thumbnail or change.is_changed:
                    if self.thumbnail_generator.get_or_create_thumbnail(change.file_id, change.file_path):
                        stats.thumbnails_created += 1
                    else:
                        stats.errors.append(f"Failed to create thumbnail for {change.file_path}")
                else:
                    stats.thumbnails_reused += 1
                
                stats.files_processed += 1
                processed_count += 1
                
            except Exception as e:
                error_msg = f"Failed to process {change.file_path}: {str(e)}"
                stats.errors.append(error_msg)
                self.logger.error(error_msg)
        
    def _add_new_file(self, file_path: Path) -> int:
        """Add new file to database and return file ID."""
        stat = file_path.stat()
        
        # Extract basic metadata
        width, height = None, None
        exif_datetime = None
        camera_model = None
        file_format = file_path.suffix.lstrip('.').lower()
        
        try:
            # Try to get image dimensions
            from PIL import Image
            with Image.open(file_path) as img:
                width, height = img.size
        except Exception:
            pass
        
        try:
            # Try to get EXIF data
            from core.exif import ExifProcessor
            exif_processor = ExifProcessor()
            exif_data = exif_processor.extract_exif(file_path)
            if exif_data and exif_data.datetime:
                exif_datetime = exif_data.datetime.timestamp()
            if exif_data and exif_data.camera_model:
                camera_model = exif_data.camera_model
        except Exception:
            pass
        
        return self.db_manager.add_file(
            file_path=file_path,
            size=stat.st_size,
            mtime=stat.st_mtime,
            ctime=stat.st_ctime,
            dims_w=width,
            dims_h=height,
            exif_dt=exif_datetime,
            camera_model=camera_model,
            format=file_format
        )
    
    def _update_changed_file(self, change: ChangeDetectionResult):
        """Update changed file in database."""
        with self.db_manager.get_connection() as conn:
            conn.execute("""
                UPDATE files 
                SET size = ?, mtime = ?, last_seen_at = ?
                WHERE id = ?
            """, (change.new_size, change.new_mtime, time.time(), change.file_id))
            
            # Clear old features and thumbnails for changed files
            conn.execute("DELETE FROM features WHERE file_id = ?", (change.file_id,))
            conn.execute("DELETE FROM thumbs WHERE file_id = ?", (change.file_id,))
    
    def _mark_missing_files(self, changes: List[ChangeDetectionResult], stats: RescanStats):
        """Mark files that no longer exist as missing."""
        missing_changes = [c for c in changes if not c.file_path.exists()]
        
        if missing_changes:
            with self.db_manager.get_connection() as conn:
                for change in missing_changes:
                    conn.execute("""
                        UPDATE files SET status = 'missing', last_seen_at = ?
                        WHERE id = ?
                    """, (time.time(), change.file_id))
                    
                    stats.files_missing += 1
            
            self.logger.info(f"Marked {len(missing_changes)} files as missing")
    
    def _find_files_needing_processing(self) -> List[Tuple[int, Path]]:
        """Find files that need feature extraction or thumbnail generation."""
        files_needing_work = []
        
        with self.db_manager.get_connection() as conn:
            # Files missing features
            cursor = conn.execute("""
                SELECT f.id, f.path
                FROM files f
                LEFT JOIN features feat ON f.id = feat.file_id
                WHERE f.status = 'active' AND feat.file_id IS NULL
            """)
            
            for row in cursor.fetchall():
                files_needing_work.append((row[0], Path(row[1])))
            
            # Files missing thumbnails (not already in the list)
            file_ids_with_features = {item[0] for item in files_needing_work}
            
            cursor = conn.execute("""
                SELECT f.id, f.path
                FROM files f
                LEFT JOIN thumbs t ON f.id = t.file_id
                WHERE f.status = 'active' AND t.file_id IS NULL
            """)
            
            for row in cursor.fetchall():
                if row[0] not in file_ids_with_features:
                    files_needing_work.append((row[0], Path(row[1])))
        
        return files_needing_work
    
    def _process_missing_features(self, files_needing_work: List[Tuple[int, Path]], 
                                stats: RescanStats, progress_callback=None):
        """Process files missing features or thumbnails."""
        for i, (file_id, file_path) in enumerate(files_needing_work):
            if progress_callback:
                progress_callback(f"Processing: {file_path.name}", i)
            
            try:
                # Check if file still exists
                if not file_path.exists():
                    self.logger.warning(f"File no longer exists: {file_path}")
                    continue
                
                # Extract features if missing
                if self._file_needs_features(file_id):
                    if self.feature_extractor.process_file(file_id, file_path):
                        stats.features_extracted += 1
                
                # Create thumbnail if missing
                if self._file_needs_thumbnail(file_id):
                    if self.thumbnail_generator.get_or_create_thumbnail(file_id, file_path):
                        stats.thumbnails_created += 1
                
            except Exception as e:
                error_msg = f"Failed to process {file_path}: {str(e)}"
                stats.errors.append(error_msg)
                self.logger.error(error_msg)
    
    def _backup_user_data(self, preserve_overrides: bool, preserve_groups: bool) -> Dict[str, Any]:
        """Backup user data before rebuild."""
        backup_data = {
            'overrides': [],
            'groups': [],
            'group_members': []
        }
        
        with self.db_manager.get_connection() as conn:
            if preserve_overrides:
                # Backup manual overrides if available
                try:
                    cursor = conn.execute("SELECT * FROM manual_overrides WHERE is_active = 1")
                    backup_data['overrides'] = [dict(row) for row in cursor.fetchall()]
                except Exception:
                    # Table might not exist
                    pass
            
            if preserve_groups:
                # Backup groups and memberships
                cursor = conn.execute("SELECT * FROM groups")
                backup_data['groups'] = [dict(row) for row in cursor.fetchall()]
                
                cursor = conn.execute("SELECT * FROM group_members")
                backup_data['group_members'] = [dict(row) for row in cursor.fetchall()]
        
        return backup_data
    
    def _clear_computed_data(self) -> Dict[str, int]:
        """Clear features and thumbnails tables."""
        cleared_stats = {'features_cleared': 0, 'thumbnails_cleared': 0}
        
        with self.db_manager.get_connection() as conn:
            # Count before clearing
            cursor = conn.execute("SELECT COUNT(*) FROM features")
            cleared_stats['features_cleared'] = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM thumbs")
            cleared_stats['thumbnails_cleared'] = cursor.fetchone()[0]
            
            # Clear tables
            conn.execute("DELETE FROM features")
            conn.execute("DELETE FROM thumbs")
            conn.execute("DELETE FROM groups")
            conn.execute("DELETE FROM group_members")
        
        # Clear thumbnail files
        try:
            thumb_dir = self.thumbnail_generator.thumbs_dir
            if thumb_dir.exists():
                shutil.rmtree(thumb_dir)
                thumb_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.warning(f"Failed to clear thumbnail directory: {e}")
        
        return cleared_stats
    
    def _get_all_active_files(self) -> List[Tuple[int, Path]]:
        """Get all active files from database."""
        files = []
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, path FROM files WHERE status = 'active'
            """)
            
            for row in cursor.fetchall():
                files.append((row[0], Path(row[1])))
        
        return files
    
    def _process_all_files_rebuild(self, all_files: List[Tuple[int, Path]], 
                                 stats: RescanStats, progress_callback=None):
        """Process all files during rebuild."""
        for i, (file_id, file_path) in enumerate(all_files):
            if progress_callback:
                progress_callback(f"Processing: {file_path.name}", i)
            
            try:
                if not file_path.exists():
                    continue
                
                # Extract features
                if self.feature_extractor.process_file(file_id, file_path):
                    stats.features_extracted += 1
                
                # Create thumbnail
                if self.thumbnail_generator.get_or_create_thumbnail(file_id, file_path):
                    stats.thumbnails_created += 1
                
                stats.files_processed += 1
                
            except Exception as e:
                error_msg = f"Failed to process {file_path}: {str(e)}"
                stats.errors.append(error_msg)
                self.logger.error(error_msg)
    
    def _restore_user_data(self, backup_data: Dict[str, Any]) -> Dict[str, int]:
        """Restore user data after rebuild."""
        restore_stats = {'groups_restored': 0, 'overrides_restored': 0}
        
        with self.db_manager.get_connection() as conn:
            try:
                # Restore groups
                for group in backup_data.get('groups', []):
                    conn.execute("""
                        INSERT OR REPLACE INTO groups (id, reason, score_summary, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (group['id'], group['reason'], group['score_summary'], group['created_at']))
                    restore_stats['groups_restored'] += 1
                
                # Restore group members (only if files still exist)
                for member in backup_data.get('group_members', []):
                    # Check if file still exists
                    cursor = conn.execute("SELECT COUNT(*) FROM files WHERE id = ? AND status = 'active'", 
                                        (member['file_id'],))
                    if cursor.fetchone()[0] > 0:
                        conn.execute("""
                            INSERT OR REPLACE INTO group_members 
                            (group_id, file_id, role, similarity_score, notes)
                            VALUES (?, ?, ?, ?, ?)
                        """, (member['group_id'], member['file_id'], member['role'], 
                             member['similarity_score'], member['notes']))
                
                # Restore manual overrides if table exists
                if backup_data.get('overrides'):
                    try:
                        for override in backup_data['overrides']:
                            # Check if both files still exist
                            cursor = conn.execute("""
                                SELECT COUNT(*) FROM files 
                                WHERE id IN (?, ?) AND status = 'active'
                            """, (override['original_file_id'], override['auto_original_id']))
                            
                            if cursor.fetchone()[0] == 2:
                                conn.execute("""
                                    INSERT OR REPLACE INTO manual_overrides 
                                    (id, group_id, original_file_id, auto_original_id, 
                                     override_type, reason, created_at, notes, is_active)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (override['id'], override['group_id'], override['original_file_id'],
                                     override['auto_original_id'], override['override_type'],
                                     override['reason'], override['created_at'], override['notes'],
                                     override['is_active']))
                                restore_stats['overrides_restored'] += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to restore manual overrides: {e}")
            
            except Exception as e:
                self.logger.error(f"Failed to restore user data: {e}")
                raise
        
        return restore_stats
    
    def get_rescan_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for rescan strategy based on current state."""
        recommendations = {
            'recommended_mode': RescanMode.DELTA_ONLY,
            'reasons': [],
            'estimated_files_to_process': 0,
            'database_stats': {}
        }
        
        try:
            # Get database statistics
            with self.db_manager.get_connection() as conn:
                # Count files, features, thumbnails
                cursor = conn.execute("""
                    SELECT 
                        (SELECT COUNT(*) FROM files WHERE status = 'active') as active_files,
                        (SELECT COUNT(*) FROM features) as features_count,
                        (SELECT COUNT(*) FROM thumbs) as thumbs_count,
                        (SELECT COUNT(*) FROM groups) as groups_count
                """)
                
                stats = cursor.fetchone()
                recommendations['database_stats'] = {
                    'active_files': stats[0],
                    'features_count': stats[1],
                    'thumbs_count': stats[2],
                    'groups_count': stats[3]
                }
                
                # Files missing features
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM files f
                    LEFT JOIN features feat ON f.id = feat.file_id
                    WHERE f.status = 'active' AND feat.file_id IS NULL
                """)
                missing_features = cursor.fetchone()[0]
                
                # Files missing thumbnails
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM files f
                    LEFT JOIN thumbs t ON f.id = t.file_id
                    WHERE f.status = 'active' AND t.file_id IS NULL
                """)
                missing_thumbs = cursor.fetchone()[0]
                
                # Determine recommendation
                if missing_features > stats[0] * 0.5 or missing_thumbs > stats[0] * 0.5:
                    recommendations['recommended_mode'] = RescanMode.FULL_REBUILD
                    recommendations['reasons'].append("More than 50% of files missing features or thumbnails")
                    recommendations['estimated_files_to_process'] = stats[0]
                elif missing_features > 0 or missing_thumbs > 0:
                    recommendations['recommended_mode'] = RescanMode.MISSING_FEATURES
                    recommendations['reasons'].append(f"{missing_features} files missing features, {missing_thumbs} missing thumbnails")
                    recommendations['estimated_files_to_process'] = max(missing_features, missing_thumbs)
                else:
                    recommendations['reasons'].append("Database appears complete, delta scan recommended")
                    recommendations['estimated_files_to_process'] = 0
        
        except Exception as e:
            self.logger.error(f"Failed to generate rescan recommendations: {e}")
            recommendations['reasons'].append("Failed to analyze database state")
        
        return recommendations


if QT_AVAILABLE:
    class RescanController(QObject):
        """Qt-based rescan controller with progress signals."""
        
        # Progress signals
        progress_updated = Signal(str, int)  # message, progress
        rescan_started = Signal(str)         # mode
        rescan_completed = Signal(dict)      # stats
        rescan_failed = Signal(str)          # error
        
        def __init__(self, db_path: Path, settings):
            super().__init__()
            self.rescan_manager = RescanManager(db_path, settings)
            self.logger = logging.getLogger(__name__)
        
        def start_delta_rescan(self, scan_paths: List[Path]):
            """Start delta rescan with progress signals."""
            try:
                self.rescan_started.emit("delta_only")
                
                def progress_callback(message: str, progress: int):
                    self.progress_updated.emit(message, progress)
                
                stats = self.rescan_manager.perform_delta_rescan(scan_paths, progress_callback)
                self.rescan_completed.emit(stats.__dict__)
                
            except Exception as e:
                self.rescan_failed.emit(str(e))
        
        def start_full_rebuild(self, scan_paths: List[Path], preserve_overrides: bool = True, preserve_groups: bool = True):
            """Start full rebuild with progress signals."""
            try:
                self.rescan_started.emit("full_rebuild")
                
                def progress_callback(message: str, progress: int):
                    self.progress_updated.emit(message, progress)
                
                stats = self.rescan_manager.perform_full_rebuild(
                    scan_paths, preserve_overrides, preserve_groups, progress_callback
                )
                self.rescan_completed.emit(stats.__dict__)
                
            except Exception as e:
                self.rescan_failed.emit(str(e))
else:
    class RescanController:
        """Fallback rescan controller for non-Qt environments."""
        
        def __init__(self, db_path: Path, settings):
            self.rescan_manager = RescanManager(db_path, settings)


def create_rescan_manager(db_path: Path, settings) -> RescanManager:
    """Factory function to create rescan manager."""
    return RescanManager(db_path, settings)


def create_rescan_controller(db_path: Path, settings) -> RescanController:
    """Factory function to create rescan controller."""
    return RescanController(db_path, settings)