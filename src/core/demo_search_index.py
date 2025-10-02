#!/usr/bin/env python3
"""
Demo script for Step 10: Near-duplicate search index using BK-tree.

This script demonstrates the BK-tree implementation for efficient
near-duplicate detection within perceptual hash Hamming distance thresholds.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import Settings
from core.search_index import NearDuplicateSearchIndex, hamming_distance
from store.db import DatabaseManager


def test_hamming_distance():
    """Test Hamming distance calculation."""
    print("=== Testing Hamming Distance ===")
    
    # Test cases
    test_cases = [
        ("0000", "0000", 0),     # Identical
        ("0000", "0001", 1),     # Single bit difference
        ("0000", "1111", 4),     # All bits different
        ("ff00", "00ff", 16),    # Completely different
        ("abcd", "abce", 2),     # Two hex bits different (d=1101, e=1110)
    ]
    
    for hash1, hash2, expected in test_cases:
        distance = hamming_distance(hash1, hash2)
        status = "✓" if distance == expected else "✗"
        print(f"  {status} hamming_distance('{hash1}', '{hash2}') = {distance} (expected {expected})")
    
    print()


def test_search_index_build(search_index):
    """Test building the search index."""
    print("=== Testing Search Index Build ===")
    
    # Check if index is already built
    if search_index.is_index_built():
        print("  ✓ Index already built")
        stats = search_index.get_index_stats()
        print(f"    - Files indexed: {stats['total_files_indexed']}")
        print(f"    - pHash tree size: {stats['phash_tree_size']}")
        print(f"    - dHash tree size: {stats['dhash_tree_size']}")
        print(f"    - wHash tree size: {stats['whash_tree_size']}")
        return True
    
    # Build index
    print("  Building search index...")
    start_time = time.time()
    files_processed = search_index.build_index()
    build_time = time.time() - start_time
    
    if files_processed > 0:
        print(f"  ✓ Index built successfully in {build_time:.2f}s")
        print(f"    - Files processed: {files_processed}")
        
        stats = search_index.get_index_stats()
        print(f"    - pHash tree size: {stats['phash_tree_size']}")
        print(f"    - dHash tree size: {stats['dhash_tree_size']}")
        print(f"    - wHash tree size: {stats['whash_tree_size']}")
        print(f"    - Current preset: {stats['current_preset']}")
        print(f"    - Max distance: {stats['max_distance']}")
        return True
    else:
        print("  ✗ Failed to build index (no files with features found)")
        return False


def test_near_duplicate_search(search_index):
    """Test near-duplicate search functionality."""
    print("=== Testing Near-Duplicate Search ===")
    
    if not search_index.is_index_built():
        print("  ✗ Index not built, skipping search tests")
        return
    
    # Get some file IDs to test with
    try:
        db_manager = DatabaseManager(search_index.db_path)
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT f.id, f.path 
                FROM files f 
                JOIN features feat ON f.id = feat.file_id 
                WHERE feat.phash IS NOT NULL 
                LIMIT 5
            """)
            test_files = cursor.fetchall()
    except Exception as e:
        print(f"  ✗ Failed to get test files: {e}")
        return
    
    if not test_files:
        print("  ✗ No files with features found for testing")
        return
    
    print(f"  Testing with {len(test_files)} files...")
    
    for file_id, file_path in test_files:
        print(f"\n  Testing file ID {file_id}: {Path(file_path).name}")
        
        # Test with different distance thresholds
        for distance in [6, 8, 12]:
            start_time = time.time()
            candidates = search_index.find_near_duplicates(file_id, distance)
            search_time = time.time() - start_time
            
            print(f"    Distance ≤{distance}: {len(candidates)} candidates "
                  f"(searched in {search_time*1000:.1f}ms)")
            
            # Show top 3 candidates
            for i, candidate in enumerate(candidates[:3]):
                min_dist = candidate['min_distance']
                similarity = candidate['similarity_score']
                distances = candidate['distances']
                dist_str = ", ".join(f"{k}:{v}" for k, v in distances.items())
                print(f"      {i+1}. ID {candidate['file_id']}: "
                      f"min_dist={min_dist}, similarity={similarity:.3f} "
                      f"({dist_str})")
        
        break  # Test only first file for demo


