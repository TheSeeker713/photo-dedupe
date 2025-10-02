#!/usr/bin/env python3
"""
Step 14: Logging & Diagnostics Demo
Demonstrates the logging system with loguru and the diagnostics panel.
"""

import tempfile
import time
from pathlib import Path

# Import required modules
from app.settings import Settings
from core.diagnostics import LoggingManager, DiagnosticsPanel, setup_logging
from store.db import DatabaseManager
from store.cache import CacheManager

def setup_test_environment():
    """Set up a temporary test environment."""
    temp_dir = Path(tempfile.mkdtemp())
    print(f"Test environment: {temp_dir}")
    
    # Create settings with temp directory
    settings = Settings(temp_dir / "config")
    
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
    """Create test data for demonstration."""
    print("Creating test data...")
    
    with db_manager.get_connection() as conn:
        # Add test files
        test_files = [
            (1, "/test/photo1.jpg", 1024*1024, time.time(), "abc123"),
            (2, "/test/photo2.jpg", 2048*1024, time.time(), "def456"),
            (3, "/test/photo3.jpg", 800*1024, time.time(), "ghi789"),
            (4, "/test/photo4.jpg", 512*1024, time.time(), "jkl012"),
            (5, "/test/photo5.jpg", 1024*1024, time.time(), "mno345"),
        ]
        
        for file_id, path, size, scan_time, hash_val in test_files:
            conn.execute("""
                INSERT OR REPLACE INTO files 
                (id, path, path_hash, size, mtime, ctime, last_seen_at, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """, (file_id, path, hash_val, size, scan_time, scan_time, scan_time, scan_time))
        
        # Add test groups
        conn.execute("INSERT OR REPLACE INTO groups (id, reason, created_at) VALUES (1, 'similar_phash', ?)", (time.time(),))
        conn.execute("INSERT OR REPLACE INTO groups (id, reason, created_at) VALUES (2, 'exact_match', ?)", (time.time(),))
        
        # Add group members
        group_members = [
            (1, 1, "original", None),
            (2, 1, "duplicate", None),
            (3, 2, "original", None),
            (4, 2, "duplicate", None),
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
                (file_id, fast_hash, sha256, phash, dhash, whash)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (file_id, f"fast_{file_id}", f"sha256_{file_id}", f"phash_{file_id}", 
                  f"dhash_{file_id}", f"whash_{file_id}"))
        
        # Add test thumbnails
        for file_id in range(1, 4):
            conn.execute("""
                INSERT OR REPLACE INTO thumbs 
                (file_id, thumb_path, thumb_w, thumb_h, created_at, last_used_at)
                VALUES (?, ?, 150, 150, ?, ?)
            """, (file_id, f"/cache/thumb_{file_id}.jpg", time.time(), time.time()))

def test_logging_functionality(logging_manager: LoggingManager):
    """Test various logging features."""
    print("\\n=== Testing Logging Functionality ===")
    
    # Import loguru logger directly
    try:
        from loguru import logger
    except ImportError:
        print("Loguru not available, skipping logging tests")
        return
    
    # Test different log levels
    logger.info("This is an info message")
    logger.debug("This is a debug message")
    logger.warning("This is a warning message")
    
    # Test error logging with context
    try:
        raise ValueError("Test error for logging demonstration")
    except Exception as e:
        logger.bind(file_path="/test/photo1.jpg", operation="hash_calculation").error(f"Caught error: {e}")
    
    # Test performance logging
    start_time = time.time()
    time.sleep(0.1)  # Simulate some work
    duration = time.time() - start_time
    logger.bind(performance=True, duration=duration, operation="test_operation").info(f"Operation completed in {duration:.3f}s")
    
    print("Logging tests completed")

