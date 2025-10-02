from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from platformdirs import user_cache_dir
except ImportError:
    user_cache_dir = None


class CacheManager:
    """Cache manager for photo-dedupe.
    
    Manages cache under %LOCALAPPDATA%/<AppName>/cache with:
    - /thumbs/ - thumbnail images
    - /logs/ - log files
    - /db.sqlite - cache metadata database
    
    Implements size cap and age-based eviction with LRU policy.
    """
    
    APP_NAME = "photo-dedupe"
    DB_FILENAME = "db.sqlite"
    
    def __init__(self, 
                 cache_dir: Optional[Path] = None,
                 size_cap_mb: int = 512,
                 max_age_days: int = 30,
                 soft_expiry_days: int = 21):
        
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            if user_cache_dir:
                self.cache_dir = Path(user_cache_dir(self.APP_NAME))
            else:
                # Fallback to LOCALAPPDATA or home-based cache
                base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".cache"))
                self.cache_dir = base / self.APP_NAME
        
        self.size_cap_bytes = size_cap_mb * 1024 * 1024
        self.max_age_days = max_age_days
        self.soft_expiry_days = soft_expiry_days
        
        # Create subdirectories
        self.thumbs_dir = self.cache_dir / "thumbs"
        self.logs_dir = self.cache_dir / "logs"
        self.db_path = self.cache_dir / self.DB_FILENAME
        
        self._ensure_directories()
        self._init_database()
    
    def _ensure_directories(self) -> None:
        """Create cache directories if they don't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.thumbs_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
    
    def _init_database(self) -> None:
        """Initialize the cache metadata database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    entry_type TEXT NOT NULL DEFAULT 'thumbnail'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_accessed 
                ON cache_entries(last_accessed)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON cache_entries(created_at)
            """)
            conn.commit()
    
    def _get_file_size(self, file_path: Path) -> int:
        """Get file size, return 0 if file doesn't exist."""
        try:
            return file_path.stat().st_size
        except (OSError, FileNotFoundError):
            return 0
    
    def _calculate_directory_size(self) -> int:
        """Calculate total size of all cache files."""
        total_size = 0
        for dir_path in [self.thumbs_dir, self.logs_dir]:
            for file_path in dir_path.rglob("*"):
                if file_path.is_file():
                    total_size += self._get_file_size(file_path)
        
        # Add database size
        total_size += self._get_file_size(self.db_path)
        return total_size
    
    def cache_stats(self) -> Dict[str, any]:
        """Return cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Count entries by type
            cursor.execute("""
                SELECT entry_type, COUNT(*), SUM(size_bytes)
                FROM cache_entries 
                GROUP BY entry_type
            """)
            type_stats = {row[0]: {"count": row[1], "size_bytes": row[2] or 0} 
                         for row in cursor.fetchall()}
            
            # Total entries
            cursor.execute("SELECT COUNT(*), SUM(size_bytes) FROM cache_entries")
            total_count, total_db_size = cursor.fetchone()
            total_db_size = total_db_size or 0
            
            # Age statistics
            now = time.time()
            soft_expiry_time = now - (self.soft_expiry_days * 24 * 3600)
            hard_expiry_time = now - (self.max_age_days * 24 * 3600)
            
            cursor.execute("""
                SELECT COUNT(*) FROM cache_entries 
                WHERE created_at < ?
            """, (hard_expiry_time,))
            expired_count = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM cache_entries 
                WHERE created_at < ? AND created_at >= ?
            """, (soft_expiry_time, hard_expiry_time))
            soft_expired_count = cursor.fetchone()[0]
        
        # Calculate actual disk usage
        actual_size = self._calculate_directory_size()
        
        return {
            "cache_dir": str(self.cache_dir),
            "total_entries": total_count,
            "size_cap_mb": self.size_cap_bytes // (1024 * 1024),
            "actual_size_bytes": actual_size,
            "actual_size_mb": actual_size / (1024 * 1024),
            "db_tracked_size_bytes": total_db_size,
            "size_utilization_pct": (actual_size / self.size_cap_bytes) * 100,
            "expired_entries": expired_count,
            "soft_expired_entries": soft_expired_count,
            "max_age_days": self.max_age_days,
            "soft_expiry_days": self.soft_expiry_days,
            "by_type": type_stats,
        }
    
    def _get_lru_candidates(self, limit: int) -> List[Tuple[str, str]]:
        """Get LRU cache entries (key, file_path) up to limit."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT key, file_path FROM cache_entries 
                ORDER BY last_accessed ASC 
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()
    
    def _get_expired_entries(self, expired_before: float) -> List[Tuple[str, str]]:
        """Get entries older than expired_before timestamp."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT key, file_path FROM cache_entries 
                WHERE created_at < ?
            """, (expired_before,))
            return cursor.fetchall()
    
    def _remove_cache_entry(self, key: str, file_path: str, dry_run: bool = False) -> bool:
        """Remove a cache entry and its file."""
        file_path_obj = Path(file_path)
        
        if not dry_run:
            # Remove file if it exists
            try:
                if file_path_obj.exists():
                    file_path_obj.unlink()
            except OSError:
                pass  # Continue even if file removal fails
            
            # Remove from database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                conn.commit()
        
        return True
    
    def purge_if_needed(self, dry_run: bool = False) -> Dict[str, any]:
        """Purge cache if size/age limits exceeded."""
        stats = self.cache_stats()
        
        removed_count = 0
        removed_size = 0
        reasons = []
        
        # 1. Remove hard-expired entries first
        now = time.time()
        hard_expiry_time = now - (self.max_age_days * 24 * 3600)
        expired_entries = self._get_expired_entries(hard_expiry_time)
        
        for key, file_path in expired_entries:
            file_size = self._get_file_size(Path(file_path))
            if self._remove_cache_entry(key, file_path, dry_run):
                removed_count += 1
                removed_size += file_size
        
        if expired_entries:
            reasons.append(f"Removed {len(expired_entries)} hard-expired entries")
        
        # 2. Check if we're still over size limit
        remaining_size = stats["actual_size_bytes"] - removed_size
        if remaining_size > self.size_cap_bytes:
            # Calculate how much we need to remove
            target_removal = remaining_size - (self.size_cap_bytes * 0.8)  # Remove to 80% of cap
            
            # Get LRU candidates
            lru_candidates = self._get_lru_candidates(1000)  # Get up to 1000 candidates
            lru_removed = 0
            
            for key, file_path in lru_candidates:
                if target_removal <= 0:
                    break
                
                file_size = self._get_file_size(Path(file_path))
                if self._remove_cache_entry(key, file_path, dry_run):
                    removed_count += 1
                    removed_size += file_size
                    target_removal -= file_size
                    lru_removed += 1
            
            if lru_removed:
                reasons.append(f"Removed {lru_removed} LRU entries for size limit")
        
        # 3. Check soft expiry (only if we have plenty of space)
        if stats["actual_size_bytes"] < (self.size_cap_bytes * 0.5):
            soft_expiry_time = now - (self.soft_expiry_days * 24 * 3600)
            soft_expired = self._get_expired_entries(soft_expiry_time)
            
            # Only remove some soft-expired entries to keep some cache warmth
            soft_to_remove = soft_expired[:len(soft_expired)//2]  # Remove half
            
            for key, file_path in soft_to_remove:
                file_size = self._get_file_size(Path(file_path))
                if self._remove_cache_entry(key, file_path, dry_run):
                    removed_count += 1
                    removed_size += file_size
            
            if soft_to_remove:
                reasons.append(f"Removed {len(soft_to_remove)} soft-expired entries")
        
        return {
            "dry_run": dry_run,
            "removed_count": removed_count,
            "removed_size_mb": removed_size / (1024 * 1024),
            "reasons": reasons,
            "cache_stats_after": self.cache_stats() if not dry_run else None,
        }
    
    def clear_cache(self, dry_run: bool = False) -> Dict[str, any]:
        """Clear all cache entries."""
        stats_before = self.cache_stats()
        
        if not dry_run:
            # Remove all files
            for dir_path in [self.thumbs_dir, self.logs_dir]:
                for file_path in dir_path.rglob("*"):
                    if file_path.is_file():
                        try:
                            file_path.unlink()
                        except OSError:
                            pass
            
            # Clear database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache_entries")
                conn.commit()
        
        return {
            "dry_run": dry_run,
            "cleared_entries": stats_before["total_entries"],
            "cleared_size_mb": stats_before["actual_size_mb"],
            "cache_stats_after": self.cache_stats() if not dry_run else None,
        }
    
    def add_cache_entry(self, key: str, file_path: Path, entry_type: str = "thumbnail") -> None:
        """Add a cache entry to the database."""
        now = time.time()
        size_bytes = self._get_file_size(file_path)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache_entries 
                (key, file_path, size_bytes, created_at, last_accessed, entry_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (key, str(file_path), size_bytes, now, now, entry_type))
            conn.commit()
    
    def touch_cache_entry(self, key: str) -> None:
        """Update last_accessed time for a cache entry."""
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE cache_entries 
                SET last_accessed = ? 
                WHERE key = ?
            """, (now, key))
            conn.commit()


__all__ = ["CacheManager"]