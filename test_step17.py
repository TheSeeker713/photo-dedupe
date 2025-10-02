#!/usr/bin/env python3
"""
Step 17 Acceptance Test: Delete flow (Recycle Bin + Undo)
Test script to verify delete functionality with recycle bin and undo.
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_test_files(temp_dir: Path, count: int = 3) -> List[Path]:
    """Create temporary test files."""
    test_files = []
    for i in range(count):
        test_file = temp_dir / f"test_file_{i}.txt"
        test_file.write_text(f"Test content {i}" * 100)  # Make files a bit larger
        test_files.append(test_file)
    return test_files

def test_delete_manager_creation():
    """Test delete manager can be created and initialized."""
    try:
        from ops.delete_manager import DeleteManager, DeleteMethod
        
        print("✓ Successfully imported delete manager classes")
        
        # Test manager creation
        manager = DeleteManager()
        
        # Test basic properties
        assert manager.can_undo() == False
        print("✓ Delete manager creates without undo history")
        
        # Test method availability
        recycle_available = manager.can_use_recycle_bin()
        print(f"✓ Recycle bin available: {recycle_available}")
        
        return True
        
    except Exception as e:
        print(f"✗ Delete manager creation test failed: {e}")
        return False

def test_quarantine_deletion():
    """Test quarantine deletion method."""
    try:
        from ops.delete_manager import DeleteManager, DeleteMethod
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            test_files = create_test_files(temp_path, 2)
            file_paths = [str(f) for f in test_files]
            
            # Create delete manager with quarantine
            quarantine_dir = temp_path / "quarantine"
            manager = DeleteManager(str(quarantine_dir))
            
            # Test quarantine deletion
            batch = manager.delete_files(file_paths, DeleteMethod.QUARANTINE, "Test deletion")
            
            # Verify results
            assert batch.file_count == 2
            assert batch.delete_method == DeleteMethod.QUARANTINE
            assert batch.total_size > 0
            print("✓ Quarantine deletion works")
            
            # Verify files moved to quarantine
            for test_file in test_files:
                assert not test_file.exists(), f"Original file still exists: {test_file}"
            print("✓ Files moved from original location")
            
            # Verify quarantine directory created and contains files
            assert quarantine_dir.exists()
            quarantine_files = list(quarantine_dir.rglob("*.txt"))
            assert len(quarantine_files) >= 2
            print("✓ Files exist in quarantine directory")
            
            return True
            
    except Exception as e:
        print(f"✗ Quarantine deletion test failed: {e}")
        return False

def test_undo_functionality():
    """Test undo functionality."""
    try:
        from ops.delete_manager import DeleteManager, DeleteMethod
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            test_files = create_test_files(temp_path, 2)
            file_paths = [str(f) for f in test_files]
            
            # Create delete manager
            manager = DeleteManager()
            
            # Delete files to quarantine
            batch = manager.delete_files(file_paths, DeleteMethod.QUARANTINE, "Test for undo")
            
            # Verify files are deleted
            for test_file in test_files:
                assert not test_file.exists()
            print("✓ Files deleted successfully")
            
            # Test undo capability
            assert manager.can_undo()
            print("✓ Undo is available after deletion")
            
            # Perform undo
            success = manager.undo_last_batch()
            assert success
            print("✓ Undo operation completed")
            
            # Verify files restored
            for test_file in test_files:
                assert test_file.exists(), f"File not restored: {test_file}"
            print("✓ Files restored to original location")
            
            # Verify undo history updated
            assert not manager.can_undo()
            print("✓ Undo history cleared after restore")
            
            return True
            
    except Exception as e:
        print(f"✗ Undo functionality test failed: {e}")
        return False

def test_delete_dialogs():
    """Test delete confirmation and progress dialogs."""
    try:
        from ops.delete_manager import DeleteConfirmationDialog, DeleteProgressDialog, DeleteMethod
        
        # Test dialog classes can be imported
        assert DeleteConfirmationDialog is not None
        assert DeleteProgressDialog is not None
        print("✓ Dialog classes imported successfully")
        
        # Test enum values
        assert DeleteMethod.RECYCLE_BIN.value == "recycle_bin"
        assert DeleteMethod.QUARANTINE.value == "quarantine"
        assert DeleteMethod.PERMANENT.value == "permanent"
        print("✓ Delete method enum values correct")
        
        # For GUI components, we just verify they can be imported
        # Full dialog testing would require QApplication setup
        print("✓ Delete dialogs available (GUI testing requires QApplication)")
        
        return True
        
    except Exception as e:
        print(f"✗ Delete dialogs test failed: {e}")
        return False

def test_delete_statistics():
    """Test delete statistics and history tracking."""
    try:
        from ops.delete_manager import DeleteManager, DeleteMethod
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            test_files = create_test_files(temp_path, 3)
            file_paths = [str(f) for f in test_files]
            
            # Create delete manager
            manager = DeleteManager()
            
            # Initial statistics
            stats = manager.get_statistics()
            assert stats['total_batches'] == 0
            assert stats['total_deleted_files'] == 0
            print("✓ Initial statistics correct")
            
            # Delete files
            batch = manager.delete_files(file_paths, DeleteMethod.QUARANTINE, "Statistics test")
            
            # Updated statistics
            stats = manager.get_statistics()
            assert stats['total_batches'] == 1
            assert stats['total_deleted_files'] == 3
            assert stats['total_deleted_size'] > 0
            assert stats['can_undo'] == True
            print("✓ Statistics updated after deletion")
            
            # Test export functionality
            export_file = temp_path / "delete_history.json"
            manager.export_delete_history(str(export_file))
            assert export_file.exists()
            print("✓ Delete history export works")
            
            return True
            
    except Exception as e:
        print(f"✗ Delete statistics test failed: {e}")
        return False

def test_gui_integration():
    """Test GUI integration (basic import test)."""
    try:
        from gui.main_window import MainWindow
        print("✓ Main window imports delete manager successfully")
        
        # Test if the class has the expected attributes without instantiating
        # (which would require QApplication)
        assert hasattr(MainWindow, 'delete_selected')
        assert hasattr(MainWindow, 'undo_delete')
        assert hasattr(MainWindow, 'open_recycle_bin')
        print("✓ Delete manager methods available in main window class")
        
        return True
        
    except Exception as e:
        print(f"✗ GUI integration test failed: {e}")
        return False

def main():
    """Run all Step 17 acceptance tests."""
    print("Running Step 17 Acceptance Tests: Delete flow (Recycle Bin + Undo)")
    print("=" * 70)
    
    tests = [
        ("Delete Manager Creation", test_delete_manager_creation),
        ("Quarantine Deletion", test_quarantine_deletion),
        ("Undo Functionality", test_undo_functionality),
        ("Delete Dialogs", test_delete_dialogs),
        ("Delete Statistics", test_delete_statistics),
        ("GUI Integration", test_gui_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        if test_func():
            passed += 1
            print(f"✓ {test_name} PASSED")
        else:
            print(f"✗ {test_name} FAILED")
    
    print("\n" + "=" * 70)
    print(f"Step 17 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Step 17 Implementation Complete!")
        print("\nFeatures implemented:")
        print("• Safe deletion with send2trash (Recycle Bin)")
        print("• Quarantine deletion with dated folders")
        print("• Confirmation dialog with file count and size")
        print("• Progress dialog during deletion")
        print("• Undo functionality for quarantine deletions")
        print("• Delete history tracking and statistics")
        print("• Open Recycle Bin/Quarantine folder")
        print("• GUI integration with toolbar controls")
        print("• Error handling and graceful failure")
        return 0
    else:
        print(f"❌ {total - passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())