def test_similarity_by_hash(search_index):
    """Test finding similarity by specific hash values."""
    print("=== Testing Similarity by Hash ===")
    
    if not search_index.is_index_built():
        print("  ✗ Index not built, skipping hash search tests")
        return
    
    # Get a sample hash to test with
    try:
        db_manager = DatabaseManager(search_index.db_path)
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT phash, dhash, whash 
                FROM features 
                WHERE phash IS NOT NULL 
                LIMIT 1
            """)
            result = cursor.fetchone()
    except Exception as e:
        print(f"  ✗ Failed to get test hash: {e}")
        return
    
    if not result:
        print("  ✗ No hashes found for testing")
        return
    
    phash, dhash, whash = result
    
    # Test searching by pHash
    if phash:
        print(f"  Testing pHash search: {phash}")
        candidates = search_index.find_similar_by_hash(phash, 'phash', 8)
        print(f"    Found {len(candidates)} candidates within distance 8")
        
        for i, candidate in enumerate(candidates[:3]):
            print(f"      {i+1}. ID {candidate['file_id']}: distance={candidate['distance']}")
    
    # Test searching by dHash
    if dhash:
        print(f"  Testing dHash search: {dhash}")
        candidates = search_index.find_similar_by_hash(dhash, 'dhash', 8)
        print(f"    Found {len(candidates)} candidates within distance 8")


def test_preset_distance_thresholds(search_index):
    """Test different preset distance thresholds."""
    print("=== Testing Preset Distance Thresholds ===")
    
    thresholds = search_index.DISTANCE_THRESHOLDS
    current_preset = search_index.current_preset
    
    print(f"  Current preset: {current_preset}")
    print(f"  Current max distance: {search_index.max_distance}")
    print("  All preset thresholds:")
    
    for preset, threshold in thresholds.items():
        status = "← current" if preset == current_preset else ""
        print(f"    {preset}: ≤{threshold} {status}")
    
    print()


def main():
    """Main demo function."""
    print("Photo Dedupe - Step 10: Near-Duplicate Search Index Demo")
    print("=" * 60)
    
    # Initialize components
    try:
        settings = Settings()
        
        # Get database path from DatabaseManager
        from store.db import DatabaseManager
        db_manager = DatabaseManager()
        db_path = db_manager.db_path
        
        if not db_path.exists():
            print(f"✗ Database not found at {db_path}")
            print("  Please run the scanning and features extraction demos first.")
            return
        
        # Initialize search index
        search_index = NearDuplicateSearchIndex(db_path, settings)
        print(f"✓ Search index initialized")
        print(f"  Database: {db_path}")
        print()
        
        # Run tests
        test_hamming_distance()
        test_preset_distance_thresholds(search_index)
        
        # Build and test index
        if test_search_index_build(search_index):
            test_near_duplicate_search(search_index)
            test_similarity_by_hash(search_index)
        
        print("\n=== Demo Summary ===")
        if search_index.is_index_built():
            stats = search_index.get_index_stats()
            print(f"✓ BK-tree search index operational")
            print(f"  - Preset: {stats['current_preset']} (distance ≤{stats['max_distance']})")
            print(f"  - Files indexed: {stats['total_files_indexed']}")
            print(f"  - Trees: pHash={stats['phash_tree_size']}, "
                  f"dHash={stats['dhash_tree_size']}, wHash={stats['whash_tree_size']}")
            print(f"  - Near-duplicate search: ✓ Available")
        else:
            print("✗ Search index not operational")
            print("  - Run scanning and features extraction first")
    
    except Exception as e:
        print(f"✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()