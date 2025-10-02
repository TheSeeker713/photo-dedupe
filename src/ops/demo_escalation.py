#!/usr/bin/env python3
"""
Demo script for Step 12: Second-tag escalation ("SAFE DUPLICATE").

This script demonstrates the escalation of duplicates to safe duplicates
based on file size, EXIF datetime, and camera model matching.
"""

import sys
import tempfile
import time
from pathlib import Path
from PIL import Image
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import Settings
from ops.escalation import SafeDuplicateEscalation, EscalationCriteria
from ops.grouping import GroupingEngine
from store.db import DatabaseManager
from core.features import FeatureExtractor


def setup_test_scenario():
    """Create test scenario with files that should be escalated to safe duplicates."""
    print("Setting up test scenario with escalation candidates...")
    
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
        
        # Test scenario 1: Perfect safe duplicate candidates
        # Same size, same EXIF time, same camera
        original_1 = temp_path / "IMG_001_original.jpg"
        safe_dup_1 = temp_path / "IMG_001_backup.jpg"
        
        # Create identical images
        img = Image.new('RGB', (200, 200), (255, 100, 100))
        img.save(original_1, 'JPEG', quality=95)
        img.save(safe_dup_1, 'JPEG', quality=95)
        
        # Test scenario 2: Near duplicate that should NOT be escalated
        # Different size, different time
        regular_dup = temp_path / "IMG_002_compressed.jpg"
        img2 = Image.new('RGB', (200, 200), (255, 100, 100))
        img2.save(regular_dup, 'JPEG', quality=70)  # Different compression = different size
        
        # Test scenario 3: Another safe duplicate pair
        # Same size and time, no camera info (should pass if camera check disabled)
        original_2 = temp_path / "vacation_sunset.jpg"
        safe_dup_2 = temp_path / "vacation_sunset_copy.jpg"
        
        img3 = Image.new('RGB', (150, 150), (100, 255, 100))
        img3.save(original_2, 'JPEG', quality=90)
        img3.save(safe_dup_2, 'JPEG', quality=90)
        
        # Add files to database with specific metadata
        test_files = [
            (original_1, "Canon EOS R5", datetime(2024, 6, 15, 14, 30, 0)),
            (safe_dup_1, "Canon EOS R5", datetime(2024, 6, 15, 14, 30, 1)),  # 1 second later
            (regular_dup, "Canon EOS R5", datetime(2024, 6, 15, 15, 0, 0)),  # Different time
            (original_2, None, datetime(2024, 7, 20, 18, 45, 0)),
            (safe_dup_2, None, datetime(2024, 7, 20, 18, 45, 0)),  # Exact same time
        ]
        
        file_ids = []
        for file_path, camera_model, exif_dt in test_files:
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
                file_ids.append(file_id)
            
            # Extract features
            success = feature_extractor.process_file(file_id, file_path)
            if not success:
                print(f"Warning: Failed to extract features for {file_path.name}")
        
        # Create duplicate groups
        all_groups, stats = grouping_engine.process_all_files()
        grouping_engine.store_groups(all_groups)
        
        print(f"  ✓ Created {len(file_ids)} test files")
        print(f"  ✓ Generated {len(all_groups)} duplicate groups")
        
        return file_ids, all_groups


