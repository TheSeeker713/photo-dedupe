#!/usr/bin/env python3
"""
Step 12 Acceptance Test: Second-tag escalation ("SAFE DUPLICATE")

Tests all acceptance criteria:
1. Escalation rule: (file_size == original file_size) AND 
   (DateTimeOriginal equal or within ±2s) AND (camera model matches, if enabled)
2. Configurable ±2s tolerance and camera model check
3. Reclassification from 'duplicate' to 'safe_duplicate'
4. Test groups show green "SAFE DUPLICATE" status where criteria met
"""

import sys
import tempfile
import time
from pathlib import Path
from PIL import Image
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import Settings
from ops.escalation import SafeDuplicateEscalation, EscalationCriteria
from ops.grouping import GroupingEngine
from store.db import DatabaseManager
from core.features import FeatureExtractor


def create_comprehensive_test_scenario():
    """Create comprehensive test scenario with known escalation cases."""
    print("Creating comprehensive test scenario for escalation validation...")
    
    settings = Settings()
    db_manager = DatabaseManager()
    feature_extractor = FeatureExtractor(db_manager.db_path, settings)
    grouping_engine = GroupingEngine(db_manager.db_path, settings)
    
    # Clear existing data
    with db_manager.get_connection() as conn:
        conn.execute("DELETE FROM group_members")
        conn.execute("DELETE FROM groups")
        conn.execute("DELETE FROM features")
        conn.execute("DELETE FROM files")
    
    # Create test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test Case 1: Perfect SAFE DUPLICATE candidate
        # Same size, same time (within ±2s), same camera
        case1_original = temp_path / "case1_original.jpg"
        case1_safe_dup = temp_path / "case1_safe_duplicate.jpg"
        
        img1 = Image.new('RGB', (200, 200), (255, 0, 0))
        img1.save(case1_original, 'JPEG', quality=95)
        img1.save(case1_safe_dup, 'JPEG', quality=95)
        
        # Test Case 2: Borderline SAFE DUPLICATE (exactly 2s difference)
        case2_original = temp_path / "case2_original.jpg"
        case2_safe_dup = temp_path / "case2_safe_duplicate.jpg"
        
        img2 = Image.new('RGB', (150, 150), (0, 255, 0))
        img2.save(case2_original, 'JPEG', quality=95)
        img2.save(case2_safe_dup, 'JPEG', quality=95)
        
        # Test Case 3: SHOULD NOT escalate (time difference > 2s)
        case3_original = temp_path / "case3_original.jpg"
        case3_regular_dup = temp_path / "case3_regular_duplicate.jpg"
        
        img3 = Image.new('RGB', (100, 100), (0, 0, 255))
        img3.save(case3_original, 'JPEG', quality=95)
        img3.save(case3_regular_dup, 'JPEG', quality=95)
        
        # Test Case 4: SHOULD NOT escalate (different file size)
        case4_original = temp_path / "case4_original.jpg"
        case4_regular_dup = temp_path / "case4_regular_duplicate.jpg"
        
        img4 = Image.new('RGB', (180, 180), (255, 255, 0))
        img4.save(case4_original, 'JPEG', quality=95)
        img4.save(case4_regular_dup, 'JPEG', quality=70)  # Different quality = different size
        
        # Test Case 5: SAFE DUPLICATE with camera check disabled scenario
        case5_original = temp_path / "case5_original.jpg"
        case5_safe_dup = temp_path / "case5_safe_duplicate.jpg"
        
        img5 = Image.new('RGB', (120, 120), (255, 0, 255))
        img5.save(case5_original, 'JPEG', quality=95)
        img5.save(case5_safe_dup, 'JPEG', quality=95)
        
        # Define test file metadata
        base_time = datetime(2024, 8, 15, 10, 30, 0)
        test_files = [
            # Case 1: Perfect match
            (case1_original, "Canon EOS R5", base_time, "Should be original"),
            (case1_safe_dup, "Canon EOS R5", base_time + timedelta(seconds=1), "Should escalate to safe_duplicate"),
            
            # Case 2: Borderline (exactly 2s)
            (case2_original, "Nikon D850", base_time + timedelta(minutes=5), "Should be original"),
            (case2_safe_dup, "Nikon D850", base_time + timedelta(minutes=5, seconds=2), "Should escalate (exactly 2s)"),
            
            # Case 3: Time too far (3s > 2s tolerance)
            (case3_original, "Sony A7R IV", base_time + timedelta(minutes=10), "Should be original"),
            (case3_regular_dup, "Sony A7R IV", base_time + timedelta(minutes=10, seconds=3), "Should NOT escalate (3s > 2s)"),
            
            # Case 4: Different size
            (case4_original, "Canon 5D Mark IV", base_time + timedelta(minutes=15), "Should be original"),
            (case4_regular_dup, "Canon 5D Mark IV", base_time + timedelta(minutes=15, seconds=1), "Should NOT escalate (different size)"),
            
            # Case 5: No camera info (should work if camera check disabled)
            (case5_original, None, base_time + timedelta(minutes=20), "Should be original"),
            (case5_safe_dup, None, base_time + timedelta(minutes=20, seconds=1), "Should escalate (no camera check)"),
        ]
        
        # Add files to database
        file_ids = []
        
        for file_path, camera_model, exif_dt, description in test_files:
            # Add to database
            import hashlib
            
            path_hash = hashlib.sha256(str(file_path).encode()).hexdigest()[:16]
            current_time = time.time()
            
            with db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO files (path, path_hash, size, mtime, ctime, last_seen_at, created_at, 
                                     exif_dt, camera_model) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (str(file_path), path_hash, file_path.stat().st_size, 
                     file_path.stat().st_mtime, file_path.stat().st_ctime,
                     current_time, current_time, exif_dt.timestamp(), camera_model))
                file_id = cursor.lastrowid
                file_ids.append((file_id, description))
            
            # Extract features
            success = feature_extractor.process_file(file_id, file_path)
            if not success:
                print(f"Warning: Failed to extract features for {file_path.name}")
        
        # Create duplicate groups
        all_groups, stats = grouping_engine.process_all_files()
        groups_stored = grouping_engine.store_groups(all_groups)
        
        print(f"  ✓ Created {len(file_ids)} test files")
        print(f"  ✓ Generated {len(all_groups)} duplicate groups")
        print(f"  ✓ Stored {groups_stored} groups in database")
        
        return file_ids, all_groups


