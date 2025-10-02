from __future__ import annotations

import json
import tempfile
from pathlib import Path

from store.cache import CacheManager


def create_dummy_files(cache_manager: CacheManager, count: int = 5) -> None:
    """Create some dummy cache files for testing."""
    for i in range(count):
        # Create dummy thumbnail
        thumb_file = cache_manager.thumbs_dir / f"thumb_{i}.jpg"
        thumb_file.write_text(f"dummy thumbnail {i}" * 100)  # ~1.7KB each
        
        # Add to cache database
        cache_manager.add_cache_entry(f"thumb_{i}", thumb_file, "thumbnail")
        
        # Create dummy log
        log_file = cache_manager.logs_dir / f"log_{i}.txt"
        log_file.write_text(f"dummy log {i}" * 50)  # ~0.6KB each
        
        cache_manager.add_cache_entry(f"log_{i}", log_file, "log")


def demo_cache():
    """Demonstrate cache manager functionality."""
    print("=== Cache Manager Demo ===\n")
    
    # Use a temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "demo_cache"
        
        # Create cache manager with small limits for testing
        cache = CacheManager(
            cache_dir=cache_dir,
            size_cap_mb=1,  # 1MB limit for demo
            max_age_days=30,
            soft_expiry_days=21
        )
        
        print(f"Cache directory: {cache.cache_dir}")
        print(f"Thumbs directory: {cache.thumbs_dir}")
        print(f"Logs directory: {cache.logs_dir}")
        print(f"Database path: {cache.db_path}")
        print()
        
        # Show initial stats
        print("Initial cache stats:")
        stats = cache.cache_stats()
        print(json.dumps(stats, indent=2))
        print()
        
        # Create some dummy files
        print("Creating dummy cache files...")
        create_dummy_files(cache, 5)
        print("Created 5 thumbnails and 5 logs")
        print()
        
        # Show stats after adding files
        print("Cache stats after adding files:")
        stats = cache.cache_stats()
        print(json.dumps(stats, indent=2))
        print()
        
        # Test dry-run purge
        print("Testing purge (dry-run):")
        purge_result = cache.purge_if_needed(dry_run=True)
        print(json.dumps(purge_result, indent=2))
        print()
        
        # Test actual purge if needed
        if purge_result["removed_count"] > 0:
            print("Running actual purge:")
            purge_result = cache.purge_if_needed(dry_run=False)
            print(json.dumps(purge_result, indent=2))
            print()
        
        # Test clear cache (dry-run)
        print("Testing clear cache (dry-run):")
        clear_result = cache.clear_cache(dry_run=True)
        print(json.dumps(clear_result, indent=2))
        print()
        
        # Show final stats
        print("Final cache stats:")
        final_stats = cache.cache_stats()
        print(json.dumps(final_stats, indent=2))
        print()
        
        print("Demo completed successfully!")


if __name__ == "__main__":
    demo_cache()