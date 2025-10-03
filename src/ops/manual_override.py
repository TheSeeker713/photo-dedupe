"""
Manual override system for Step 22 - Conflict handling & manual overrides.

This module provides:
- Database schema for tracking manual overrides
- Override persistence across rescans
- Conflict detection between auto and manual selection
- User preference tracking for future selections
"""

import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from PySide6.QtCore import QObject, Signal
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QObject = object
    Signal = lambda *args, **kwargs: None


class OverrideType(Enum):
    """Types of manual overrides."""
    SINGLE_GROUP = "single_group"  # Override for this group only
    DEFAULT_RULE = "default_rule"  # Make this rule default going forward


class OverrideReason(Enum):
    """Reasons for manual overrides."""
    USER_PREFERENCE = "user_preference"
    QUALITY_BETTER = "quality_better"
    FORMAT_PREFERENCE = "format_preference"
    MANUAL_SELECTION = "manual_selection"
    ALGORITHM_ERROR = "algorithm_error"


@dataclass
class ManualOverride:
    """Represents a manual override of original selection."""
    id: Optional[int]
    group_id: int
    original_file_id: int  # File ID that user wants as original
    auto_original_id: int  # File ID that algorithm selected
    override_type: OverrideType
    reason: OverrideReason
    created_at: float
    notes: Optional[str] = None
    is_active: bool = True


@dataclass
class ConflictInfo:
    """Information about a conflict between auto and manual selection."""
    group_id: int
    auto_original_id: int
    user_preferred_id: int
    confidence_score: float
    reason: str
    suggested_actions: List[str]