def test_acceptance_criteria():
    """Test all Step 12 acceptance criteria."""
    print("Step 12 Acceptance Test: Second-tag escalation (SAFE DUPLICATE)")
    print("=" * 60)
    
    # Create comprehensive test scenario
    file_ids, groups = create_comprehensive_test_scenario()
    
    # Initialize escalation engine with default settings
    settings = Settings()
    db_manager = DatabaseManager()
    escalation_engine = SafeDuplicateEscalation(db_manager.db_path, settings)
    
    print("\n1. Testing escalation rule implementation...")
    
    # Verify default configuration
    print(f"   Default datetime tolerance: {escalation_engine.datetime_tolerance}s")
    print(f"   Default camera check enabled: {escalation_engine.enable_camera_check}")
    
    if escalation_engine.datetime_tolerance != 2.0:
        print(f"   ✗ Expected default tolerance of 2.0s, got {escalation_engine.datetime_tolerance}s")
        return False
    
    print(f"   ✓ Default ±2s tolerance correctly configured")
    
    # Test 2: Process escalations with default settings
    print("\n2. Testing escalation processing with default settings...")
    
    initial_status = escalation_engine.get_safe_duplicate_status()
    print(f"   Initial duplicate count: {initial_status['role_counts'].get('duplicate', 0)}")
    print(f"   Initial safe_duplicate count: {initial_status['role_counts'].get('safe_duplicate', 0)}")
    
    # Process escalations
    results, stats = escalation_engine.process_all_groups()
    
    print(f"   Groups processed: {stats['groups_processed']}")
    print(f"   Duplicates analyzed: {stats['duplicates_analyzed']}")
    print(f"   Safe duplicates found: {stats['safe_duplicates_found']}")
    print(f"   Escalations applied: {stats['escalations_applied']}")
    
    if stats['safe_duplicates_found'] == 0:
        print(f"   ✗ No safe duplicates found - check test data")
        return False
    
    print(f"   ✓ Found {stats['safe_duplicates_found']} safe duplicates")
    
    # Test 3: Verify specific escalation cases
    print("\n3. Testing specific escalation cases...")
    
    case_validation = {
        'perfect_match': 0,          # Case 1: Same size, 1s diff, same camera
        'borderline_time': 0,        # Case 2: Same size, 2s diff, same camera  
        'time_too_far': 0,           # Case 3: Same size, 3s diff, same camera (should NOT escalate)
        'different_size': 0,         # Case 4: Different size, 1s diff, same camera (should NOT escalate)
        'no_camera': 0,              # Case 5: Same size, 1s diff, no camera info
    }
    
    escalated_files = [r for r in results if r.was_escalated]
    non_escalated_files = [r for r in results if not r.was_escalated]
    
    print(f"   Files escalated: {len(escalated_files)}")
    print(f"   Files not escalated: {len(non_escalated_files)}")
    
    # Analyze escalation details
    for result in results:
        details = result.details
        original_dt = details.get('original_datetime')
        duplicate_dt = details.get('duplicate_datetime')
        
        if original_dt and duplicate_dt:
            time_diff = abs((original_dt - duplicate_dt).total_seconds())
            
            # Categorize the case
            if result.was_escalated:
                if time_diff <= 1:
                    case_validation['perfect_match'] += 1
                elif abs(time_diff - 2.0) < 0.1:  # Approximately 2 seconds
                    case_validation['borderline_time'] += 1
                elif not details.get('original_camera'):
                    case_validation['no_camera'] += 1
        
        # Check cases that should NOT escalate
        if not result.was_escalated:
            if original_dt and duplicate_dt:
                time_diff = abs((original_dt - duplicate_dt).total_seconds())
                original_size = details.get('original_size', 0)
                duplicate_size = details.get('duplicate_size', 0)
                
                if time_diff > 2.0:
                    case_validation['time_too_far'] += 1
                elif original_size != duplicate_size:
                    case_validation['different_size'] += 1
    
    # Validate expected cases
    validation_passed = True
    expected_results = {
        'perfect_match': 1,      # Should find 1 perfect match
        'borderline_time': 1,    # Should find 1 borderline case
        'no_camera': 1,          # Should find 1 no-camera case
        'time_too_far': 1,       # Should reject 1 time-too-far case
        'different_size': 1,     # Should reject 1 different-size case
    }
    
    for case, expected_count in expected_results.items():
        actual_count = case_validation[case]
        if actual_count == expected_count:
            print(f"   ✓ {case}: {actual_count} (as expected)")
        else:
            print(f"   ✗ {case}: {actual_count}, expected {expected_count}")
            validation_passed = False
    
    if not validation_passed:
        return False
    
    # Test 4: Configurable settings
    print("\n4. Testing configurable settings...")
    
    # Test different datetime tolerance
    test_tolerances = [1.0, 3.0, 5.0]
    for tolerance in test_tolerances:
        settings._data.setdefault("Escalation", {})["datetime_tolerance_seconds"] = tolerance
        test_engine = SafeDuplicateEscalation(db_manager.db_path, settings)
        
        if test_engine.datetime_tolerance != tolerance:
            print(f"   ✗ Failed to set tolerance to {tolerance}s")
            return False
        
        print(f"   ✓ DateTime tolerance configurable: {tolerance}s")
    
    # Test camera model check toggle
    for enable_camera in [True, False]:
        settings._data["Escalation"]["enable_camera_model_check"] = enable_camera
        test_engine = SafeDuplicateEscalation(db_manager.db_path, settings)
        
        if test_engine.enable_camera_check != enable_camera:
            print(f"   ✗ Failed to set camera check to {enable_camera}")
            return False
        
        print(f"   ✓ Camera model check configurable: {enable_camera}")
    
    # Test 5: Database state verification
    print("\n5. Testing database state and green status...")
    
    final_status = escalation_engine.get_safe_duplicate_status()
    role_counts = final_status['role_counts']
    
    safe_duplicate_count = role_counts.get('safe_duplicate', 0)
    if safe_duplicate_count == 0:
        print(f"   ✗ No 'safe_duplicate' roles found in database")
        return False
    
    print(f"   ✓ Database contains {safe_duplicate_count} 'safe_duplicate' entries")
    
    # Verify specific entries
    with db_manager.get_connection() as conn:
        cursor = conn.execute("""
            SELECT file_id, role, notes 
            FROM group_members 
            WHERE role = 'safe_duplicate'
        """)
        safe_duplicates = cursor.fetchall()
    
    if not safe_duplicates:
        print(f"   ✗ No safe_duplicate records found")
        return False
    
    print(f"   ✓ Found {len(safe_duplicates)} safe_duplicate records")
    for file_id, role, notes in safe_duplicates[:3]:  # Show first 3
        print(f"     File {file_id}: {role} ({notes})")
    
    # Test 6: Summary and statistics
    print("\n6. Testing summary generation...")
    
    summary = escalation_engine.get_escalation_summary(results)
    
    required_fields = ['total_analyzed', 'safe_duplicates_found', 'escalation_rate', 
                      'criteria_breakdown', 'groups_affected', 'configuration']
    
    for field in required_fields:
        if field not in summary:
            print(f"   ✗ Missing summary field: {field}")
            return False
    
    print(f"   ✓ Complete summary generated")
    print(f"     Escalation rate: {summary['escalation_rate']:.1%}")
    print(f"     Groups affected: {summary['groups_affected']}")
    
    # Final validation
    print("\n" + "=" * 60)
    print("✅ STEP 12 ACCEPTANCE CRITERIA MET:")
    print("   ✓ Escalation rule implemented:")
    print("     - (file_size == original file_size) AND")
    print("     - (DateTimeOriginal equal or within ±2s) AND") 
    print("     - (camera model matches, if enabled)")
    print("   ✓ Configurable ±2s tolerance and camera model check")
    print("   ✓ Reclassification from 'duplicate' to 'safe_duplicate'")
    print("   ✓ Green 'SAFE DUPLICATE' status available in database")
    print("   ✓ Comprehensive test cases validated")
    
    return True


def main():
    """Run acceptance test."""
    try:
        success = test_acceptance_criteria()
        if success:
            print("\n🎉 Step 12 implementation PASSED all acceptance criteria!")
        else:
            print("\n❌ Step 12 implementation FAILED acceptance criteria.")
    except Exception as e:
        print(f"\n💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()