#!/usr/bin/env python3
"""
Step 15: GUI Shell Acceptance Test
Tests that the GUI application meets the acceptance criteria.
"""

import sys
import time
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Global app instance to avoid singleton issues
app = None
window = None

def setup_app():
    """Set up the QApplication and main window."""
    global app, window
    
    if app is None:
        from PySide6.QtWidgets import QApplication
        from gui.main_window import MainWindow
        
        app = QApplication([])
        window = MainWindow()
    
    return app, window

def test_gui_components():
    """Test that all GUI components are available and functional."""
    print("1. Testing GUI components availability...")
    
    try:
        app, window = setup_app()
        
        # Test main window creation
        assert window is not None, "Main window should be created"
        assert window.windowTitle() == "Photo Deduplicator", "Window title should be set"
        
        # Test toolbar components exist
        toolbar_actions = [
            'pick_folders_action', 'start_action', 'pause_action', 
            'resume_action', 'delete_action', 'export_action', 'settings_action'
        ]
        
        for action in toolbar_actions:
            assert hasattr(window, action), f"{action} should exist"
        
        # Test toolbar checkboxes
        assert hasattr(window, 'include_subfolders_cb'), "Include subfolders checkbox should exist"
        assert hasattr(window, 'dry_run_cb'), "Dry run checkbox should exist"
        
        # Test left pane components
        assert hasattr(window, 'filter_combo'), "Filter combo should exist"
        assert hasattr(window, 'groups_list'), "Groups list should exist"
        assert hasattr(window, 'space_saved_label'), "Space saved label should exist"
        
        # Test right pane components
        assert hasattr(window, 'preview_tabs'), "Preview tabs should exist"
        assert hasattr(window, 'original_preview'), "Original preview should exist"
        assert hasattr(window, 'candidates_grid'), "Candidates grid should exist"
        assert hasattr(window, 'compare_widget'), "Compare widget should exist"
        
        # Test status bar components
        assert hasattr(window, 'worker_status'), "Worker status should exist"
        assert hasattr(window, 'cache_status_label'), "Cache status label should exist"
        
        print("  ✓ All GUI components available")
        return True
        
    except Exception as e:
        print(f"  ✗ GUI components test failed: {e}")
        return False

def test_sample_data_rendering():
    """Test that sample data is properly loaded and rendered."""
    print("2. Testing sample data rendering...")
    
    try:
        app, window = setup_app()
        
        # Test sample groups are loaded
        assert len(window.sample_groups) > 0, "Sample groups should be loaded"
        assert len(window.sample_files) > 0, "Sample files should be loaded"
        
        # Test groups list has items
        groups_count = window.groups_list.topLevelItemCount()
        assert groups_count > 0, f"Groups list should have items, got {groups_count}"
        
        # Test filter combo has options
        filter_count = window.filter_combo.count()
        assert filter_count == 5, f"Filter combo should have 5 options, got {filter_count}"
        
        # Test space estimate is calculated
        space_text = window.space_saved_label.text()
        assert "MB" in space_text, f"Space estimate should show MB, got: {space_text}"
        
        print("  ✓ Sample data properly rendered")
        return True
        
    except Exception as e:
        print(f"  ✗ Sample data rendering test failed: {e}")
        return False

def test_action_states():
    """Test that actions are appropriately enabled/disabled."""
    print("3. Testing action enable/disable states...")
    
    try:
        app, window = setup_app()
        
        # Test initial states
        assert window.start_action.isEnabled(), "Start action should be enabled initially"
        assert not window.pause_action.isEnabled(), "Pause action should be disabled initially"
        assert not window.resume_action.isEnabled(), "Resume action should be disabled initially"
        assert not window.delete_action.isEnabled(), "Delete action should be disabled initially"
        assert window.export_action.isEnabled(), "Export action should be enabled"
        assert window.settings_action.isEnabled(), "Settings action should be enabled"
        
        # Test group selection enables delete action
        if window.groups_list.topLevelItemCount() > 0:
            window.groups_list.setCurrentItem(window.groups_list.topLevelItem(0))
            window.load_group_files(1)  # Load first group
            
            # After loading a group with duplicates, delete should be enabled
            assert window.delete_action.isEnabled(), "Delete action should be enabled after selecting group with duplicates"
        
        print("  ✓ Action states working correctly")
        return True
        
    except Exception as e:
        print(f"  ✗ Action states test failed: {e}")
        return False

def test_ui_responsiveness():
    """Test basic UI responsiveness and interactions."""
    print("4. Testing UI responsiveness...")
    
    try:
        app, window = setup_app()
        
        # Test filter combo interaction
        original_count = 0
        for i in range(window.groups_list.topLevelItemCount()):
            if not window.groups_list.topLevelItem(i).isHidden():
                original_count += 1
        
        # Change filter and test
        window.filter_combo.setCurrentText("Exact")
        window.filter_groups("Exact")
        
        exact_count = 0
        for i in range(window.groups_list.topLevelItemCount()):
            if not window.groups_list.topLevelItem(i).isHidden():
                exact_count += 1
        
        assert exact_count <= original_count, "Filtering should reduce or maintain item count"
        
        # Test tab switching
        window.preview_tabs.setCurrentIndex(1)
        assert window.preview_tabs.currentIndex() == 1, "Tab switching should work"
        
        print("  ✓ UI responsiveness working")
        return True
        
    except Exception as e:
        print(f"  ✗ UI responsiveness test failed: {e}")
        return False

def test_app_launch():
    """Test that the application launches successfully."""
    print("5. Testing application launch...")
    
    try:
        app, window = setup_app()
        
        # Show the window briefly
        window.show()
        
        # Process events to ensure window is properly initialized
        app.processEvents()
        
        # Verify window is visible
        assert window.isVisible(), "Window should be visible after show()"
        
        # Test basic properties
        assert window.width() > 0, "Window should have positive width"
        assert window.height() > 0, "Window should have positive height"
        
        print("  ✓ Application launches successfully")
        
        # Hide the window
        window.hide()
        
        return True
        
    except Exception as e:
        print(f"  ✗ Application launch test failed: {e}")
        return False

def main():
    """Run Step 15 acceptance tests."""
    print("Starting Step 15 Acceptance Tests...")
    print("\n=== Step 15 Acceptance Test ===")
    
    # Check if PySide6 is available
    try:
        from PySide6.QtWidgets import QApplication
        print("PySide6 is available, running GUI tests...")
    except ImportError:
        print("❌ PySide6 is not available. Cannot run GUI tests.")
        print("Install PySide6 with: pip install PySide6")
        return 1
    
    tests = [
        test_gui_components,
        test_sample_data_rendering,
        test_action_states,
        test_ui_responsiveness,
        test_app_launch,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    # Clean up the app
    global app
    if app:
        app.quit()
    
    print(f"\n{'='*50}")
    print("STEP 15 ACCEPTANCE TEST RESULTS:")
    print(f"{'='*50}")
    
    test_names = [
        "GUI Components",
        "Sample Data Rendering", 
        "Action States",
        "UI Responsiveness",
        "Application Launch"
    ]
    
    for i, name in enumerate(test_names):
        if i < passed:
            print(f"✓ PASS: {name}")
        else:
            print(f"✗ FAIL: {name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All acceptance criteria met!")
    else:
        print(f"\n❌ {total - passed} acceptance criteria not met. Review failed tests.")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())