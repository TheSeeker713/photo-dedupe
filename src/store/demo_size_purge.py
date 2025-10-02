from __future__ import annotations

import json
import tempfile
from pathlib import Path

from store.cache import CacheManager


def create_large_dummy_files(cache_manager: CacheManager, count: int = 10) -> None:
    """Create larger dummy cache files to trigger size limits."""
    for i in range(count):
        # Create larger dummy thumbnail (100KB each)
        thumb_file = cache_manager.thumbs_dir / f"large_thumb_{i}.jpg"
        thumb_file.write_text(f"large dummy thumbnail {i}" * 5000)  # ~100KB each
        
        # Add to cache database
        cache_manager.add_cache_entry(f"large_thumb_{i}", thumb_file, "thumbnail")


def demo_size_purge():
    """Demonstrate cache size-based purging."""
    print("=== Cache Size Purge Demo ===\n")
    
    # Use a temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "size_demo_cache"
        
        # Create cache manager with very small limit for testing
        cache = CacheManager(
            cache_dir=cache_dir,
            size_cap_mb=1,  # 1MB limit
            max_age_days=30,
            soft_expiry_days=21
        )
        
        print(f"Cache directory: {cache.cache_dir}")
        print(f"Size cap: {cache.size_cap_bytes / (1024*1024):.1f} MB")
        print()
        
        # Show initial stats
        stats = cache.cache_stats()
        print(f"Initial size: {stats['actual_size_mb']:.3f} MB")
        print()
        
        # Create large files to exceed size limit
        print("Creating large cache files (each ~100KB)...")
        create_large_dummy_files(cache, 15)  # ~1.5MB total
        print("Created 15 large thumbnails")
        print()
        
        # Show stats after adding files
        stats = cache.cache_stats()
        print(f"Size after adding files: {stats['actual_size_mb']:.3f} MB")
        print(f"Size utilization: {stats['size_utilization_pct']:.1f}%")
        print(f"Total entries: {stats['total_entries']}")
        print()
        
        # Test purge (dry-run first)
        print("Testing size-based purge (dry-run):")
        purge_result = cache.purge_if_needed(dry_run=True)
        print(f"Would remove {purge_result['removed_count']} entries")
        print(f"Would save {purge_result['removed_size_mb']:.3f} MB")
        print(f"Reasons: {purge_result['reasons']}")
        print()
        
        # Run actual purge
        print("Running actual purge:")
        purge_result = cache.purge_if_needed(dry_run=False)
        print(f"Removed {purge_result['removed_count']} entries")
        print(f"Saved {purge_result['removed_size_mb']:.3f} MB")
        print(f"Reasons: {purge_result['reasons']}")
        print()
        
        # Show final stats
        final_stats = cache.cache_stats()
        print(f"Final size: {final_stats['actual_size_mb']:.3f} MB")
        print(f"Final utilization: {final_stats['size_utilization_pct']:.1f}%")
        print(f"Final entries: {final_stats['total_entries']}")
        print()
        
        print("Size purge demo completed successfully!")


if __name__ == "__main__":
    demo_size_purge()