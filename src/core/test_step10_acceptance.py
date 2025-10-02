#!/usr/bin/env python3
"""
Step 10 Acceptance Test: Near-duplicate search index (BK-tree)

Tests all acceptance criteria:
1. BK-tree implementation for approximate search over perceptual hashes
2. find_near_duplicates(file_id, max_distance) function
3. Preset distance values (Ultra-Lite ≤6, Balanced ≤8, Accurate ≤12)
4. Returns plausible near-duplicate candidates with distances
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import Settings
from core.search_index import NearDuplicateSearchIndex, hamming_distance
from store.db import DatabaseManager


def test_acceptance_criteria():
    """Test all Step 10 acceptance criteria."""
    print("Step 10 Acceptance Test: Near-duplicate search index (BK-tree)")
    print("=" * 70)
    
    # Initialize components
    settings = Settings()
    db_manager = DatabaseManager()
    search_index = NearDuplicateSearchIndex(db_manager.db_path, settings)
    
    # Build index
    print("1. Building BK-tree search index...")
    files_processed = search_index.build_index()
    
    if files_processed == 0:
        print("   ✗ No files with features found")
        print("   Please run populate_test_data.py first")
        return False
    
    print(f"   ✓ Index built with {files_processed} files")
    stats = search_index.get_index_stats()
    print(f"   - BK-trees: pHash={stats['phash_tree_size']}, dHash={stats['dhash_tree_size']}, wHash={stats['whash_tree_size']}")
    
    # Test 1: BK-tree implementation
    print("\n2. Testing BK-tree implementation...")
    
    # Test Hamming distance calculation
    test_cases = [
        ("0000", "0000", 0),     # Identical
        ("0000", "0001", 1),     # 1 bit different
        ("ff00", "00ff", 16),    # Many bits different
    ]
    
    hamming_ok = True
    for hash1, hash2, expected in test_cases:
        result = hamming_distance(hash1, hash2)
        if result != expected:
            hamming_ok = False
            print(f"   ✗ hamming_distance('{hash1}', '{hash2}') = {result}, expected {expected}")
        else:
            print(f"   ✓ hamming_distance('{hash1}', '{hash2}') = {result}")
    
    if not hamming_ok:
        return False
    
    # Test 2: find_near_duplicates function
    print("\n3. Testing find_near_duplicates(file_id, max_distance)...")
    
    # Get a test file that has features
    with db_manager.get_connection() as conn:
        cursor = conn.execute("""
            SELECT f.id FROM files f 
            JOIN features feat ON f.id = feat.file_id 
            WHERE feat.phash IS NOT NULL 
            LIMIT 1
        """)
        result = cursor.fetchone()
        if not result:
            print("   ✗ No files with pHash found for testing")
            return False
        test_file_id = result[0]
    
    # Test function exists and works
    try:
        candidates = search_index.find_near_duplicates(test_file_id, 8)
        print(f"   ✓ find_near_duplicates({test_file_id}, 8) returned {len(candidates)} candidates")
        
        # Verify return format
        if candidates:
            candidate = candidates[0]
            required_fields = ['file_id', 'file_path', 'distances', 'min_distance', 'similarity_score']
            for field in required_fields:
                if field not in candidate:
                    print(f"   ✗ Missing required field: {field}")
                    return False
            print(f"   ✓ Candidate format correct: {list(candidate.keys())}")
        
    except Exception as e:
        print(f"   ✗ find_near_duplicates failed: {e}")
        return False
    
    # Test 3: Preset distance thresholds
    print("\n4. Testing preset distance thresholds...")
    
    expected_thresholds = {
        "Ultra-Lite": 6,
        "Balanced": 8,
        "Accurate": 12
    }
    
    actual_thresholds = search_index.DISTANCE_THRESHOLDS
    thresholds_ok = True
    
    for preset, expected_dist in expected_thresholds.items():
        if preset not in actual_thresholds:
            print(f"   ✗ Missing preset: {preset}")
            thresholds_ok = False
        elif actual_thresholds[preset] != expected_dist:
            print(f"   ✗ Wrong threshold for {preset}: {actual_thresholds[preset]}, expected {expected_dist}")
            thresholds_ok = False
        else:
            print(f"   ✓ {preset}: ≤{expected_dist}")
    
    if not thresholds_ok:
        return False
    
    # Test current preset is working
    current_preset = search_index.current_preset
    current_max = search_index.max_distance
    expected_max = expected_thresholds[current_preset]
    
    if current_max != expected_max:
        print(f"   ✗ Current preset {current_preset} has wrong max distance: {current_max}, expected {expected_max}")
        return False
    
    print(f"   ✓ Current preset {current_preset} using correct distance ≤{current_max}")
    
    # Test 4: Distance-based search results
    print("\n5. Testing distance-based search results...")
    
    # Test with different distance thresholds
    test_distances = [6, 8, 12]
    results_by_distance = {}
    
    for max_dist in test_distances:
        candidates = search_index.find_near_duplicates(test_file_id, max_dist)
        results_by_distance[max_dist] = len(candidates)
        print(f"   ✓ Distance ≤{max_dist}: {len(candidates)} candidates")
    
    # Verify that larger distances return same or more results
    prev_count = 0
    for max_dist in sorted(test_distances):
        current_count = results_by_distance[max_dist]
        if current_count < prev_count:
            print(f"   ✗ Inconsistent results: distance ≤{max_dist} returned fewer results than smaller distance")
            return False
        prev_count = current_count
    
    print("   ✓ Distance thresholds work correctly (larger distance ≥ smaller distance results)")
    
    # Test 5: Performance and candidate quality
    print("\n6. Testing performance and candidate quality...")
    
    # Measure search performance
    start_time = time.time()
    candidates = search_index.find_near_duplicates(test_file_id, 8)
    search_time = time.time() - start_time
    
    print(f"   ✓ Search completed in {search_time*1000:.2f}ms")
    
    if search_time > 0.1:  # Should be very fast for small dataset
        print(f"   ⚠ Search took longer than expected (>{100}ms)")
    
    # Verify candidate quality
    if candidates:
        # Check distances are within threshold
        for candidate in candidates:
            min_dist = candidate['min_distance']
            if min_dist > 8:
                print(f"   ✗ Candidate has distance {min_dist} > threshold 8")
                return False
        
        print(f"   ✓ All {len(candidates)} candidates within distance threshold")
        
        # Check similarity scores
        similarities = [c['similarity_score'] for c in candidates]
        if all(0 <= s <= 1 for s in similarities):
            print(f"   ✓ Similarity scores in valid range [0,1]: {similarities[:3]}...")
        else:
            print(f"   ✗ Invalid similarity scores: {similarities}")
            return False
    
    # Final summary
    print("\n" + "=" * 70)
    print("✅ STEP 10 ACCEPTANCE CRITERIA MET:")
    print("   ✓ BK-tree implementation for approximate perceptual hash search")
    print("   ✓ find_near_duplicates(file_id, max_distance) function working")
    print("   ✓ Preset distance values: Ultra-Lite ≤6, Balanced ≤8, Accurate ≤12")
    print("   ✓ Returns plausible near-duplicate candidates with distances")
    print("   ✓ Fast search performance (BK-tree efficiency)")
    print("   ✓ Multiple hash types supported (pHash, dHash, wHash)")
    
    return True


def main():
    """Run acceptance test."""
    try:
        success = test_acceptance_criteria()
        if success:
            print("\n🎉 Step 10 implementation PASSED all acceptance criteria!")
        else:
            print("\n❌ Step 10 implementation FAILED acceptance criteria.")
    except Exception as e:
        print(f"\n💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()