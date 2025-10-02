#!/usr/bin/env python3
"""
Simple test for BK-tree implementation with synthetic data.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.search_index import BKTree, hamming_distance


def test_bk_tree_basic():
    """Test basic BK-tree functionality with known data."""
    print("=== BK-Tree Basic Test ===")
    
    # Create test data (hex hashes and distances)
    test_data = [
        ("ff00ff00", 1),  # Base hash
        ("ff00ff01", 2),  # 1 bit difference
        ("ff00ff03", 3),  # 2 bit differences  
        ("ff00fe00", 4),  # Different pattern
        ("00ff00ff", 5),  # Inverse pattern
    ]
    
    # Build tree
    tree = BKTree()
    
    print("Building tree with test data:")
    for hash_val, file_id in test_data:
        tree.add(hash_val, file_id)
        print(f"  Added: {hash_val} -> file {file_id}")
    
    print(f"\nTree size: {tree.size}")
    
    # Test searches
    target_hash = "ff00ff00"  # Exact match for file 1
    print(f"\nSearching for hashes similar to: {target_hash}")
    
    for max_dist in [0, 1, 2, 4, 8]:
        results = tree.search(target_hash, max_dist)
        print(f"  Distance ≤{max_dist}: {len(results)} results")
        for file_id, distance in sorted(results):
            print(f"    File {file_id}: distance {distance}")
    
    print()


def test_hamming_distance_comprehensive():
    """Test Hamming distance with various inputs."""
    print("=== Hamming Distance Comprehensive Test ===")
    
    test_cases = [
        # Basic cases
        ("0000", "0000", 0),
        ("0001", "0000", 1),
        ("0003", "0001", 1),  # 0011 vs 0001 = 1 bit
        ("000f", "0000", 4),  # 1111 vs 0000 = 4 bits
        
        # Realistic perceptual hash cases
        ("ff00ff00ff00ff00", "ff00ff00ff00ff01", 1),
        ("abcdef123456789a", "abcdef123456789b", 1),
        ("0000000000000000", "ffffffffffffffff", 64),
        
        # Edge cases
        ("", "", float('inf')),      # Empty strings
        ("ff", "ffff", float('inf')), # Different lengths
        ("xyz", "abc", float('inf')), # Invalid hex
    ]
    
    for hash1, hash2, expected in test_cases:
        result = hamming_distance(hash1, hash2)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{hash1}' vs '{hash2}' = {result} (expected {expected})")
    
    print()


def test_search_performance():
    """Test search performance with larger dataset."""
    print("=== Search Performance Test ===")
    
    import random
    import time
    
    # Generate synthetic hash data
    def generate_random_hash():
        return ''.join(f'{random.randint(0, 255):02x}' for _ in range(8))
    
    # Create tree with many hashes
    tree = BKTree()
    num_hashes = 1000
    
    print(f"Generating {num_hashes} random hashes...")
    hashes = []
    for i in range(num_hashes):
        hash_val = generate_random_hash()
        tree.add(hash_val, i)
        hashes.append(hash_val)
    
    print(f"Tree size: {tree.size}")
    
    # Test search performance
    target_hash = hashes[0]  # Use first hash as target
    print(f"\nSearching for: {target_hash}")
    
    for max_dist in [4, 8, 12, 16]:
        start_time = time.time()
        results = tree.search(target_hash, max_dist)
        search_time = time.time() - start_time
        
        print(f"  Distance ≤{max_dist}: {len(results)} results in {search_time*1000:.2f}ms")
    
    print()


def main():
    """Run all BK-tree tests."""
    print("BK-Tree Implementation Test")
    print("=" * 40)
    
    test_hamming_distance_comprehensive()
    test_bk_tree_basic()
    test_search_performance()
    
    print("✓ All BK-tree tests completed")


if __name__ == "__main__":
    main()