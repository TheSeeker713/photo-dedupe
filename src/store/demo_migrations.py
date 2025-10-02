from __future__ import annotations

import tempfile
from pathlib import Path
import sqlite3

from store.db import DatabaseManager


def demo_migrations():
    """Demonstrate database migration functionality."""
    print("=== Database Migration Demo ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "migration_demo.db"
        
        # First, create an empty database file to simulate an old version
        print("Creating empty database (simulating version 0)...")
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at REAL NOT NULL
                )
            """)
            # Don't insert any version - this simulates version 0
        print("Empty database created")
        print()
        
        # Now initialize with DatabaseManager - should trigger migration
        print("Initializing DatabaseManager (should trigger migration to version 1)...")
        db = DatabaseManager(db_path=db_path)
        print("Migration completed")
        print()
        
        # Check that all tables exist
        print("Checking that all tables were created:")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  Table '{table}': {count} rows")
        print()
        
        # Check schema version
        stats = db.get_database_stats()
        print(f"Current schema version: {stats['schema_version']}")
        print()
        
        # Check that indexes were created
        print("Checking indexes:")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            indexes = [row[0] for row in cursor.fetchall()]
            print(f"Created {len(indexes)} indexes:")
            for idx in indexes[:5]:  # Show first 5
                print(f"  {idx}")
            if len(indexes) > 5:
                print(f"  ... and {len(indexes) - 5} more")
        print()
        
        # Test that we can re-initialize without issues (should be no-op)
        print("Re-initializing DatabaseManager (should be no-op)...")
        db2 = DatabaseManager(db_path=db_path)
        stats2 = db2.get_database_stats()
        print(f"Schema version after re-init: {stats2['schema_version']}")
        print("No additional migrations applied (as expected)")
        print()
        
        print("Migration demo completed successfully!")


if __name__ == "__main__":
    demo_migrations()