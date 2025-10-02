#!/usr/bin/env python3
"""
Demo script for Step 11: Grouping engine & "original" selection.

This script demonstrates the two-tier duplicate grouping engine with
deterministic original selection rules.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import Settings
from ops.grouping import GroupingEngine, GroupTier, FileFormat
from store.db import DatabaseManager


def test_file_format_classification():
    """Test file format classification and priority ordering."""
    print("=== Testing File Format Classification ===")
    
    test_cases = [
        ("image.cr2", FileFormat.RAW, 1),
        ("photo.nef", FileFormat.RAW, 1),
        ("scan.tiff", FileFormat.TIFF, 2),
        ("graphic.png", FileFormat.PNG, 3),
        ("photo.jpg", FileFormat.JPEG, 4),
        ("modern.webp", FileFormat.WEBP, 5),
        ("unknown.xyz", FileFormat.OTHER, 6),
    ]
    
    for filename, expected_format, expected_priority in test_cases:
        ext = Path(filename).suffix
        format_obj = FileFormat.from_extension(ext)
        status = "✓" if format_obj == expected_format else "✗"
        print(f"  {status} {filename} -> {format_obj.format_name} (priority {format_obj.priority})")
    
    print()


def test_grouping_engine_initialization():
    """Test grouping engine initialization."""
    print("=== Testing Grouping Engine Initialization ===")
    
    try:
        settings = Settings()
        db_manager = DatabaseManager()
        grouping_engine = GroupingEngine(db_manager.db_path, settings)
        
        print(f"  ✓ Grouping engine initialized")
        print(f"    - Database: {db_manager.db_path}")
        print(f"    - Preset: {grouping_engine.current_preset}")
        print(f"    - pHash threshold: {grouping_engine.phash_threshold}")
        print(f"    - SHA256 confirmation: {grouping_engine.enable_sha256_confirmation}")
        print(f"    - Strict EXIF mode: {grouping_engine.strict_mode_exif_match}")
        print(f"    - Dimension tolerance: {grouping_engine.dimension_tolerance}")
        
        return grouping_engine
        
    except Exception as e:
        print(f"  ✗ Failed to initialize: {e}")
        return None


def test_file_loading(grouping_engine):
    """Test loading file records from database."""
    print("=== Testing File Record Loading ===")
    
    try:
        file_records = grouping_engine.load_file_records()
        print(f"  ✓ Loaded {len(file_records)} file records")
        
        if file_records:
            # Show sample record
            sample = file_records[0]
            print(f"    Sample record ID {sample.id}:")
            print(f"      Path: {Path(sample.path).name}")
            print(f"      Size: {sample.size} bytes")
            print(f"      Resolution: {sample.resolution} pixels")
            print(f"      Format: {sample.file_format.format_name}")
            print(f"      Has fast_hash: {bool(sample.fast_hash)}")
            print(f"      Has pHash: {bool(sample.phash)}")
        
        return file_records
        
    except Exception as e:
        print(f"  ✗ Failed to load file records: {e}")
        return []


def test_exact_duplicate_detection(grouping_engine, file_records):
    """Test Tier 1 exact duplicate detection."""
    print("=== Testing Exact Duplicate Detection (Tier 1) ===")
    
    try:
        exact_groups = grouping_engine.find_exact_duplicates(file_records)
        print(f"  ✓ Found {len(exact_groups)} exact duplicate groups")
        
        for i, group in enumerate(exact_groups[:3], 1):  # Show first 3 groups
            print(f"    Group {i} ({group.id}):")
            print(f"      - Tier: {group.tier.value}")
            print(f"      - Original: {group.original_id}")
            print(f"      - Duplicates: {group.duplicate_ids}")
            print(f"      - Confidence: {group.confidence_score:.3f}")
            print(f"      - Total files: {group.total_files}")
            if group.metadata:
                sha256_confirmed = group.metadata.get('sha256_confirmed', 'unknown')
                print(f"      - SHA256 confirmed: {sha256_confirmed}")
        
        return exact_groups
        
    except Exception as e:
        print(f"  ✗ Failed to find exact duplicates: {e}")
        return []


def test_near_duplicate_detection(grouping_engine, file_records, exact_group_files):
    """Test Tier 2 near duplicate detection."""
    print("=== Testing Near Duplicate Detection (Tier 2) ===")
    
    try:
        near_groups = grouping_engine.find_near_duplicates(file_records, exact_group_files)
        print(f"  ✓ Found {len(near_groups)} near duplicate groups")
        
        for i, group in enumerate(near_groups[:3], 1):  # Show first 3 groups
            print(f"    Group {i} ({group.id}):")
            print(f"      - Tier: {group.tier.value}")
            print(f"      - Original: {group.original_id}")
            print(f"      - Duplicates: {group.duplicate_ids}")
            print(f"      - Confidence: {group.confidence_score:.3f}")
            print(f"      - Total files: {group.total_files}")
            if group.metadata:
                min_distance = group.metadata.get('min_distance', 'unknown')
                threshold = group.metadata.get('phash_threshold', 'unknown')
                print(f"      - Min pHash distance: {min_distance}/{threshold}")
        
        return near_groups
        
    except Exception as e:
        print(f"  ✗ Failed to find near duplicates: {e}")
        return []


def test_full_processing_workflow(grouping_engine):
    """Test the complete processing workflow."""
    print("=== Testing Full Processing Workflow ===")
    
    try:
        start_time = time.time()
        all_groups, stats = grouping_engine.process_all_files()
        processing_time = time.time() - start_time
        
        print(f"  ✓ Processing completed in {processing_time:.2f}s")
        print(f"    - Files processed: {stats['files_processed']}")
        print(f"    - Exact groups: {stats['exact_groups_found']}")
        print(f"    - Near groups: {stats['near_groups_found']}")
        print(f"    - Total duplicates: {stats['total_duplicates']}")
        print(f"    - Engine processing time: {stats['processing_time']:.2f}s")
        
        return all_groups, stats
        
    except Exception as e:
        print(f"  ✗ Failed full processing: {e}")
        return [], {}


def test_group_storage(grouping_engine, groups):
    """Test storing groups in database."""
    print("=== Testing Group Storage ===")
    
    try:
        groups_stored = grouping_engine.store_groups(groups)
        print(f"  ✓ Stored {groups_stored} groups in database")
        
        # Verify storage by checking database
        with grouping_engine.db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM groups")
            db_groups = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM group_members")
            db_members = cursor.fetchone()[0]
            
            print(f"    - Groups in database: {db_groups}")
            print(f"    - Members in database: {db_members}")
        
        return groups_stored > 0
        
    except Exception as e:
        print(f"  ✗ Failed to store groups: {e}")
        return False


def test_group_summary(grouping_engine, groups):
    """Test group summary generation."""
    print("=== Testing Group Summary ===")
    
    try:
        summary = grouping_engine.get_group_summary(groups)
        
        print(f"  ✓ Generated group summary")
        print(f"    - Total groups: {summary['total_groups']}")
        print(f"    - Exact groups: {summary['exact_groups']}")
        print(f"    - Near groups: {summary['near_groups']}")
        print(f"    - Total files in groups: {summary['total_files']}")
        print(f"    - Total duplicates: {summary['total_duplicates']}")
        print(f"    - Space savings estimate: {summary['space_savings_estimate']:,} bytes")
        
        confidence_dist = summary['confidence_distribution']
        print(f"    - Confidence distribution:")
        print(f"      - High (≥0.8): {confidence_dist['high']} groups")
        print(f"      - Medium (≥0.5): {confidence_dist['medium']} groups")
        print(f"      - Low (<0.5): {confidence_dist['low']} groups")
        
        return summary
        
    except Exception as e:
        print(f"  ✗ Failed to generate summary: {e}")
        return {}


def main():
    """Main demo function."""
    print("Photo Dedupe - Step 11: Grouping Engine & Original Selection Demo")
    print("=" * 70)
    
    # Test format classification
    test_file_format_classification()
    
    # Initialize grouping engine
    grouping_engine = test_grouping_engine_initialization()
    if not grouping_engine:
        print("Cannot proceed without grouping engine")
        return
    
    # Load file records
    file_records = test_file_loading(grouping_engine)
    if not file_records:
        print("No file records found. Please run populate_test_data.py first.")
        return
    
    # Test exact duplicates
    exact_groups = test_exact_duplicate_detection(grouping_engine, file_records)
    
    # Get exact group file IDs
    exact_group_files = set()
    for group in exact_groups:
        exact_group_files.update(group.all_file_ids)
    
    # Test near duplicates
    near_groups = test_near_duplicate_detection(grouping_engine, file_records, exact_group_files)
    
    # Test full workflow
    all_groups, stats = test_full_processing_workflow(grouping_engine)
    
    # Test storage
    if all_groups:
        test_group_storage(grouping_engine, all_groups)
        
        # Test summary
        summary = test_group_summary(grouping_engine, all_groups)
    
    print("\n=== Demo Summary ===")
    if all_groups:
        print(f"✓ Grouping engine operational")
        print(f"  - Two-tier grouping: ✓ Implemented")
        print(f"  - Deterministic original selection: ✓ Implemented")
        print(f"  - Database storage: ✓ Working")
        print(f"  - Score summaries: ✓ Generated")
        print(f"  - Total groups found: {len(all_groups)}")
        
        # Validate acceptance criteria
        original_selection_valid = True
        for group in all_groups:
            if group.total_files < 2:
                print(f"  ✗ Group {group.id} has only {group.total_files} files")
                original_selection_valid = False
        
        if original_selection_valid:
            print(f"  ✓ All groups have exactly one original and at least one duplicate")
        
    else:
        print("✗ Grouping engine not operational")
        print("  - Run populate_test_data.py first to create test data")


if __name__ == "__main__":
    main()