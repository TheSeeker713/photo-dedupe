from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from platformdirs import user_data_dir
except ImportError:
    user_data_dir = None


class DatabaseManager:
    """SQLite database manager for photo-dedupe.
    
    Manages the main database with tables for files, features, groups, and thumbnails.
    Uses WAL mode for better concurrent access and includes migration support.
    """
    
    APP_NAME = "photo-dedupe"
    DB_FILENAME = "photo_dedupe.db"
    CURRENT_SCHEMA_VERSION = 1
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            if user_data_dir:
                data_dir = Path(user_data_dir(self.APP_NAME))
            else:
                # Fallback to LOCALAPPDATA or home-based data dir
                import os
                base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share"))
                data_dir = base / self.APP_NAME
            
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = data_dir / self.DB_FILENAME
        
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database with pragmatic settings and create tables."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode = WAL")
            
            # Performance optimizations
            conn.execute("PRAGMA synchronous = NORMAL")  # Balance safety vs performance
            conn.execute("PRAGMA cache_size = -64000")   # 64MB cache
            conn.execute("PRAGMA temp_store = MEMORY")   # Use memory for temp tables
            conn.execute("PRAGMA mmap_size = 268435456") # 256MB memory map
            conn.execute("PRAGMA foreign_keys = ON")     # Enable foreign key constraints
            
            # Check/create schema version table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at REAL NOT NULL
                )
            """)
            
            # Get current schema version
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            current_version = row[0] if row else 0
            
            # Apply migrations if needed
            if current_version < self.CURRENT_SCHEMA_VERSION:
                self._apply_migrations(conn, current_version)
            
            conn.commit()
    
    def _apply_migrations(self, conn: sqlite3.Connection, from_version: int) -> None:
        """Apply database migrations from current version to latest."""
        migrations = {
            1: self._create_initial_schema,
        }
        
        for version in range(from_version + 1, self.CURRENT_SCHEMA_VERSION + 1):
            if version in migrations:
                print(f"Applying database migration to version {version}")
                migrations[version](conn)
                
                # Record migration
                conn.execute("""
                    INSERT INTO schema_version (version, applied_at) 
                    VALUES (?, ?)
                """, (version, time.time()))
    
    def _create_initial_schema(self, conn: sqlite3.Connection) -> None:
        """Create initial database schema (version 1)."""
        
        # Files table - core file metadata
        conn.execute("""
            CREATE TABLE files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                path_hash TEXT NOT NULL,
                size INTEGER NOT NULL,
                mtime REAL NOT NULL,
                ctime REAL NOT NULL,
                dims_w INTEGER,
                dims_h INTEGER,
                exif_dt REAL,
                camera_model TEXT,
                format TEXT,
                orientation INTEGER DEFAULT 1,
                last_seen_at REAL NOT NULL,
                created_at REAL NOT NULL,
                status TEXT DEFAULT 'active' CHECK (status IN ('active', 'deleted', 'missing'))
            )
        """)
        
        # Features table - hashes and signatures
        conn.execute("""
            CREATE TABLE features (
                file_id INTEGER PRIMARY KEY,
                fast_hash TEXT,
                sha256 TEXT,
                phash TEXT,
                dhash TEXT,
                whash TEXT,
                orb_sig BLOB,
                feature_ver INTEGER DEFAULT 1,
                FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
            )
        """)
        
        # Groups table - duplicate groups
        conn.execute("""
            CREATE TABLE groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reason TEXT NOT NULL,
                score_summary TEXT,
                created_at REAL NOT NULL
            )
        """)
        
        # Group members - files in duplicate groups
        conn.execute("""
            CREATE TABLE group_members (
                group_id INTEGER NOT NULL,
                file_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'duplicate' 
                    CHECK (role IN ('original', 'duplicate', 'safe_duplicate')),
                similarity_score REAL,
                notes TEXT,
                PRIMARY KEY (group_id, file_id),
                FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
            )
        """)
        
        # Thumbnails table - thumbnail cache metadata
        conn.execute("""
            CREATE TABLE thumbs (
                file_id INTEGER PRIMARY KEY,
                thumb_path TEXT NOT NULL,
                thumb_w INTEGER NOT NULL,
                thumb_h INTEGER NOT NULL,
                created_at REAL NOT NULL,
                last_used_at REAL NOT NULL,
                FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for performance
        self._create_indexes(conn)
    
    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """Create database indexes for performance."""
        indexes = [
            # Files table indexes
            "CREATE INDEX IF NOT EXISTS idx_files_path_hash ON files (path_hash)",
            "CREATE INDEX IF NOT EXISTS idx_files_size ON files (size)",
            "CREATE INDEX IF NOT EXISTS idx_files_mtime ON files (mtime)",
            "CREATE INDEX IF NOT EXISTS idx_files_status ON files (status)",
            "CREATE INDEX IF NOT EXISTS idx_files_last_seen ON files (last_seen_at)",
            
            # Features table indexes
            "CREATE INDEX IF NOT EXISTS idx_features_fast_hash ON features (fast_hash)",
            "CREATE INDEX IF NOT EXISTS idx_features_sha256 ON features (sha256)",
            "CREATE INDEX IF NOT EXISTS idx_features_phash ON features (phash)",
            "CREATE INDEX IF NOT EXISTS idx_features_dhash ON features (dhash)",
            "CREATE INDEX IF NOT EXISTS idx_features_whash ON features (whash)",
            
            # Groups table indexes
            "CREATE INDEX IF NOT EXISTS idx_groups_created_at ON groups (created_at)",
            "CREATE INDEX IF NOT EXISTS idx_groups_reason ON groups (reason)",
            
            # Group members indexes
            "CREATE INDEX IF NOT EXISTS idx_group_members_file_id ON group_members (file_id)",
            "CREATE INDEX IF NOT EXISTS idx_group_members_role ON group_members (role)",
            "CREATE INDEX IF NOT EXISTS idx_group_members_similarity ON group_members (similarity_score)",
            
            # Thumbs table indexes
            "CREATE INDEX IF NOT EXISTS idx_thumbs_last_used ON thumbs (last_used_at)",
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    def add_file(self, file_path: Path, size: int, mtime: float, ctime: float,
                 dims_w: Optional[int] = None, dims_h: Optional[int] = None,
                 exif_dt: Optional[float] = None, camera_model: Optional[str] = None,
                 format: Optional[str] = None, orientation: int = 1) -> int:
        """Add a new file record and return the file ID."""
        path_str = str(file_path)
        path_hash = hashlib.blake2b(path_str.encode('utf-8'), digest_size=16).hexdigest()
        now = time.time()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO files 
                (path, path_hash, size, mtime, ctime, dims_w, dims_h, exif_dt, 
                 camera_model, format, orientation, last_seen_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (path_str, path_hash, size, mtime, ctime, dims_w, dims_h, 
                  exif_dt, camera_model, format, orientation, now, now))
            
            return cursor.lastrowid
    
    def find_file_by_path(self, file_path: Path) -> Optional[sqlite3.Row]:
        """Find a file record by path."""
        path_str = str(file_path)
        path_hash = hashlib.blake2b(path_str.encode('utf-8'), digest_size=16).hexdigest()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM files 
                WHERE path_hash = ? AND path = ?
            """, (path_hash, path_str))
            return cursor.fetchone()
    
    def update_file_features(self, file_id: int, fast_hash: Optional[str] = None,
                           sha256: Optional[str] = None, phash: Optional[str] = None,
                           dhash: Optional[str] = None, whash: Optional[str] = None,
                           orb_sig: Optional[bytes] = None, feature_ver: int = 1) -> None:
        """Add or update features for a file."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO features 
                (file_id, fast_hash, sha256, phash, dhash, whash, orb_sig, feature_ver)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (file_id, fast_hash, sha256, phash, dhash, whash, orb_sig, feature_ver))
    
    def find_similar_files(self, fast_hash: Optional[str] = None,
                          sha256: Optional[str] = None, size: Optional[int] = None) -> List[sqlite3.Row]:
        """Find files with similar features."""
        conditions = []
        params = []
        
        if fast_hash:
            conditions.append("f.fast_hash = ?")
            params.append(fast_hash)
        
        if sha256:
            conditions.append("f.sha256 = ?")
            params.append(sha256)
        
        if size:
            conditions.append("files.size = ?")
            params.append(size)
        
        if not conditions:
            return []
        
        where_clause = " AND ".join(conditions)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT files.*, f.fast_hash, f.sha256, f.phash, f.dhash, f.whash
                FROM files 
                LEFT JOIN features f ON files.id = f.file_id
                WHERE {where_clause} AND files.status = 'active'
                ORDER BY files.mtime DESC
            """, params)
            return cursor.fetchall()
    
    def create_duplicate_group(self, reason: str, score_summary: Optional[str] = None) -> int:
        """Create a new duplicate group and return its ID."""
        now = time.time()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO groups (reason, score_summary, created_at)
                VALUES (?, ?, ?)
            """, (reason, score_summary, now))
            return cursor.lastrowid
    
    def add_to_group(self, group_id: int, file_id: int, role: str = 'duplicate',
                     similarity_score: Optional[float] = None, notes: Optional[str] = None) -> None:
        """Add a file to a duplicate group."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO group_members 
                (group_id, file_id, role, similarity_score, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (group_id, file_id, role, similarity_score, notes))
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Count records in each table
            stats = {}
            tables = ['files', 'features', 'groups', 'group_members', 'thumbs']
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()[0]
            
            # Database size
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            stats['db_size_bytes'] = page_size * page_count
            stats['db_size_mb'] = stats['db_size_bytes'] / (1024 * 1024)
            
            # Schema version
            cursor.execute("SELECT MAX(version) FROM schema_version")
            stats['schema_version'] = cursor.fetchone()[0] or 0
            
            return stats
    
    def vacuum_database(self) -> None:
        """Vacuum the database to reclaim space."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("VACUUM")
    
    def analyze_database(self) -> None:
        """Update database statistics for query optimization."""
        with self.get_connection() as conn:
            conn.execute("ANALYZE")


__all__ = ["DatabaseManager"]