def test_diagnostics_panel(db_manager: DatabaseManager, cache_manager: CacheManager, temp_dir: Path):
    """Test the diagnostics panel functionality."""
    print("\\n=== Testing Diagnostics Panel ===")
    
    # Create diagnostics panel
    diagnostics = DiagnosticsPanel(db_manager.db_path, cache_manager, temp_dir / "logs")
    
    # Generate and display diagnostics
    diagnostics_data = diagnostics.get_diagnostics()
    
    print("\\nSystem Statistics:")
    print(f"  Total Files: {diagnostics_data.system_stats.total_files}")
    print(f"  Total Groups: {diagnostics_data.system_stats.total_groups}")
    print(f"  Total Duplicates: {diagnostics_data.system_stats.total_duplicates}")
    print(f"  Safe Duplicates: {diagnostics_data.system_stats.safe_duplicates}")
    print(f"  Estimated Reclaimable Space: {diagnostics_data.system_stats.estimated_reclaimable_mb} MB")
    print(f"  Cache Size: {diagnostics_data.system_stats.cache_size_mb} MB")
    print(f"  Last Cache Purge: {diagnostics_data.system_stats.last_purge_time}")
    print(f"  Database Size: {diagnostics_data.system_stats.database_size_mb} MB")
    print(f"  Thumbnail Count: {diagnostics_data.system_stats.thumbnail_count}")
    print(f"  Feature Count: {diagnostics_data.system_stats.feature_count}")
    
    # Test performance metrics
    print(f"\\nPerformance Metrics:")
    print(f"  Files/sec (scan): {diagnostics_data.performance_metrics.files_per_second_scan}")
    print(f"  Thumbnails/sec: {diagnostics_data.performance_metrics.thumbnails_per_second}")
    print(f"  Hashes/sec: {diagnostics_data.performance_metrics.hashes_per_second}")
    print(f"  Memory Usage: {diagnostics_data.performance_metrics.memory_usage_mb:.1f} MB")
    print(f"  CPU Usage: {diagnostics_data.performance_metrics.cpu_usage_percent}%")
    print(f"  Disk I/O: {diagnostics_data.performance_metrics.disk_io_mb_per_second} MB/sec")
    print(f"  Active Threads: {diagnostics_data.performance_metrics.active_threads}")
    print(f"  Queue Depth: {diagnostics_data.performance_metrics.queue_depth}")
    
    # Test health assessment
    health = diagnostics.get_health_summary()
    print(f"\\nHealth Assessment:")
    print(f"  Overall Status: {health.get('status', 'unknown')}")
    print(f"  Issues: {len(health.get('issues', []))}")
    for issue in health.get('issues', []):
        print(f"    - {issue.get('type', 'unknown')}: {issue.get('message', 'no message')}")
    
    # Render full diagnostics
    print("\\n=== Full Diagnostics Panel ===")
    full_diagnostics = diagnostics.render_diagnostics_text()
    print(full_diagnostics)

def demonstrate_log_rotation(logging_manager: LoggingManager):
    """Demonstrate log rotation by generating many log entries."""
    print("\\n=== Testing Log Rotation ===")
    
    # Import loguru logger directly
    try:
        from loguru import logger
    except ImportError:
        print("Loguru not available, skipping log rotation tests")
        return
    
    # Generate many log entries to trigger rotation
    for i in range(100):
        logger.info(f"Log rotation test message {i+1}: " + "x" * 200)  # Make messages large
        if i % 10 == 0:
            logger.warning(f"Warning message {i+1}")
        if i % 25 == 0:
            logger.bind(file_path=f"/test/photo{i}.jpg").error(f"Error message {i+1}")
    
    print("Log rotation test completed")

def main():
    """Main demonstration function."""
    print("Starting Step 14 Logging & Diagnostics Demo...")
    print("\\n=== Step 14: Logging & Diagnostics Demo ===")
    
    try:
        # Set up test environment
        settings, db_manager, cache_manager, logging_manager, temp_dir = setup_test_environment()
        
        # Create test data
        create_test_data(db_manager)
        
        # Test logging functionality
        test_logging_functionality(logging_manager)
        
        # Test diagnostics panel
        test_diagnostics_panel(db_manager, cache_manager, temp_dir)
        
        # Demonstrate log rotation
        demonstrate_log_rotation(logging_manager)
        
        print("\\n=== Demo Completed Successfully ===")
        print(f"Log files available in: {temp_dir / 'logs'}")
        print(f"Database file: {temp_dir / 'test_diagnostics.db'}")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()