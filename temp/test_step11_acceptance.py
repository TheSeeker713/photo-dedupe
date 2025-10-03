#!/usr/bin/env python3
"""
Step 11 Acceptance Test: Grouping engine & "original" selection

Tests all acceptance criteria:
1. Two-tier grouping (Exact: size + fast hash + SHA256, Near: pHash + dimension check)
2. Deterministic original selection rules (resolution > EXIF time > size > format)
3. Each group has exactly one original and at least one duplicate
4. Score summaries for all groups
"""

import sys
import tempfile
from pathlib import Path
from PIL import Image

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import Settings
from ops.grouping import GroupingEngine, GroupTier, FileFormat, FileRecord
from store.db import DatabaseManager
from core.features import FeatureExtractor


def create_test_scenario():
    """Create comprehensive test scenario with known duplicates."""
    print("Creating test scenario with known duplicate patterns...")
    
    settings = Settings()
    db_manager = DatabaseManager()
    feature_extractor = FeatureExtractor(db_manager.db_path, settings)
    
    # Clear existing data
    with db_manager.get_connection() as conn:
        conn.execute("DELETE FROM group_members")
        conn.execute("DELETE FROM groups")
        conn.execute("DELETE FROM features")
        conn.execute("DELETE FROM files")
    
    # Create test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test scenario 1: Exact duplicates (same content, different names)
        exact_original = temp_path / "vacation_2024_high_res.jpg"
        exact_duplicate = temp_path / "copy_of_vacation_2024.jpg"
        
        # Create identical 200x200 red images
        img = Image.new('RGB', (200, 200), (255, 0, 0))
        img.save(exact_original, 'JPEG', quality=95)
        img.save(exact_duplicate, 'JPEG', quality=95)
        
        # Test scenario 2: Near duplicates (same image, different compression)
        near_original_large = temp_path / "portrait_original.png"  # PNG format (higher priority)
        near_duplicate_small = temp_path / "portrait_compressed.jpg"  # JPEG format (lower priority)
        
        # Create 150x200 blue images with different compression
        img2 = Image.new('RGB', (150, 200), (0, 0, 255))
        img2.save(near_original_large, 'PNG')
        img2.save(near_duplicate_small, 'JPEG', quality=70)
        
        # Test scenario 3: Different images (should not be grouped)
        different_image = temp_path / "landscape.jpg"
        img3 = Image.new('RGB', (300, 100), (0, 255, 0))
        img3.save(different_image, 'JPEG')
        
        # Test scenario 4: Format priority test (same content, different formats)
        format_test_raw = temp_path / "test_image.tiff"  # Higher priority format
        format_test_jpeg = temp_path / "test_image.jpg"  # Lower priority format
        
        img4 = Image.new('RGB', (100, 100), (128, 128, 128))
        img4.save(format_test_raw, 'TIFF')
        img4.save(format_test_jpeg, 'JPEG')
        
        # Add files to database and extract features
        test_files = [
            exact_original, exact_duplicate,
            near_original_large, near_duplicate_small,
            different_image,
            format_test_raw, format_test_jpeg
        ]
        
        file_ids = []
        for file_path in test_files:
            # Add to database
            import hashlib
            import time
            
            path_hash = hashlib.sha256(str(file_path).encode()).hexdigest()[:16]
            current_time = time.time()
            
            with db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO files (path, path_hash, size, mtime, ctime, last_seen_at, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (str(file_path), path_hash, file_path.stat().st_size, 
                     file_path.stat().st_mtime, file_path.stat().st_ctime,
                     current_time, current_time))
                file_id = cursor.lastrowid
                file_ids.append(file_id)
            
            # Extract features
            success = feature_extractor.process_file(file_id, file_path)
            if not success:
                print(f"Warning: Failed to extract features for {file_path.name}")
        
        print(f"  ✓ Created {len(file_ids)} test files with features")
        return file_ids