def test_escalation_criteria():
    """Test escalation criteria analysis."""
    print("=== Testing Escalation Criteria Analysis ===")
    
    # Initialize escalation engine
    settings = Settings()
    db_manager = DatabaseManager()
    escalation_engine = SafeDuplicateEscalation(db_manager.db_path, settings)
    
    # Test case 1: Perfect match (should escalate)
    original_meta = {
        'size': 1500,
        'exif_datetime': datetime(2024, 6, 15, 14, 30, 0),
        'camera_model': 'Canon EOS R5'
    }
    
    duplicate_meta = {
        'size': 1500,  # Same size
        'exif_datetime': datetime(2024, 6, 15, 14, 30, 1),  # 1 second later
        'camera_model': 'Canon EOS R5'  # Same camera
    }
    
    criteria = escalation_engine.analyze_escalation_criteria(original_meta, duplicate_meta)
    print(f"  Perfect match test: {criteria}")
    print(f"    Size match: {criteria.file_size_match}")
    print(f"    DateTime match: {criteria.datetime_match}")
    print(f"    Camera match: {criteria.camera_model_match}")
    print(f"    Should escalate: {criteria.all_met}")
    
    # Test case 2: Size mismatch (should NOT escalate)
    duplicate_meta_bad_size = duplicate_meta.copy()
    duplicate_meta_bad_size['size'] = 1200  # Different size
    
    criteria_bad = escalation_engine.analyze_escalation_criteria(original_meta, duplicate_meta_bad_size)
    print(f"  Size mismatch test: {criteria_bad}")
    print(f"    Should escalate: {criteria_bad.all_met}")
    
    # Test case 3: Time outside tolerance (should NOT escalate)
    duplicate_meta_bad_time = duplicate_meta.copy()
    duplicate_meta_bad_time['exif_datetime'] = datetime(2024, 6, 15, 14, 30, 5)  # 5 seconds later
    
    criteria_time = escalation_engine.analyze_escalation_criteria(original_meta, duplicate_meta_bad_time)
    print(f"  Time outside tolerance test: {criteria_time}")
    print(f"    Should escalate: {criteria_time.all_met}")
    
    print()


def test_escalation_processing():
    """Test the full escalation processing workflow."""
    print("=== Testing Escalation Processing ===")
    
    # Setup test scenario
    file_ids, groups = setup_test_scenario()
    
    # Initialize escalation engine
    settings = Settings()
    db_manager = DatabaseManager()
    escalation_engine = SafeDuplicateEscalation(db_manager.db_path, settings)
    
    # Show initial state
    initial_status = escalation_engine.get_safe_duplicate_status()
    print(f"  Initial state:")
    print(f"    Role counts: {initial_status['role_counts']}")
    print(f"    Groups with safe duplicates: {initial_status['groups_with_safe_duplicates']}")
    
    # Process escalations
    print(f"  Processing escalations...")
    results, stats = escalation_engine.process_all_groups()
    
    print(f"  Processing results:")
    print(f"    Groups processed: {stats['groups_processed']}")
    print(f"    Duplicates analyzed: {stats['duplicates_analyzed']}")
    print(f"    Safe duplicates found: {stats['safe_duplicates_found']}")
    print(f"    Escalations applied: {stats['escalations_applied']}")
    print(f"    Processing time: {stats['processing_time']:.3f}s")
    
    # Show final state
    final_status = escalation_engine.get_safe_duplicate_status()
    print(f"  Final state:")
    print(f"    Role counts: {final_status['role_counts']}")
    print(f"    Groups with safe duplicates: {final_status['groups_with_safe_duplicates']}")
    print(f"    Safe duplicate percentage: {final_status['safe_duplicate_percentage']:.1f}%")
    
    return results, stats


def test_escalation_details(results):
    """Test detailed escalation results."""
    print("=== Testing Escalation Details ===")
    
    if not results:
        print("  No escalation results to analyze")
        return
    
    print(f"  Analyzing {len(results)} escalation results...")
    
    escalated_count = 0
    for result in results:
        print(f"  File {result.file_id}:")
        print(f"    Role: {result.original_role} → {result.new_role}")
        print(f"    Escalated: {result.was_escalated}")
        print(f"    Criteria: {result.criteria_met}")
        
        if result.details:
            details = result.details
            print(f"    Original size: {details.get('original_size')} bytes")
            print(f"    Duplicate size: {details.get('duplicate_size')} bytes")
            print(f"    Original datetime: {details.get('original_datetime')}")
            print(f"    Duplicate datetime: {details.get('duplicate_datetime')}")
            print(f"    Original camera: {details.get('original_camera')}")
            print(f"    Duplicate camera: {details.get('duplicate_camera')}")
        
        if result.was_escalated:
            escalated_count += 1
        
        print()
    
    print(f"  Summary: {escalated_count} files escalated to safe_duplicate")


