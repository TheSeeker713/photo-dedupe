from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from app.settings import Settings
    from store.db import DatabaseManager

# Import local modules for runtime
try:
    from app.settings import Settings
    from store.db import DatabaseManager
except ImportError:
    try:
        from ..app.settings import Settings
        from ..store.db import DatabaseManager
    except ImportError:
        Settings = None
        DatabaseManager = None

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class EscalationCriteria:
    """Criteria for escalating duplicates to safe duplicates."""
    file_size_match: bool = False
    datetime_match: bool = False
    camera_model_match: bool = False
    
    @property
    def all_met(self) -> bool:
        """Check if all required criteria are met."""
        return self.file_size_match and self.datetime_match and self.camera_model_match
    
    def __str__(self) -> str:
        """String representation of criteria status."""
        criteria = []
        if self.file_size_match:
            criteria.append("size_match")
        if self.datetime_match:
            criteria.append("datetime_match")
        if self.camera_model_match:
            criteria.append("camera_match")
        return " + ".join(criteria) if criteria else "no_match"


@dataclass
class EscalationResult:
    """Result of escalation analysis for a duplicate."""
    file_id: int
    original_role: str
    new_role: str
    criteria_met: EscalationCriteria
    details: Dict[str, Any]
    
    @property
    def was_escalated(self) -> bool:
        """Check if the file was escalated to safe duplicate."""
        return self.new_role == 'safe_duplicate'


