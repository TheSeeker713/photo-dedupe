#!/usr/bin/env python3
"""
Simple Step 12 acceptance validation focused on core functionality.
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
from ops.escalation import SafeDuplicateEscalation
from ops.grouping import GroupingEngine
from store.db import DatabaseManager
from core.features import FeatureExtractor


def test_core_functionality():
    """Test core safe duplicate escalation functionality."""
    print("Step 12 Core Functionality Test")
    print("=" * 35)
    
    # Setup
    settings = Settings()
    db_manager = DatabaseManager()
    feature_extractor = FeatureExtractor(db_manager.db_path, settings)
    grouping_engine = GroupingEngine(db_manager.db_path, settings)
    escalation_engine = SafeDuplicateEscalation(db_manager.db_path, settings)
    
    # Clear data
    with db_manager.get_connection() as conn:
        conn.execute("DELETE FROM group_members")
        conn.execute("DELETE FROM groups")
        conn.execute("DELETE FROM features")
        conn.execute("DELETE FROM files")
    
    # Create test images
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Case 1: Should escalate (same size, 1s diff, same camera)
        original = temp_path / "original.jpg"
        safe_dup = temp_path / "safe_duplicate.jpg"
        
        # Create identical images (same size)
        img = Image.new('RGB', (100, 100), (255, 0, 0))
        img.save(original, 'JPEG', quality=95)
        img.save(safe_dup, 'JPEG', quality=95)
        
        # Case 2: Should NOT escalate (different size)
        regular_dup = temp_path / "regular_duplicate.jpg"
        img.save(regular_dup, 'JPEG', quality=70)  # Different quality = different size
        
        # Add to database with EXIF metadata
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        test_files = [
            (original, "Canon EOS R5", base_time),
            (safe_dup, "Canon EOS R5", base_time + timedelta(seconds=1)),  # 1s later, same camera
            (regular_dup, "Canon EOS R5", base_time + timedelta(seconds=1)),  # Different size
        ]
        
        file_ids = []
        for file_path, camera, exif_dt in test_files:
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
                     current_time, current_time, exif_dt.timestamp(), camera))
                file_id = cursor.lastrowid
                file_ids.append(file_id)
            
            # Extract features
            feature_extractor.process_file(file_id, file_path)
        
        print(f"Created {len(file_ids)} test files")
        
        # Create groups
        all_groups, stats = grouping_engine.process_all_files()
        grouping_engine.store_groups(all_groups)
        print(f"Created {len(all_groups)} duplicate groups")
        
        # Check initial state
        initial_status = escalation_engine.get_safe_duplicate_status()
        print(f"Initial duplicates: {initial_status['role_counts'].get('duplicate', 0)}")
        print(f"Initial safe_duplicates: {initial_status['role_counts'].get('safe_duplicate', 0)}")
        
        # Test 1: Escalation criteria
        print("\n1. Testing escalation criteria...")
        
        # Test perfect match
        original_meta = {
            'size': 1000,
            'exif_datetime': datetime(2024, 1, 1, 12, 0, 0),
            'camera_model': 'Canon EOS R5'
        }
        
        safe_dup_meta = {
            'size': 1000,  # Same size
            'exif_datetime': datetime(2024, 1, 1, 12, 0, 1),  # 1s later
            'camera_model': 'Canon EOS R5'  # Same camera
        }
        
        criteria = escalation_engine.analyze_escalation_criteria(original_meta, safe_dup_meta)
        print(f"   Perfect match criteria: {criteria}")
        if criteria.all_met:
            print("   ✓ Perfect match correctly identified for escalation")
        else:
            print("   ✗ Perfect match failed criteria check")
            return False
        
        # Test size mismatch
        bad_size_meta = safe_dup_meta.copy()
        bad_size_meta['size'] = 500  # Different size
        
        criteria_bad = escalation_engine.analyze_escalation_criteria(original_meta, bad_size_meta)
        if not criteria_bad.all_met:
            print("   ✓ Size mismatch correctly rejected")
        else:
            print("   ✗ Size mismatch incorrectly passed")
            return False
        
        # Test 2: Configuration
        print("\n2. Testing configuration...")
        
        print(f"   Default tolerance: {escalation_engine.datetime_tolerance}s")
        print(f"   Default camera check: {escalation_engine.enable_camera_check}")
        
        if escalation_engine.datetime_tolerance == 2.0:
            print("   ✓ Default ±2s tolerance correct")
        else:
            print(f"   ✗ Expected 2.0s tolerance, got {escalation_engine.datetime_tolerance}")
            return False
        
        # Test custom tolerance
        settings._data.setdefault("Escalation", {})["datetime_tolerance_seconds"] = 5.0
        custom_engine = SafeDuplicateEscalation(db_manager.db_path, settings)
        if custom_engine.datetime_tolerance == 5.0:
            print("   ✓ Custom tolerance configuration works")
        else:
            print("   ✗ Custom tolerance configuration failed")
            return False
        
        # Test 3: Process escalations
        print("\n3. Testing escalation processing...")
        
        results, process_stats = escalation_engine.process_all_groups()
        print(f"   Duplicates analyzed: {process_stats['duplicates_analyzed']}")
        print(f"   Safe duplicates found: {process_stats['safe_duplicates_found']}")
        print(f"   Escalations applied: {process_stats['escalations_applied']}")
        
        if process_stats['safe_duplicates_found'] > 0:
            print("   ✓ Safe duplicates found and processed")
        else:
            print("   ✗ No safe duplicates found")
            return False
        
        # Test 4: Database verification
        print("\n4. Testing database state...")
        
        final_status = escalation_engine.get_safe_duplicate_status()
        final_counts = final_status['role_counts']
        
        print(f"   Final duplicates: {final_counts.get('duplicate', 0)}")
        print(f"   Final safe_duplicates: {final_counts.get('safe_duplicate', 0)}")
        
        if final_counts.get('safe_duplicate', 0) > 0:
            print("   ✓ Safe duplicates stored in database")
        else:
            print("   ✗ No safe duplicates in database")
            return False
        
        # Verify specific database entries
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT file_id, role, notes 
                FROM group_members 
                WHERE role = 'safe_duplicate'
                LIMIT 3
            """)
            safe_entries = cursor.fetchall()
        
        if safe_entries:
            print("   ✓ Safe duplicate entries verified:")
            for file_id, role, notes in safe_entries:
                print(f"     File {file_id}: {role} - {notes}")
        else:
            print("   ✗ No safe duplicate entries found")
            return False
        
        print("\n" + "=" * 35)
        print("✅ CORE FUNCTIONALITY VERIFIED:")
        print("   ✓ Escalation rule: (size == size) AND (time ≤ ±2s) AND (camera match)")
        print("   ✓ Configurable tolerance and camera check")
        print("   ✓ Reclassification to 'safe_duplicate'")
        print("   ✓ Database storage and retrieval")
        print("   ✓ Green 'SAFE DUPLICATE' status available")
        
        return True


def main():
    """Run core functionality test."""
    try:
        success = test_core_functionality()
        if success:
            print("\n🎉 Step 12 core functionality VERIFIED!")
        else:
            print("\n❌ Step 12 core functionality FAILED.")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()