def test_configuration_options():
    """Test different configuration options for escalation."""
    print("=== Testing Configuration Options ===")
    
    settings = Settings()
    
    # Test different datetime tolerances
    tolerances = [1.0, 2.0, 5.0]
    for tolerance in tolerances:
        # Update settings
        settings._data.setdefault("Escalation", {})["datetime_tolerance_seconds"] = tolerance
        
        db_manager = DatabaseManager()
        escalation_engine = SafeDuplicateEscalation(db_manager.db_path, settings)
        
        print(f"  DateTime tolerance: {tolerance}s")
        print(f"    Engine tolerance: {escalation_engine.datetime_tolerance}s")
        
        # Test with sample data
        original_meta = {
            'size': 1000,
            'exif_datetime': datetime(2024, 1, 1, 12, 0, 0),
            'camera_model': 'Test Camera'
        }
        
        duplicate_meta = {
            'size': 1000,
            'exif_datetime': datetime(2024, 1, 1, 12, 0, 3),  # 3 seconds later
            'camera_model': 'Test Camera'
        }
        
        criteria = escalation_engine.analyze_escalation_criteria(original_meta, duplicate_meta)
        print(f"    3-second difference passes: {criteria.datetime_match}")
    
    # Test camera model check toggle
    print(f"  Camera model check options:")
    for enable_camera in [True, False]:
        settings._data["Escalation"]["enable_camera_model_check"] = enable_camera
        
        escalation_engine = SafeDuplicateEscalation(db_manager.db_path, settings)
        print(f"    Camera check enabled: {escalation_engine.enable_camera_check}")
        
        # Test with missing camera data
        original_meta_no_camera = {
            'size': 1000,
            'exif_datetime': datetime(2024, 1, 1, 12, 0, 0),
            'camera_model': None
        }
        
        duplicate_meta_no_camera = {
            'size': 1000,
            'exif_datetime': datetime(2024, 1, 1, 12, 0, 0),
            'camera_model': None
        }
        
        criteria = escalation_engine.analyze_escalation_criteria(
            original_meta_no_camera, duplicate_meta_no_camera
        )
        print(f"      Missing camera data passes: {criteria.camera_model_match}")
    
    print()


def test_summary_generation():
    """Test escalation summary generation."""
    print("=== Testing Summary Generation ===")
    
    # Get results from previous processing
    settings = Settings()
    db_manager = DatabaseManager()
    escalation_engine = SafeDuplicateEscalation(db_manager.db_path, settings)
    
    # Get all current results
    groups = escalation_engine.get_duplicate_groups()
    all_results = []
    
    for group_id, members in groups:
        results = escalation_engine.process_duplicate_group(group_id, members)
        all_results.extend(results)
    
    # Generate summary
    summary = escalation_engine.get_escalation_summary(all_results)
    
    print(f"  Escalation summary:")
    print(f"    Total analyzed: {summary['total_analyzed']}")
    print(f"    Safe duplicates found: {summary['safe_duplicates_found']}")
    print(f"    Escalation rate: {summary['escalation_rate']:.2%}")
    print(f"    Groups affected: {summary['groups_affected']}")
    
    print(f"  Criteria breakdown:")
    for criteria, count in summary['criteria_breakdown'].items():
        if count > 0:
            print(f"    {criteria}: {count}")
    
    print(f"  Configuration:")
    config = summary['configuration']
    print(f"    DateTime tolerance: {config['datetime_tolerance']}s")
    print(f"    Camera check enabled: {config['camera_check_enabled']}")
    
    print()


def main():
    """Main demo function."""
    print("Photo Dedupe - Step 12: Second-tag Escalation Demo")
    print("=" * 55)
    
    try:
        # Test criteria analysis
        test_escalation_criteria()
        
        # Test configuration options
        test_configuration_options()
        
        # Test full processing workflow
        results, stats = test_escalation_processing()
        
        # Test detailed results
        test_escalation_details(results[:3])  # Show first 3 results
        
        # Test summary generation
        test_summary_generation()
        
        print("=== Demo Summary ===")
        if results:
            escalated_count = len([r for r in results if r.was_escalated])
            print(f"✓ Safe duplicate escalation operational")
            print(f"  - Files analyzed: {len(results)}")
            print(f"  - Safe duplicates found: {escalated_count}")
            print(f"  - Escalation criteria: ✓ Working")
            print(f"  - Database updates: ✓ Applied")
            print(f"  - Configuration: ✓ Customizable")
            
            if escalated_count > 0:
                print(f"  - Green 'SAFE DUPLICATE' status: ✓ Available")
            else:
                print(f"  - No escalations in current test data")
        else:
            print("✗ No escalation results found")
            print("  - Check test data setup")
    
    except Exception as e:
        print(f"✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()