class ManualOverrideManager:
    """Manages manual overrides for original selection conflicts."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Initialize override table
        self._ensure_override_table()
    
    def _ensure_override_table(self):
        """Ensure the manual override table exists."""
        try:
            from store.db import DatabaseManager
            db_manager = DatabaseManager(self.db_path)
            
            with db_manager.get_connection() as conn:
                # Create manual_overrides table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS manual_overrides (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        group_id INTEGER NOT NULL,
                        original_file_id INTEGER NOT NULL,
                        auto_original_id INTEGER NOT NULL,
                        override_type TEXT NOT NULL CHECK (override_type IN ('single_group', 'default_rule')),
                        reason TEXT NOT NULL CHECK (reason IN ('user_preference', 'quality_better', 'format_preference', 'manual_selection', 'algorithm_error')),
                        created_at REAL NOT NULL,
                        notes TEXT,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                        FOREIGN KEY (original_file_id) REFERENCES files (id) ON DELETE CASCADE,
                        FOREIGN KEY (auto_original_id) REFERENCES files (id) ON DELETE CASCADE,
                        UNIQUE (group_id, is_active) -- Only one active override per group
                    )
                """)
                
                # Create indexes for performance
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_manual_overrides_group_id 
                    ON manual_overrides (group_id)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_manual_overrides_active 
                    ON manual_overrides (is_active)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_manual_overrides_type 
                    ON manual_overrides (override_type)
                """)
                
                self.logger.info("Manual override table initialized")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize override table: {e}")
            raise
    
    def record_override(self, override: ManualOverride) -> int:
        """Record a manual override in the database."""
        try:
            from store.db import DatabaseManager
            db_manager = DatabaseManager(self.db_path)
            
            with db_manager.get_connection() as conn:
                # Deactivate any existing override for this group
                conn.execute("""
                    UPDATE manual_overrides 
                    SET is_active = 0 
                    WHERE group_id = ? AND is_active = 1
                """, (override.group_id,))
                
                # Insert new override
                cursor = conn.execute("""
                    INSERT INTO manual_overrides 
                    (group_id, original_file_id, auto_original_id, override_type, reason, created_at, notes, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    override.group_id,
                    override.original_file_id,
                    override.auto_original_id,
                    override.override_type.value,
                    override.reason.value,
                    override.created_at,
                    override.notes,
                    override.is_active
                ))
                
                override_id = cursor.lastrowid
                
                # Update the group_members table to reflect the override
                self._update_group_original(conn, override.group_id, override.original_file_id)
                
                self.logger.info(f"Recorded manual override for group {override.group_id}: "
                              f"file {override.original_file_id} now original")
                
                return override_id
                
        except Exception as e:
            self.logger.error(f"Failed to record override: {e}")
            raise
    
    def _update_group_original(self, conn, group_id: int, new_original_id: int):
        """Update group_members table to reflect new original selection."""
        # Set all members of this group to 'duplicate'
        conn.execute("""
            UPDATE group_members 
            SET role = 'duplicate' 
            WHERE group_id = ?
        """, (group_id,))
        
        # Set the new original
        conn.execute("""
            UPDATE group_members 
            SET role = 'original' 
            WHERE group_id = ? AND file_id = ?
        """, (group_id, new_original_id))
    
    def get_override_for_group(self, group_id: int) -> Optional[ManualOverride]:
        """Get active manual override for a group."""
        try:
            from store.db import DatabaseManager
            db_manager = DatabaseManager(self.db_path)
            
            with db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id, group_id, original_file_id, auto_original_id, 
                           override_type, reason, created_at, notes, is_active
                    FROM manual_overrides
                    WHERE group_id = ? AND is_active = 1
                """, (group_id,))
                
                row = cursor.fetchone()
                if row:
                    return ManualOverride(
                        id=row[0],
                        group_id=row[1],
                        original_file_id=row[2],
                        auto_original_id=row[3],
                        override_type=OverrideType(row[4]),
                        reason=OverrideReason(row[5]),
                        created_at=row[6],
                        notes=row[7],
                        is_active=bool(row[8])
                    )
                
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get override for group {group_id}: {e}")
            return None
    
    def get_all_overrides(self, active_only: bool = True) -> List[ManualOverride]:
        """Get all manual overrides."""
        try:
            from store.db import DatabaseManager
            db_manager = DatabaseManager(self.db_path)
            
            overrides = []
            
            with db_manager.get_connection() as conn:
                query = """
                    SELECT id, group_id, original_file_id, auto_original_id, 
                           override_type, reason, created_at, notes, is_active
                    FROM manual_overrides
                """
                
                if active_only:
                    query += " WHERE is_active = 1"
                
                query += " ORDER BY created_at DESC"
                
                cursor = conn.execute(query)
                
                for row in cursor.fetchall():
                    override = ManualOverride(
                        id=row[0],
                        group_id=row[1],
                        original_file_id=row[2],
                        auto_original_id=row[3],
                        override_type=OverrideType(row[4]),
                        reason=OverrideReason(row[5]),
                        created_at=row[6],
                        notes=row[7],
                        is_active=bool(row[8])
                    )
                    overrides.append(override)
                
                return overrides
                
        except Exception as e:
            self.logger.error(f"Failed to get overrides: {e}")
            return []
    
    def remove_override(self, group_id: int) -> bool:
        """Remove manual override for a group (revert to automatic selection)."""
        try:
            from store.db import DatabaseManager
            db_manager = DatabaseManager(self.db_path)
            
            with db_manager.get_connection() as conn:
                # Get the override before removing it
                override = self.get_override_for_group(group_id)
                if not override:
                    return False
                
                # Deactivate the override
                conn.execute("""
                    UPDATE manual_overrides 
                    SET is_active = 0 
                    WHERE group_id = ? AND is_active = 1
                """, (group_id,))
                
                # Revert to automatic original selection
                self._update_group_original(conn, group_id, override.auto_original_id)
                
                self.logger.info(f"Removed manual override for group {group_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to remove override for group {group_id}: {e}")
            return False
    
    def detect_conflicts_after_rescan(self) -> List[ConflictInfo]:
        """Detect conflicts between existing overrides and new automatic selection."""
        conflicts = []
        
        try:
            from store.db import DatabaseManager
            db_manager = DatabaseManager(self.db_path)
            
            # Get all active overrides
            overrides = self.get_all_overrides(active_only=True)
            
            with db_manager.get_connection() as conn:
                for override in overrides:
                    # Check if the original file still exists in the group
                    cursor = conn.execute("""
                        SELECT f.id, f.path, f.status 
                        FROM files f
                        JOIN group_members gm ON f.id = gm.file_id
                        WHERE gm.group_id = ? AND f.id = ?
                    """, (override.group_id, override.original_file_id))
                    
                    original_file = cursor.fetchone()
                    
                    if not original_file or original_file[2] != 'active':
                        # Original file disappeared - conflict!
                        conflicts.append(ConflictInfo(
                            group_id=override.group_id,
                            auto_original_id=override.auto_original_id,
                            user_preferred_id=override.original_file_id,
                            confidence_score=0.0,
                            reason=f"Manual original file disappeared: {original_file[1] if original_file else 'Unknown'}",
                            suggested_actions=[
                                "Remove manual override",
                                "Select new original from remaining files",
                                "Review group composition"
                            ]
                        ))
            
            return conflicts
            
        except Exception as e:
            self.logger.error(f"Failed to detect conflicts: {e}")
            return []
    
    def get_override_stats(self) -> Dict[str, Any]:
        """Get statistics about manual overrides."""
        try:
            from store.db import DatabaseManager
            db_manager = DatabaseManager(self.db_path)
            
            with db_manager.get_connection() as conn:
                # Total overrides
                cursor = conn.execute("SELECT COUNT(*) FROM manual_overrides")
                total_overrides = cursor.fetchone()[0]
                
                # Active overrides
                cursor = conn.execute("SELECT COUNT(*) FROM manual_overrides WHERE is_active = 1")
                active_overrides = cursor.fetchone()[0]
                
                # Overrides by type
                cursor = conn.execute("""
                    SELECT override_type, COUNT(*) 
                    FROM manual_overrides 
                    WHERE is_active = 1 
                    GROUP BY override_type
                """)
                overrides_by_type = dict(cursor.fetchall())
                
                # Overrides by reason
                cursor = conn.execute("""
                    SELECT reason, COUNT(*) 
                    FROM manual_overrides 
                    WHERE is_active = 1 
                    GROUP BY reason
                """)
                overrides_by_reason = dict(cursor.fetchall())
                
                return {
                    "total_overrides": total_overrides,
                    "active_overrides": active_overrides,
                    "overrides_by_type": overrides_by_type,
                    "overrides_by_reason": overrides_by_reason,
                    "override_percentage": (active_overrides / max(1, total_overrides)) * 100
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get override stats: {e}")
            return {}


if QT_AVAILABLE:
    class ConflictHandler(QObject):
        """Handles conflicts between automatic and manual original selection."""
        
        # Signals for conflict resolution
        conflict_detected = Signal(dict)  # ConflictInfo as dict
        override_requested = Signal(int, int, str, str)  # group_id, file_id, reason, notes
        override_applied = Signal(int)  # group_id
        
        def __init__(self, db_path: Path):
            super().__init__()
            self.db_path = db_path
            self.override_manager = ManualOverrideManager(db_path)
            self.logger = logging.getLogger(__name__)
        
        def check_for_conflicts(self, group_id: int, auto_original_id: int, 
                              current_original_id: int) -> Optional[ConflictInfo]:
            """Check if there's a conflict between auto and manual selection."""
            if auto_original_id == current_original_id:
                return None  # No conflict
            
            # Check if there's an existing override
            existing_override = self.override_manager.get_override_for_group(group_id)
            
            if existing_override and existing_override.original_file_id == current_original_id:
                # User had manually selected this original
                conflict = ConflictInfo(
                    group_id=group_id,
                    auto_original_id=auto_original_id,
                    user_preferred_id=current_original_id,
                    confidence_score=0.8,  # High confidence in conflict detection
                    reason="Manual override differs from automatic selection",
                    suggested_actions=[
                        "Keep manual selection",
                        "Use automatic selection",
                        "Review group and select manually"
                    ]
                )
                
                return conflict
            
            return None
        
        def apply_override(self, group_id: int, new_original_id: int, 
                          override_type: OverrideType = OverrideType.SINGLE_GROUP,
                          reason: OverrideReason = OverrideReason.USER_PREFERENCE,
                          notes: str = ""):
            """Apply a manual override."""
            try:
                # Get current automatic original
                from store.db import DatabaseManager
                db_manager = DatabaseManager(self.db_path)
                
                with db_manager.get_connection() as conn:
                    cursor = conn.execute("""
                        SELECT file_id FROM group_members 
                        WHERE group_id = ? AND role = 'original'
                    """, (group_id,))
                    
                    current_original = cursor.fetchone()
                    if not current_original:
                        self.logger.error(f"No original found for group {group_id}")
                        return False
                    
                    auto_original_id = current_original[0]
                
                # Create override record
                override = ManualOverride(
                    id=None,
                    group_id=group_id,
                    original_file_id=new_original_id,
                    auto_original_id=auto_original_id,
                    override_type=override_type,
                    reason=reason,
                    created_at=time.time(),
                    notes=notes
                )
                
                # Record the override
                override_id = self.override_manager.record_override(override)
                
                # Emit signal
                self.override_applied.emit(group_id)
                
                self.logger.info(f"Applied manual override {override_id} for group {group_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to apply override: {e}")
                return False
        
        def get_conflict_summary(self) -> Dict[str, Any]:
            """Get summary of all conflicts and overrides."""
            conflicts = self.override_manager.detect_conflicts_after_rescan()
            stats = self.override_manager.get_override_stats()
            
            return {
                "conflicts": [
                    {
                        "group_id": c.group_id,
                        "auto_original_id": c.auto_original_id,
                        "user_preferred_id": c.user_preferred_id,
                        "confidence_score": c.confidence_score,
                        "reason": c.reason,
                        "suggested_actions": c.suggested_actions
                    }
                    for c in conflicts
                ],
                "stats": stats,
                "total_conflicts": len(conflicts)
            }
else:
    # Fallback for non-Qt environments
    class ConflictHandler:
        def __init__(self, db_path: Path):
            self.db_path = db_path
            self.override_manager = ManualOverrideManager(db_path)
        
        def check_for_conflicts(self, *args, **kwargs):
            return None
        
        def apply_override(self, *args, **kwargs):
            return False


def create_manual_override_manager(db_path: Path) -> ManualOverrideManager:
    """Factory function to create manual override manager."""
    return ManualOverrideManager(db_path)


def create_conflict_handler(db_path: Path) -> ConflictHandler:
    """Factory function to create conflict handler.""" 
    return ConflictHandler(db_path)