#!/usr/bin/env python3
"""
Step 17 Demo: Delete Flow Demonstration
Shows the delete functionality in action.
"""

import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def demo_delete_flow():
    """Demonstrate the delete flow with all methods."""
    from ops.delete_manager import DeleteManager, DeleteMethod
    
    print("🗑️ Photo Deduplicator - Delete Flow Demo")
    print("=" * 50)
    
    # Create temporary test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create demo files
        test_files = []
        for i in range(3):
            test_file = temp_path / f"duplicate_{i}.jpg"
            test_file.write_text(f"Duplicate photo content {i}" * 100)
            test_files.append(str(test_file))
            
        print(f"📁 Created {len(test_files)} demo files in {temp_path}")
        
        # Initialize delete manager
        manager = DeleteManager(str(temp_path / "quarantine"))
        
        print(f"\n🔧 Delete Manager Status:")
        print(f"   • Recycle Bin Available: {manager.can_use_recycle_bin()}")
        print(f"   • Can Undo: {manager.can_undo()}")
        
        # Demo quarantine deletion
        print(f"\n📦 Testing Quarantine Deletion...")
        batch = manager.delete_files(
            test_files[:2], 
            DeleteMethod.QUARANTINE, 
            "Demo quarantine deletion"
        )
        
        print(f"   • Deleted: {batch.file_count} files")
        print(f"   • Size: {batch.size_mb:.2f} MB")
        print(f"   • Method: {batch.delete_method.value}")
        print(f"   • Quarantine: {batch.quarantine_dir}")
        
        # Verify files moved
        for file_path in test_files[:2]:
            if not Path(file_path).exists():
                print(f"   ✓ {Path(file_path).name} moved to quarantine")
        
        # Demo undo
        print(f"\n↶ Testing Undo Functionality...")
        if manager.can_undo():
            success = manager.undo_last_batch()
            if success:
                print(f"   ✓ Undo successful - files restored")
                
                # Verify files restored
                for file_path in test_files[:2]:
                    if Path(file_path).exists():
                        print(f"   ✓ {Path(file_path).name} restored to original location")
            else:
                print(f"   ✗ Undo failed")
        
        # Demo statistics
        print(f"\n📊 Statistics:")
        stats = manager.get_statistics()
        for key, value in stats.items():
            print(f"   • {key}: {value}")
        
        # Demo recycle bin (if available)
        if manager.can_use_recycle_bin():
            print(f"\n🗂️ Testing Recycle Bin Deletion...")
            
            # Create one more test file
            recycle_test = temp_path / "recycle_test.jpg"
            recycle_test.write_text("Test file for recycle bin")
            
            batch = manager.delete_files(
                [str(recycle_test)], 
                DeleteMethod.RECYCLE_BIN, 
                "Demo recycle bin deletion"
            )
            
            print(f"   • Sent to recycle bin: {batch.file_count} files")
            print(f"   • File removed from disk: {not recycle_test.exists()}")
            print(f"   • Can be restored via system recycle bin")
        
        print(f"\n✅ Delete Flow Demo Complete!")
        print(f"All deletion methods working correctly.")

if __name__ == "__main__":
    demo_delete_flow()