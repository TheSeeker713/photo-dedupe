"""
Quick test for Step 25 dataset generation.
This script tests just the dataset creation without running the full validation.
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_dataset_generation():
    """Test that we can generate a test dataset."""
    try:
        from tests.validation_dataset import TestDatasetGenerator
        
        print("Testing dataset generation...")
        
        # Create temp directory
        temp_dir = Path(tempfile.mkdtemp())
        print(f"Using temp directory: {temp_dir}")
        
        # Generate dataset
        generator = TestDatasetGenerator(temp_dir / "test_gen")
        test_specs, expectations = generator.generate_test_dataset()
        
        # Check results
        test_dir = generator.get_test_directory()
        generated_files = list(test_dir.glob("*"))
        
        print(f"Generated {len(generated_files)} test files")
        print(f"Expected {expectations.total_files} files")
        print(f"Expected groups: {len(expectations.expected_groups)}")
        
        # List some files
        print("\nGenerated files:")
        for i, file_path in enumerate(generated_files[:10]):  # Show first 10
            print(f"  {file_path.name}")
            if i == 9 and len(generated_files) > 10:
                print(f"  ... and {len(generated_files) - 10} more")
        
        # Cleanup
        generator.cleanup()
        shutil.rmtree(temp_dir)
        
        print("\n✅ Dataset generation test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Dataset generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_dataset_generation()
    sys.exit(0 if success else 1)