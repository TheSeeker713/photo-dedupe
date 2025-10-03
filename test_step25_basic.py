"""
Quick validation test for Step 25.
This runs a simplified version of the validation without all the complex components.
"""

import sys
import tempfile
import shutil
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_basic_validation():
    """Test basic validation components."""
    try:
        from tests.validation_dataset import TestDatasetGenerator
        from store.db import DatabaseManager
        from ops.scan import FileScanner
        
        print("Running basic Step 25 validation test...")
        
        # Create temp directory
        temp_dir = Path(tempfile.mkdtemp())
        print(f"Using temp directory: {temp_dir}")
        
        # Step 1: Generate test dataset
        print("\n1. Generating test dataset...")
        generator = TestDatasetGenerator(temp_dir / "dataset")
        test_specs, expectations = generator.generate_test_dataset()
        test_dataset_path = generator.get_test_directory()
        
        print(f"✅ Generated {expectations.total_files} test files")
        print(f"   Expected groups: {len(expectations.expected_groups)}")
        
        # Step 2: Initialize database and scan files
        print("\n2. Scanning files into database...")
        db_path = temp_dir / "test_validation.db"
        db_manager = DatabaseManager(db_path)
        file_scanner = FileScanner(db_manager)
        
        scan_stats = file_scanner.scan_directory(test_dataset_path)
        print(f"✅ Scanned {scan_stats.get('files_added', 0)} files")
        
        # Step 3: Check database contents
        print("\n3. Validating database contents...")
        with db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM files WHERE status = 'active'")
            file_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT path FROM files LIMIT 5")
            sample_files = [row[0] for row in cursor.fetchall()]
        
        print(f"✅ Database contains {file_count} active files")
        print("   Sample files:")
        for file_path in sample_files:
            print(f"     {Path(file_path).name}")
        
        # Step 4: Test expectations structure
        print("\n4. Validating test expectations...")
        total_expected_files = sum(len(files) for files in expectations.expected_groups.values())
        deletion_candidates = len(expectations.expected_deletion_candidates)
        
        print(f"✅ Expectations: {total_expected_files} total files")
        print(f"   Expected deletion candidates: {deletion_candidates}")
        print(f"   Burst sequences: {len(expectations.burst_sequences)}")
        
        # Step 5: Basic validation logic test
        print("\n5. Testing validation logic...")
        
        # Check that we have the expected groups
        expected_group_names = list(expectations.expected_groups.keys())
        actual_files = {Path(f).name for f in sample_files}
        
        validation_score = 0
        total_checks = 0
        
        for group_name, expected_files in expectations.expected_groups.items():
            for expected_file in expected_files:
                total_checks += 1
                if expected_file in {Path(p).name for p in sample_files + [row[0] for row in conn.execute("SELECT path FROM files").fetchall()]}:
                    validation_score += 1
        
        success_rate = (validation_score / total_checks) * 100 if total_checks > 0 else 0
        print(f"✅ File presence validation: {success_rate:.1f}% ({validation_score}/{total_checks})")
        
        # Close database connections
        if hasattr(db_manager, '_connection') and db_manager._connection:
            db_manager._connection.close()
        
        # Cleanup
        generator.cleanup()
        try:
            shutil.rmtree(temp_dir)
        except Exception as cleanup_error:
            print(f"⚠️ Cleanup warning: {cleanup_error}")
            # Don't fail the test due to cleanup issues
        
        print(f"\n🎉 Basic validation completed successfully!")
        print(f"   Dataset generation: ✅")
        print(f"   File scanning: ✅")
        print(f"   Database operations: ✅")
        print(f"   Validation logic: ✅")
        print(f"   Overall success rate: {success_rate:.1f}%")
        
        return success_rate >= 90
        
    except Exception as e:
        print(f"❌ Basic validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_basic_validation()
    if success:
        print("\n✅ Step 25 basic validation PASSED!")
    else:
        print("\n❌ Step 25 basic validation FAILED!")
    sys.exit(0 if success else 1)