class SafeDuplicateEscalation:
    """Second-tag escalation engine for identifying safe duplicates."""
    
    # Default configuration values
    DEFAULT_DATETIME_TOLERANCE = 2.0  # seconds
    DEFAULT_ENABLE_CAMERA_CHECK = True
    
    def __init__(self, db_path: Path, settings: 'Settings'):
        """Initialize safe duplicate escalation engine."""
        self.db_path = db_path
        self.settings = settings
        self.db_manager = DatabaseManager(db_path)
        
        # Get escalation settings
        escalation_config = settings._data.get("Escalation", {})
        self.datetime_tolerance = escalation_config.get(
            "datetime_tolerance_seconds", self.DEFAULT_DATETIME_TOLERANCE
        )
        self.enable_camera_check = escalation_config.get(
            "enable_camera_model_check", self.DEFAULT_ENABLE_CAMERA_CHECK
        )
        
        # Statistics
        self.stats = {
            'groups_processed': 0,
            'duplicates_analyzed': 0,
            'safe_duplicates_found': 0,
            'escalations_applied': 0,
            'processing_time': 0.0
        }
        
        logger.info(f"SafeDuplicateEscalation initialized: "
                   f"datetime_tolerance={self.datetime_tolerance}s, "
                   f"camera_check={self.enable_camera_check}")
    
    def get_duplicate_groups(self) -> List[Tuple[int, List[Tuple[int, str]]]]:
        """Get all duplicate groups with their members."""
        logger.info("Loading duplicate groups for escalation analysis...")
        
        with self.db_manager.get_connection() as conn:
            # Get all groups with their members
            cursor = conn.execute("""
                SELECT 
                    g.id as group_id,
                    gm.file_id,
                    gm.role
                FROM groups g
                JOIN group_members gm ON g.id = gm.group_id
                ORDER BY g.id, gm.role DESC, gm.file_id
            """)
            
            # Group by group_id
            groups = {}
            for row in cursor.fetchall():
                group_id, file_id, role = row
                if group_id not in groups:
                    groups[group_id] = []
                groups[group_id].append((file_id, role))
        
        # Convert to list of tuples
        group_list = [(group_id, members) for group_id, members in groups.items()]
        
        logger.info(f"Loaded {len(group_list)} groups for escalation analysis")
        return group_list
    
    def get_file_metadata(self, file_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Get file metadata for escalation analysis."""
        if not file_ids:
            return {}
        
        placeholders = ','.join('?' * len(file_ids))
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(f"""
                SELECT 
                    f.id, f.path, f.size, f.exif_dt, f.camera_model
                FROM files f
                WHERE f.id IN ({placeholders})
            """, file_ids)
            
            metadata = {}
            for row in cursor.fetchall():
                file_id, path, size, exif_dt, camera_model = row
                
                # Parse EXIF datetime
                exif_datetime = None
                if exif_dt:
                    try:
                        exif_datetime = datetime.fromtimestamp(exif_dt)
                    except (ValueError, OSError):
                        exif_datetime = None
                
                metadata[file_id] = {
                    'path': path,
                    'size': size,
                    'exif_datetime': exif_datetime,
                    'camera_model': camera_model
                }
            
            return metadata
    
    def analyze_escalation_criteria(self, original_metadata: Dict[str, Any], 
                                  duplicate_metadata: Dict[str, Any]) -> EscalationCriteria:
        """Analyze if a duplicate meets criteria for escalation to safe duplicate."""
        criteria = EscalationCriteria()
        
        # Criterion 1: File size match
        original_size = original_metadata.get('size', 0)
        duplicate_size = duplicate_metadata.get('size', 0)
        criteria.file_size_match = (original_size == duplicate_size and original_size > 0)
        
        # Criterion 2: DateTimeOriginal match (within tolerance)
        original_dt = original_metadata.get('exif_datetime')
        duplicate_dt = duplicate_metadata.get('exif_datetime')
        
        if original_dt and duplicate_dt:
            time_diff = abs((original_dt - duplicate_dt).total_seconds())
            criteria.datetime_match = time_diff <= self.datetime_tolerance
        elif not original_dt and not duplicate_dt:
            # Both missing EXIF - consider a match if camera check is disabled
            criteria.datetime_match = not self.enable_camera_check
        else:
            criteria.datetime_match = False
        
        # Criterion 3: Camera model match (if enabled)
        if self.enable_camera_check:
            original_camera = original_metadata.get('camera_model')
            duplicate_camera = duplicate_metadata.get('camera_model')
            
            if original_camera and duplicate_camera:
                # Normalize camera model strings for comparison
                original_norm = original_camera.strip().lower()
                duplicate_norm = duplicate_camera.strip().lower()
                criteria.camera_model_match = (original_norm == duplicate_norm)
            elif not original_camera and not duplicate_camera:
                # Both missing camera info - consider a match
                criteria.camera_model_match = True
            else:
                criteria.camera_model_match = False
        else:
            # Camera check disabled - always pass this criterion
            criteria.camera_model_match = True
        
        return criteria
    
    def process_duplicate_group(self, group_id: int, 
                              members: List[Tuple[int, str]]) -> List[EscalationResult]:
        """Process a single duplicate group for safe duplicate escalation."""
        # Find original and duplicates
        original_members = [(fid, role) for fid, role in members if role == 'original']
        duplicate_members = [(fid, role) for fid, role in members if role == 'duplicate']
        
        if not original_members or not duplicate_members:
            logger.debug(f"Group {group_id}: No escalation needed (no original or no duplicates)")
            return []
        
        if len(original_members) > 1:
            logger.warning(f"Group {group_id}: Multiple originals found, using first one")
        
        original_id = original_members[0][0]
        
        # Get metadata for all files
        all_file_ids = [fid for fid, _ in members]
        metadata = self.get_file_metadata(all_file_ids)
        
        if original_id not in metadata:
            logger.error(f"Group {group_id}: Original file {original_id} metadata not found")
            return []
        
        original_metadata = metadata[original_id]
        results = []
        
        # Analyze each duplicate for escalation
        for duplicate_id, current_role in duplicate_members:
            if duplicate_id not in metadata:
                logger.warning(f"Group {group_id}: Duplicate file {duplicate_id} metadata not found")
                continue
            
            duplicate_metadata = metadata[duplicate_id]
            
            # Analyze escalation criteria
            criteria = self.analyze_escalation_criteria(original_metadata, duplicate_metadata)
            
            # Determine new role
            new_role = 'safe_duplicate' if criteria.all_met else current_role
            
            # Create result
            result = EscalationResult(
                file_id=duplicate_id,
                original_role=current_role,
                new_role=new_role,
                criteria_met=criteria,
                details={
                    'group_id': group_id,
                    'original_id': original_id,
                    'original_size': original_metadata.get('size'),
                    'duplicate_size': duplicate_metadata.get('size'),
                    'original_datetime': original_metadata.get('exif_datetime'),
                    'duplicate_datetime': duplicate_metadata.get('exif_datetime'),
                    'original_camera': original_metadata.get('camera_model'),
                    'duplicate_camera': duplicate_metadata.get('camera_model'),
                    'datetime_tolerance': self.datetime_tolerance,
                    'camera_check_enabled': self.enable_camera_check
                }
            )
            
            results.append(result)
            
            # Log escalation details
            if result.was_escalated:
                logger.info(f"Group {group_id}: File {duplicate_id} escalated to safe_duplicate "
                           f"({criteria})")
            else:
                logger.debug(f"Group {group_id}: File {duplicate_id} remains duplicate "
                            f"({criteria})")
        
        return results
    
    def apply_escalations(self, escalation_results: List[EscalationResult]) -> int:
        """Apply escalation results to database."""
        logger.info(f"Applying {len(escalation_results)} escalation results...")
        
        escalations_applied = 0
        
        with self.db_manager.get_connection() as conn:
            for result in escalation_results:
                if result.was_escalated:
                    try:
                        # Update role in group_members table
                        conn.execute("""
                            UPDATE group_members 
                            SET role = ?, notes = ?
                            WHERE file_id = ? AND role = ?
                        """, (
                            result.new_role,
                            f"Escalated: {result.criteria_met}",
                            result.file_id,
                            result.original_role
                        ))
                        
                        escalations_applied += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to apply escalation for file {result.file_id}: {e}")
        
        logger.info(f"Applied {escalations_applied} escalations successfully")
        return escalations_applied
    
    def process_all_groups(self) -> Tuple[List[EscalationResult], Dict[str, Any]]:
        """Process all duplicate groups for safe duplicate escalation."""
        logger.info("Starting safe duplicate escalation processing...")
        start_time = time.time()
        
        # Get all duplicate groups
        groups = self.get_duplicate_groups()
        self.stats['groups_processed'] = len(groups)
        
        # Process each group
        all_results = []
        duplicates_analyzed = 0
        safe_duplicates_found = 0
        
        for group_id, members in groups:
            results = self.process_duplicate_group(group_id, members)
            all_results.extend(results)
            
            # Update statistics
            duplicates_analyzed += len([r for r in results if r.original_role == 'duplicate'])
            safe_duplicates_found += len([r for r in results if r.was_escalated])
        
        # Apply escalations
        escalations_applied = self.apply_escalations(all_results)
        
        # Update statistics
        self.stats['duplicates_analyzed'] = duplicates_analyzed
        self.stats['safe_duplicates_found'] = safe_duplicates_found
        self.stats['escalations_applied'] = escalations_applied
        self.stats['processing_time'] = time.time() - start_time
        
        logger.info(f"Escalation processing completed in {self.stats['processing_time']:.2f}s: "
                   f"{duplicates_analyzed} analyzed, {safe_duplicates_found} escalated")
        
        return all_results, self.stats
    
    def get_escalation_summary(self, results: List[EscalationResult]) -> Dict[str, Any]:
        """Get comprehensive summary of escalation results."""
        if not results:
            return {
                'total_analyzed': 0,
                'safe_duplicates_found': 0,
                'escalation_rate': 0.0,
                'criteria_breakdown': {},
                'groups_affected': 0,
                'configuration': {
                    'datetime_tolerance': self.datetime_tolerance,
                    'camera_check_enabled': self.enable_camera_check
                }
            }
        
        # Basic statistics
        total_analyzed = len(results)
        safe_duplicates_found = len([r for r in results if r.was_escalated])
        escalation_rate = safe_duplicates_found / total_analyzed if total_analyzed > 0 else 0.0
        
        # Criteria breakdown
        criteria_counts = {
            'size_match_only': 0,
            'datetime_match_only': 0,
            'camera_match_only': 0,
            'size_and_datetime': 0,
            'size_and_camera': 0,
            'datetime_and_camera': 0,
            'all_criteria': 0,
            'no_criteria': 0
        }
        
        for result in results:
            criteria = result.criteria_met
            if criteria.all_met:
                criteria_counts['all_criteria'] += 1
            elif criteria.file_size_match and criteria.datetime_match:
                criteria_counts['size_and_datetime'] += 1
            elif criteria.file_size_match and criteria.camera_model_match:
                criteria_counts['size_and_camera'] += 1
            elif criteria.datetime_match and criteria.camera_model_match:
                criteria_counts['datetime_and_camera'] += 1
            elif criteria.file_size_match:
                criteria_counts['size_match_only'] += 1
            elif criteria.datetime_match:
                criteria_counts['datetime_match_only'] += 1
            elif criteria.camera_model_match:
                criteria_counts['camera_match_only'] += 1
            else:
                criteria_counts['no_criteria'] += 1
        
        # Affected groups
        groups_affected = len(set(r.details['group_id'] for r in results if r.was_escalated))
        
        return {
            'total_analyzed': total_analyzed,
            'safe_duplicates_found': safe_duplicates_found,
            'escalation_rate': escalation_rate,
            'criteria_breakdown': criteria_counts,
            'groups_affected': groups_affected,
            'processing_stats': self.stats,
            'configuration': {
                'datetime_tolerance': self.datetime_tolerance,
                'camera_check_enabled': self.enable_camera_check
            }
        }
    
    def get_safe_duplicate_status(self) -> Dict[str, Any]:
        """Get current status of safe duplicates in database."""
        logger.info("Getting safe duplicate status...")
        
        with self.db_manager.get_connection() as conn:
            # Count roles
            cursor = conn.execute("""
                SELECT role, COUNT(*) as count
                FROM group_members
                GROUP BY role
            """)
            role_counts = dict(cursor.fetchall())
            
            # Get groups with safe duplicates
            cursor = conn.execute("""
                SELECT DISTINCT g.id
                FROM groups g
                JOIN group_members gm ON g.id = gm.group_id
                WHERE gm.role = 'safe_duplicate'
            """)
            groups_with_safe_duplicates = len(cursor.fetchall())
            
            # Total groups
            cursor = conn.execute("SELECT COUNT(*) FROM groups")
            total_groups = cursor.fetchone()[0]
        
        return {
            'role_counts': role_counts,
            'groups_with_safe_duplicates': groups_with_safe_duplicates,
            'total_groups': total_groups,
            'safe_duplicate_percentage': (
                role_counts.get('safe_duplicate', 0) / 
                max(1, role_counts.get('duplicate', 0) + role_counts.get('safe_duplicate', 0))
            ) * 100
        }