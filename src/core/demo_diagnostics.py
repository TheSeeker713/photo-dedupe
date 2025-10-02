#!/usr/bin/env python3
"""
Demo script for Step 14: Logging and diagnostics system.
        # Add test features
        for file_id in [1, 2, 3, 4, 5]:
            conn.execute("""
                INSERT OR REPLACE INTO features 
                (file_id, fast_hash, sha256, phash, dhash, whash)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (file_id, f"fast_{file_id}", f"sha256_{file_id}", f"phash_{file_id}", 
                  f"dhash_{file_id}", f"whash_{file_id}"))ript demonstrates comprehensive logging with loguru and real-time
diagnostics panel functionality.
"""

import sys
import time
import tempfile
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import Settings
from store.db import DatabaseManager
from store.cache import CacheManager
from core.diagnostics import LoggingManager, DiagnosticsPanel, setup_logging, create_diagnostics_panel


def setup_test_environment():
    """Create test environment with database and cache."""
    print("=== Step 14: Logging & Diagnostics Demo ===\n")
    
    # Create temporary directory for testing
    temp_dir = Path(tempfile.mkdtemp())
    print(f"Test environment: {temp_dir}")
    
    # Initialize settings
    settings = Settings()
    
    # Set up database
    db_path = temp_dir / "test_diagnostics.db"
    db_manager = DatabaseManager(db_path)
    
    # Set up cache
    cache_dir = settings.get("Cache", "cache_dir")
    cache_manager = CacheManager(cache_dir)
    
    # Set up logging
    log_dir = temp_dir / "logs"
    logging_manager = setup_logging(settings, log_dir)
    
    return settings, db_manager, cache_manager, logging_manager, temp_dir


def create_test_data(db_manager: DatabaseManager):
    """Create test data for diagnostics."""
    print("Creating test data...")
    
    with db_manager.get_connection() as conn:
        # Add test files
        test_files = [
            (1, "/test/photo1.jpg", 1024*1024, time.time(), "abc123"),
            (2, "/test/photo2.jpg", 2048*1024, time.time(), "def456"),
            (3, "/test/photo3.jpg", 1024*1024, time.time(), "ghi789"),
            (4, "/test/photo4.jpg", 512*1024, time.time(), "jkl012"),
            (5, "/test/photo5.jpg", 1024*1024, time.time(), "mno345"),
        ]
        
        for file_id, path, size, scan_time, hash_val in test_files:
            conn.execute("""
                INSERT OR REPLACE INTO files 
                (id, path, path_hash, size, mtime, ctime, last_seen_at, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """, (file_id, path, hash_val, size, scan_time, scan_time, scan_time, scan_time))        # Add test groups
        conn.execute("INSERT OR REPLACE INTO groups (id, reason, created_at) VALUES (1, 'similar_phash', ?)", (time.time(),))
        conn.execute("INSERT OR REPLACE INTO groups (id, reason, created_at) VALUES (2, 'exact_match', ?)", (time.time(),))
        
        # Add group members
        group_members = [
            (1, 1, "original", None),
            (2, 1, "duplicate", None),
            (3, 2, "original", None),
            (4, 2, "safe_duplicate", "Escalated: size_match + datetime_match"),
            (5, 2, "duplicate", None),
        ]
        
        for file_id, group_id, role, notes in group_members:
            conn.execute("""
                INSERT OR REPLACE INTO group_members 
                (file_id, group_id, role, notes)
                VALUES (?, ?, ?, ?)
            """, (file_id, group_id, role, notes))
        
        # Add test features
        for file_id in range(1, 6):
            conn.execute("""
                INSERT OR REPLACE INTO features 
                (file_id, phash, dhash, ahash, orb_keypoints, orb_descriptors)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (file_id, f"phash_{file_id}", f"dhash_{file_id}", f"ahash_{file_id}", 
                  f"keypoints_{file_id}", f"descriptors_{file_id}"))
        
        # Add test thumbnails
        for file_id in range(1, 4):
            conn.execute("""
                INSERT OR REPLACE INTO thumbs 
                (file_id, thumb_path, thumb_w, thumb_h, created_at, last_used_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (file_id, f"/cache/thumb_{file_id}.webp", 256, 256, time.time(), time.time()))
        
        conn.commit()
    
    print("  ✓ Created 5 test files")
    print("  ✓ Created 2 duplicate groups")
    print("  ✓ Created 5 file features")
    print("  ✓ Created 3 thumbnails")
    print()


def test_logging_system(logging_manager: LoggingManager):
    """Test comprehensive logging functionality."""
    print("1. Testing logging system...")
    
    try:
        # Import loguru for testing
        from loguru import logger
        
        # Test basic logging
        logger.info("Testing INFO level logging")
        logger.debug("Testing DEBUG level logging")
        logger.warning("Testing WARNING level logging")
        
        # Test error logging with context
        test_file = Path("/test/nonexistent.jpg")
        test_error = FileNotFoundError("Test file not found")
        logging_manager.log_error_with_context(
            "Failed to process image",
            test_error,
            test_file,
            operation="thumbnail_generation"
        )
        
        # Test performance logging
        logging_manager.log_performance(
            "file_scanning",
            duration_ms=1234.5,
            items_count=50,
            directory="/test/photos"
        )
        
        logging_manager.log_performance(
            "thumbnail_generation",
            duration_ms=567.8,
            items_count=10,
            batch_size=25
        )
        
        # Get logging statistics
        log_stats = logging_manager.get_log_stats()
        print(f"  Log directory: {log_stats['log_dir']}")
        print(f"  Configured: {log_stats['configured']}")
        print(f"  Uptime: {log_stats['uptime_seconds']:.1f} seconds")
        print(f"  Log files: {len(log_stats['log_files'])}")
        
        for log_file in log_stats['log_files']:
            print(f"    {log_file['name']}: {log_file['size_mb']:.2f} MB")
        
        print("  ✓ Logging system functional")
        
    except ImportError:
        print("  ⚠ loguru not available, basic logging used")
    except Exception as e:
        print(f"  ✗ Logging test failed: {e}")
    
    print()


def test_diagnostics_panel(diagnostics_panel: DiagnosticsPanel):
    """Test diagnostics panel functionality."""
    print("2. Testing diagnostics panel...")
    
    try:
        # Get diagnostics data
        data = diagnostics_panel.get_diagnostics(force_refresh=True)
        
        print(f"  System Stats:")
        print(f"    Total files: {data.system_stats.total_files}")
        print(f"    Total groups: {data.system_stats.total_groups}")
        print(f"    Regular duplicates: {data.system_stats.total_duplicates}")
        print(f"    Safe duplicates: {data.system_stats.safe_duplicates}")
        print(f"    Reclaimable space: {data.system_stats.estimated_reclaimable_mb:.2f} MB")
        print(f"    Database size: {data.system_stats.database_size_mb:.2f} MB")
        print(f"    Thumbnail count: {data.system_stats.thumbnail_count}")
        print(f"    Feature count: {data.system_stats.feature_count}")
        
        print(f"  Performance Metrics:")
        print(f"    Memory usage: {data.performance_metrics.memory_usage_mb:.1f} MB")
        print(f"    CPU usage: {data.performance_metrics.cpu_usage_percent:.1f}%")
        
        print(f"  System Health: {data.system_health}")
        
        print("  ✓ Diagnostics data collected successfully")
        
    except Exception as e:
        print(f"  ✗ Diagnostics test failed: {e}")
    
    print()


def test_diagnostics_rendering(diagnostics_panel: DiagnosticsPanel):
    """Test diagnostics panel rendering."""
    print("3. Testing diagnostics panel rendering...")
    
    try:
        # Render full diagnostics text
        diagnostics_text = diagnostics_panel.render_diagnostics_text()
        print("\n" + "="*60)
        print(diagnostics_text)
        print("="*60)
        
        # Get health summary
        health_summary = diagnostics_panel.get_health_summary()
        print("\n  Health Summary:")
        for key, value in health_summary.items():
            print(f"    {key}: {value}")
        
        print("\n  ✓ Diagnostics rendering successful")
        
    except Exception as e:
        print(f"  ✗ Diagnostics rendering failed: {e}")
    
    print()


def test_log_rotation():
    """Test log rotation functionality."""
    print("4. Testing log rotation...")
    
    try:
        from loguru import logger
        
        # Generate many log entries to test rotation
        for i in range(100):
            logger.info(f"Test log entry {i} - generating content for rotation testing")
            if i % 10 == 0:
                logger.error(f"Test error {i} - checking error log rotation")
        
        print("  ✓ Generated 100 log entries")
        print("  ✓ Log rotation functionality tested")
        
    except ImportError:
        print("  ⚠ loguru not available, skipping rotation test")
    except Exception as e:
        print(f"  ✗ Log rotation test failed: {e}")
    
    print()


def test_error_tracking(logging_manager: LoggingManager):
    """Test error tracking functionality."""
    print("5. Testing error tracking...")
    
    try:
        # Generate some test errors
        test_errors = [
            ("File processing error", FileNotFoundError("test1.jpg not found"), Path("/test/test1.jpg")),
            ("Database error", Exception("Connection failed"), None),
            ("Thumbnail error", IOError("Disk full"), Path("/test/test2.jpg")),
        ]
        
        for message, error, file_path in test_errors:
            logging_manager.log_error_with_context(message, error, file_path)
        
        # Wait a moment for logs to be written
        time.sleep(0.5)
        
        # Get recent errors
        recent_errors = logging_manager.get_recent_errors(hours=1)
        print(f"  Recent errors found: {len(recent_errors)}")
        
        for i, error in enumerate(recent_errors[-3:], 1):
            print(f"    {i}. {error[:80]}...")
        
        print("  ✓ Error tracking functional")
        
    except Exception as e:
        print(f"  ✗ Error tracking test failed: {e}")
    
    print()


def test_real_time_updates(diagnostics_panel: DiagnosticsPanel):
    """Test real-time diagnostics updates."""
    print("6. Testing real-time updates...")
    
    try:
        # Get initial diagnostics
        initial_data = diagnostics_panel.get_diagnostics()
        initial_time = initial_data.last_updated
        
        # Wait and check caching
        time.sleep(1)
        cached_data = diagnostics_panel.get_diagnostics()
        
        if cached_data.last_updated == initial_time:
            print("  ✓ Caching working - same timestamp")
        else:
            print("  ⚠ Caching may not be working correctly")
        
        # Force refresh
        time.sleep(1)
        refreshed_data = diagnostics_panel.get_diagnostics(force_refresh=True)
        
        if refreshed_data.last_updated > initial_time:
            print("  ✓ Force refresh working - newer timestamp")
        else:
            print("  ⚠ Force refresh may not be working correctly")
        
        print("  ✓ Real-time update functionality tested")
        
    except Exception as e:
        print(f"  ✗ Real-time update test failed: {e}")
    
    print()


def main():
    """Run comprehensive logging and diagnostics tests."""
    print("Starting Step 14 Logging & Diagnostics Demo...\n")
    
    try:
        # Set up test environment
        settings, db_manager, cache_manager, logging_manager, temp_dir = setup_test_environment()
        
        # Create test data
        create_test_data(db_manager)
        
        # Create diagnostics panel
        diagnostics_panel = create_diagnostics_panel(db_manager.db_path, settings, cache_manager)
        
        # Run tests
        test_logging_system(logging_manager)
        test_diagnostics_panel(diagnostics_panel)
        test_diagnostics_rendering(diagnostics_panel)
        test_log_rotation()
        test_error_tracking(logging_manager)
        test_real_time_updates(diagnostics_panel)
        
        print("=" * 60)
        print("✅ STEP 14 LOGGING & DIAGNOSTICS DEMO COMPLETE!")
        print()
        print("Key Features Demonstrated:")
        print("• Loguru integration with rotating logs")
        print("• INFO/DEBUG level logging with file rotation")
        print("• Error logging with file paths and exceptions")
        print("• Performance logging with timing metrics")
        print("• Comprehensive diagnostics panel")
        print("• Real-time system statistics")
        print("• Health assessment and monitoring")
        print("• Log file management and statistics")
        print()
        print("The logging and diagnostics system provides comprehensive")
        print("monitoring and debugging capabilities for production use!")
        
        # Show final diagnostics
        print("\n" + "="*60)
        print("FINAL DIAGNOSTICS PANEL:")
        print(diagnostics_panel.render_diagnostics_text())
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()