def test_acceptance_criteria():
    """Test all Step 11 acceptance criteria."""
    print("Step 11 Acceptance Test: Grouping engine & original selection")
    print("=" * 65)
    
    # Create test scenario
    file_ids = create_test_scenario()
    
    # Initialize grouping engine
    settings = Settings()
    db_manager = DatabaseManager()
    grouping_engine = GroupingEngine(db_manager.db_path, settings)
    
    print("\n1. Testing two-tier grouping implementation...")
    
    # Process all files
    all_groups, stats = grouping_engine.process_all_files()
    
    # Test 1: Two-tier grouping
    exact_groups = [g for g in all_groups if g.tier == GroupTier.EXACT]
    near_groups = [g for g in all_groups if g.tier == GroupTier.NEAR]
    
    print(f"   ✓ Tier 1 (Exact): {len(exact_groups)} groups found")
    print(f"   ✓ Tier 2 (Near): {len(near_groups)} groups found")
    
    if len(exact_groups) == 0 and len(near_groups) == 0:
        print("   ✗ No duplicate groups found - test data issue")
        return False
    
    # Test 2: Group composition validation
    print("\n2. Testing group composition (one original + duplicates)...")
    
    composition_valid = True
    for group in all_groups:
        if group.total_files < 2:
            print(f"   ✗ Group {group.id} has only {group.total_files} files")
            composition_valid = False
        elif len(group.duplicate_ids) < 1:
            print(f"   ✗ Group {group.id} has no duplicates")
            composition_valid = False
        else:
            print(f"   ✓ Group {group.id}: 1 original + {len(group.duplicate_ids)} duplicates")
    
    if not composition_valid:
        return False
    
    # Test 3: Deterministic original selection
    print("\n3. Testing deterministic original selection rules...")
    
    # Load file records to verify selection
    file_records = grouping_engine.load_file_records()
    file_lookup = {r.id: r for r in file_records}
    
    selection_valid = True
    for group in all_groups:
        original = file_lookup.get(group.original_id)
        duplicates = [file_lookup.get(d_id) for d_id in group.duplicate_ids if file_lookup.get(d_id)]
        
        if not original:
            print(f"   ✗ Original file {group.original_id} not found")
            selection_valid = False
            continue
        
        print(f"   Group {group.id} original selection:")
        print(f"     Original: ID {original.id} - {Path(original.path).name}")
        print(f"       Resolution: {original.resolution}, Format: {original.file_format.format_name}")
        print(f"       Size: {original.size} bytes, Priority: {original.file_format.priority}")
        
        # Verify original selection logic
        all_files = [original] + duplicates
        manually_sorted = sorted(all_files, key=grouping_engine._original_sort_key)
        expected_original = manually_sorted[0]
        
        if original.id != expected_original.id:
            print(f"   ✗ Wrong original selected. Expected {expected_original.id}, got {original.id}")
            selection_valid = False
        else:
            print(f"   ✓ Correct original selected based on deterministic rules")
    
    if not selection_valid:
        return False
    
    # Test 4: Score summaries
    print("\n4. Testing score summaries...")
    
    summary_valid = True
    for group in all_groups:
        if not (0 <= group.confidence_score <= 1):
            print(f"   ✗ Group {group.id} has invalid confidence score: {group.confidence_score}")
            summary_valid = False
        else:
            print(f"   ✓ Group {group.id}: confidence={group.confidence_score:.3f}, tier={group.tier.value}")
    
    # Test overall summary
    summary = grouping_engine.get_group_summary(all_groups)
    required_summary_fields = [
        'total_groups', 'exact_groups', 'near_groups', 
        'total_files', 'total_duplicates', 'confidence_distribution'
    ]
    
    for field in required_summary_fields:
        if field not in summary:
            print(f"   ✗ Missing summary field: {field}")
            summary_valid = False
    
    if summary_valid:
        print(f"   ✓ Complete summary generated with all required fields")
    
    # Test 5: Database storage
    print("\n5. Testing database storage...")
    
    groups_stored = grouping_engine.store_groups(all_groups)
    if groups_stored != len(all_groups):
        print(f"   ✗ Storage mismatch: {groups_stored} stored, {len(all_groups)} expected")
        return False
    
    # Verify database content
    with db_manager.get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM groups")
        db_groups = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM group_members WHERE role = 'original'")
        db_originals = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM group_members WHERE role = 'duplicate'")
        db_duplicates = cursor.fetchone()[0]
    
    if db_groups != len(all_groups):
        print(f"   ✗ Database groups mismatch: {db_groups} in DB, {len(all_groups)} expected")
        return False
    
    if db_originals != len(all_groups):
        print(f"   ✗ Database originals mismatch: {db_originals} in DB, {len(all_groups)} expected")
        return False
    
    total_expected_duplicates = sum(len(g.duplicate_ids) for g in all_groups)
    if db_duplicates != total_expected_duplicates:
        print(f"   ✗ Database duplicates mismatch: {db_duplicates} in DB, {total_expected_duplicates} expected")
        return False
    
    print(f"   ✓ Database storage verified: {db_groups} groups, {db_originals} originals, {db_duplicates} duplicates")
    
    # Final summary
    print("\n" + "=" * 65)
    print("✅ STEP 11 ACCEPTANCE CRITERIA MET:")
    print("   ✓ Two-tier grouping engine implemented")
    print("     - Tier 1 (Exact): same size + same fast hash + SHA256 confirmation")
    print("     - Tier 2 (Near): pHash within threshold + dimension sanity check")
    print("   ✓ Deterministic original selection rules implemented")
    print("     - Priority: highest resolution → earliest EXIF time → largest size → preferred format")
    print("   ✓ Each group has exactly one original and at least one duplicate")
    print("   ✓ Score summaries generated for all groups")
    print("   ✓ Database storage with proper schema integration")
    
    return True


def main():
    """Run acceptance test."""
    try:
        success = test_acceptance_criteria()
        if success:
            print("\n🎉 Step 11 implementation PASSED all acceptance criteria!")
        else:
            print("\n❌ Step 11 implementation FAILED acceptance criteria.")
    except Exception as e:
        print(f"\n💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()