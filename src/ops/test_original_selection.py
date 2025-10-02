#!/usr/bin/env python3
"""
Test deterministic original selection rules in detail.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ops.grouping import FileRecord, FileFormat, GroupingEngine
from app.settings import Settings
from store.db import DatabaseManager


def test_original_selection_rules():
    """Test the deterministic original selection rules with specific scenarios."""
    print("Testing Deterministic Original Selection Rules")
    print("=" * 50)
    
    # Initialize engine for access to selection logic
    settings = Settings()
    db_manager = DatabaseManager()
    engine = GroupingEngine(db_manager.db_path, settings)
    
    # Test Scenario 1: Resolution priority
    print("\n1. Testing resolution priority (highest resolution wins)...")
    
    files_res = [
        FileRecord(1, "/test/low_res.jpg", 1000, 1.0, 100, 100, None, "jpeg"),    # 10,000 pixels
        FileRecord(2, "/test/high_res.jpg", 1200, 1.0, 200, 150, None, "jpeg"),  # 30,000 pixels
        FileRecord(3, "/test/med_res.jpg", 1100, 1.0, 150, 100, None, "jpeg"),   # 15,000 pixels
    ]
    
    original_id, duplicate_ids = engine._select_original(files_res)
    expected_original = 2  # Highest resolution (200x150 = 30,000 pixels)
    
    if original_id == expected_original:
        print(f"   ✓ Highest resolution selected: ID {original_id} (200x150)")
    else:
        print(f"   ✗ Wrong selection: ID {original_id}, expected {expected_original}")
    
    # Test Scenario 2: EXIF datetime priority (when resolution is same)
    print("\n2. Testing EXIF datetime priority (earliest wins when resolution equal)...")
    
    early_time = datetime(2024, 1, 1, 10, 0, 0).timestamp()
    late_time = datetime(2024, 1, 2, 10, 0, 0).timestamp()
    
    files_time = [
        FileRecord(1, "/test/late.jpg", 1000, 1.0, 100, 100, late_time, "jpeg"),   # Later time
        FileRecord(2, "/test/early.jpg", 1000, 1.0, 100, 100, early_time, "jpeg"), # Earlier time
        FileRecord(3, "/test/no_exif.jpg", 1000, 1.0, 100, 100, None, "jpeg"),     # No EXIF
    ]
    
    original_id, duplicate_ids = engine._select_original(files_time)
    expected_original = 2  # Earliest EXIF time
    
    if original_id == expected_original:
        print(f"   ✓ Earliest EXIF time selected: ID {original_id}")
    else:
        print(f"   ✗ Wrong selection: ID {original_id}, expected {expected_original}")
    
    # Test Scenario 3: File size priority (when resolution and EXIF are same)
    print("\n3. Testing file size priority (largest wins when resolution/EXIF equal)...")
    
    files_size = [
        FileRecord(1, "/test/small.jpg", 500, 1.0, 100, 100, early_time, "jpeg"),  # Smaller file
        FileRecord(2, "/test/large.jpg", 1500, 1.0, 100, 100, early_time, "jpeg"), # Larger file
        FileRecord(3, "/test/medium.jpg", 1000, 1.0, 100, 100, early_time, "jpeg"), # Medium file
    ]
    
    original_id, duplicate_ids = engine._select_original(files_size)
    expected_original = 2  # Largest file size
    
    if original_id == expected_original:
        print(f"   ✓ Largest file size selected: ID {original_id} (1500 bytes)")
    else:
        print(f"   ✗ Wrong selection: ID {original_id}, expected {expected_original}")
    
    # Test Scenario 4: Format priority (when everything else is equal)
    print("\n4. Testing format priority (RAW > TIFF > PNG > JPEG > WEBP)...")
    
    files_format = [
        FileRecord(1, "/test/image.jpg", 1000, 1.0, 100, 100, early_time, "jpeg"),  # JPEG (priority 4)
        FileRecord(2, "/test/image.png", 1000, 1.0, 100, 100, early_time, "png"),   # PNG (priority 3)
        FileRecord(3, "/test/image.cr2", 1000, 1.0, 100, 100, early_time, "cr2"),   # RAW (priority 1)
        FileRecord(4, "/test/image.tiff", 1000, 1.0, 100, 100, early_time, "tiff"), # TIFF (priority 2)
        FileRecord(5, "/test/image.webp", 1000, 1.0, 100, 100, early_time, "webp"), # WEBP (priority 5)
    ]
    
    original_id, duplicate_ids = engine._select_original(files_format)
    expected_original = 3  # RAW format (highest priority)
    
    if original_id == expected_original:
        print(f"   ✓ Best format selected: ID {original_id} (RAW format)")
    else:
        print(f"   ✗ Wrong selection: ID {original_id}, expected {expected_original}")
        # Debug format priorities
        for f in files_format:
            print(f"     ID {f.id}: {f.file_format.format_name} (priority {f.file_format.priority})")
    
    # Test Scenario 5: Path as tie-breaker (when everything is identical)
    print("\n5. Testing path tie-breaker (alphabetical when all else equal)...")
    
    files_path = [
        FileRecord(1, "/test/zebra.jpg", 1000, 1.0, 100, 100, early_time, "jpeg"),
        FileRecord(2, "/test/alpha.jpg", 1000, 1.0, 100, 100, early_time, "jpeg"),
        FileRecord(3, "/test/beta.jpg", 1000, 1.0, 100, 100, early_time, "jpeg"),
    ]
    
    original_id, duplicate_ids = engine._select_original(files_path)
    expected_original = 2  # Alphabetically first path
    
    if original_id == expected_original:
        print(f"   ✓ Alphabetically first path selected: ID {original_id}")
    else:
        print(f"   ✗ Wrong selection: ID {original_id}, expected {expected_original}")
    
    # Test Scenario 6: Complex mixed scenario
    print("\n6. Testing complex mixed scenario...")
    
    files_mixed = [
        # ID 1: Low res, JPEG, large file - should lose on resolution
        FileRecord(1, "/test/low_res_large.jpg", 5000, 1.0, 100, 100, early_time, "jpeg"),
        
        # ID 2: High res, JPEG, small file, late time - should lose on time
        FileRecord(2, "/test/high_res_late.jpg", 1000, 1.0, 300, 200, late_time, "jpeg"),
        
        # ID 3: High res, JPEG, small file, early time - should WIN (best combination)
        FileRecord(3, "/test/high_res_early.jpg", 1000, 1.0, 300, 200, early_time, "jpeg"),
        
        # ID 4: High res, PNG, small file, early time - should lose on format (JPEG vs PNG minimal diff)
        FileRecord(4, "/test/high_res_png.png", 1000, 1.0, 300, 200, early_time, "png"),
    ]
    
    original_id, duplicate_ids = engine._select_original(files_mixed)
    expected_original = 4  # PNG format is better than JPEG when everything else equal
    
    if original_id == expected_original:
        print(f"   ✓ Complex scenario correct: ID {original_id} (high res + early time + better format)")
    else:
        print(f"   ✗ Complex scenario wrong: ID {original_id}, expected {expected_original}")
        # Debug the sort order
        sorted_files = sorted(files_mixed, key=engine._original_sort_key)
        print("     Sort order:")
        for i, f in enumerate(sorted_files):
            marker = "← SELECTED" if i == 0 else ""
            print(f"       {i+1}. ID {f.id}: {f.resolution}px, {f.file_format.format_name}, "
                  f"{f.size}b, {f.exif_datetime} {marker}")
    
    print("\n" + "=" * 50)
    print("✓ Deterministic original selection rules validation complete")


def test_format_classification():
    """Test file format classification and priority."""
    print("\nTesting File Format Classification")
    print("=" * 35)
    
    test_extensions = [
        ("cr2", FileFormat.RAW, 1),
        ("nef", FileFormat.RAW, 1),
        ("arw", FileFormat.RAW, 1),
        ("dng", FileFormat.RAW, 1),
        ("tiff", FileFormat.TIFF, 2),
        ("tif", FileFormat.TIFF, 2),
        ("png", FileFormat.PNG, 3),
        ("jpg", FileFormat.JPEG, 4),
        ("jpeg", FileFormat.JPEG, 4),
        ("webp", FileFormat.WEBP, 5),
        ("bmp", FileFormat.OTHER, 6),
        ("unknown", FileFormat.OTHER, 6),
    ]
    
    all_correct = True
    for ext, expected_format, expected_priority in test_extensions:
        format_obj = FileFormat.from_extension(ext)
        if format_obj != expected_format or format_obj.priority != expected_priority:
            print(f"   ✗ {ext} -> {format_obj.format_name} (priority {format_obj.priority}), "
                  f"expected {expected_format.format_name} (priority {expected_priority})")
            all_correct = False
        else:
            print(f"   ✓ {ext} -> {format_obj.format_name} (priority {format_obj.priority})")
    
    if all_correct:
        print("   ✓ All format classifications correct")
    
    return all_correct


def main():
    """Run all deterministic selection tests."""
    print("Deterministic Original Selection Rules - Detailed Test")
    print("=" * 60)
    
    test_format_classification()
    test_original_selection_rules()
    
    print("\n🎯 All deterministic selection rule tests completed!")


if __name__ == "__main__":
    main()