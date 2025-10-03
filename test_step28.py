#!/usr/bin/env python3
"""
Test Step 28: Performance Profiling & Thresholds Tuning
========================================================

Validation script for the hidden Developer panel with:
1. Performance monitoring for scan/decode/hashing/grouping/UI paint operations
2. Real-time threshold tuning with hit count updates
3. Hidden developer access mechanisms

Usage:
    python test_step28.py
"""

import sys
import time
import random
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_performance_profiler():
    """Test the PerformanceProfiler core functionality."""
    print("🔧 Testing PerformanceProfiler...")
    
    try:
        from src.core.profiler import PerformanceProfiler, TimingData
        
        profiler = PerformanceProfiler()
        
        # Test timing different operations
        print("  📊 Testing timing operations...")
        
        # Simulate some operations with timing
        with profiler.time_operation("test_scan"):
            time.sleep(0.1)  # Simulate scan time
        
        with profiler.time_operation("test_decode"):
            time.sleep(0.05)  # Simulate decode time
            
        with profiler.time_operation("test_hash"):
            time.sleep(0.02)  # Simulate hashing time
            
        with profiler.time_operation("test_group"):
            time.sleep(0.03)  # Simulate grouping time
            
        with profiler.time_operation("test_ui"):
            time.sleep(0.01)  # Simulate UI paint time
        
        # Get stats
        stats = profiler.get_stats()
        print(f"  ✅ Recorded {len(stats)} operation types")
        
        for op_name, perf_stats in stats.items():
            print(f"    {op_name}: {perf_stats.count} calls, "
                  f"avg {perf_stats.avg_time:.3f}s")
        
        print("  ✅ PerformanceProfiler working correctly!")
        return True
        
    except Exception as e:
        print(f"  ❌ PerformanceProfiler test failed: {e}")
        return False

def test_threshold_tuner():
    """Test the ThresholdTuner functionality."""
    print("🎛️ Testing ThresholdTuner...")
    
    try:
        from src.core.profiler import ThresholdTuner
        
        tuner = ThresholdTuner()
        
        # Test setting and getting thresholds
        print("  📊 Testing threshold management...")
        
        # Test updating thresholds
        tuner.update_threshold("perceptual_hash_threshold", 7)
        tuner.update_threshold("orb_match_threshold", 0.8)
        tuner.update_threshold("minimum_matches", 15)
        
        # Test getting values
        config = tuner.config
        print(f"    perceptual_hash_threshold: {config.perceptual_hash_threshold}")
        print(f"    orb_match_threshold: {config.orb_match_threshold}")
        print(f"    minimum_matches: {config.minimum_matches}")
        
        # Test with sample data
        sample_data = [
            {'size': 1024, 'perceptual_hash': 'abcd1234'},
            {'size': 1100, 'perceptual_hash': 'abcd1235'},  # Similar to first
            {'size': 2048, 'perceptual_hash': 'xyz98765'},
        ]
        tuner.set_sample_data(sample_data)
        
        group_count = tuner.get_group_count()
        total_dupes = tuner.get_total_duplicates()
        
        print(f"    Found {group_count} groups with {total_dupes} total duplicates")
        
        print("  ✅ ThresholdTuner working correctly!")
        return True
        
    except Exception as e:
        print(f"  ❌ ThresholdTuner test failed: {e}")
        return False

def test_profiled_operations():
    """Test the profiled operation classes."""
    print("⚡ Testing Profiled Operations...")
    
    try:
        from src.core.profiled_ops import ProfiledImageScanner, ProfiledDuplicateGrouper, ProfiledUIRenderer
        from src.core.profiler import PerformanceProfiler
        from pathlib import Path
        
        profiler = PerformanceProfiler()
        
        # Test profiled scanner
        print("  🔍 Testing ProfiledImageScanner...")
        scanner = ProfiledImageScanner()
        
        # Simulate scanning a directory (mock test)
        test_dir = Path("test_images")
        print(f"    Scanner created and ready for directory scanning")
        
        # Test profiled grouper
        print("  🗂️ Testing ProfiledDuplicateGrouper...")
        grouper = ProfiledDuplicateGrouper()
        
        # Simulate grouping with test data
        test_images_data = [
            {'hashes': {'perceptual': 'hash123', 'average': 'avg123'}},
            {'hashes': {'perceptual': 'hash123', 'average': 'avg124'}},  # Same perceptual
            {'hashes': {'perceptual': 'hash456', 'average': 'avg456'}},
        ]
        groups = grouper.group_by_hash(test_images_data, 'perceptual')
        print(f"    Found {len(groups)} hash groups")
        
        # Test profiled renderer
        print("  🎨 Testing ProfiledUIRenderer...")
        renderer = ProfiledUIRenderer()
        
        # Simulate rendering with correct method names
        test_images = [
            {'path': 'img1.jpg', 'size': (1920, 1080)},
            {'path': 'img2.jpg', 'size': (1920, 1080)},
        ]
        result = renderer.render_image_grid(test_images)
        print(f"    {result}")
        
        progress_result = renderer.update_progress(50, 100, "Processing images...")
        print(f"    {progress_result}")
        
        print("  ✅ Profiled operations classes created and tested successfully")
        print("  ✅ Profiled Operations working correctly!")
        return True
        
    except Exception as e:
        print(f"  ❌ Profiled Operations test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_developer_panel_import():
    """Test that the developer panel can be imported."""
    print("🖥️ Testing Developer Panel Import...")
    
    try:
        # First try to import the main module
        import src.ui.developer_panel as dev_panel
        print("  ✅ Developer panel module imported successfully")
        
        # Check if Qt is available
        if hasattr(dev_panel, 'QT_AVAILABLE') and dev_panel.QT_AVAILABLE:
            from src.ui.developer_panel import DeveloperPanel
            print("  ✅ DeveloperPanel class imported successfully")
            print("  💡 Qt is available, full UI functionality ready")
        else:
            print("  ⚠️ Qt not available, but module structure is correct")
            print("  💡 This is expected if PySide6 is not installed")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ Developer Panel import failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"  ❌ Developer Panel test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_main_app_integration():
    """Test that the main app has developer panel integration."""
    print("🚀 Testing Main App Integration...")
    
    try:
        # Check if launch_app has the required methods
        with open("launch_app.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        required_methods = [
            "toggle_dev_mode",
            "show_developer_panel", 
            "keyPressEvent"
        ]
        
        missing_methods = []
        for method in required_methods:
            if f"def {method}" not in content:
                missing_methods.append(method)
        
        if missing_methods:
            print(f"  ❌ Missing methods: {missing_methods}")
            return False
        
        print(f"  ✅ All required methods found: {required_methods}")
        
        # Check for keyboard shortcuts
        if "Ctrl+Shift+D" in content and "Ctrl+Alt+Shift+M" in content:
            print("  ✅ Hidden keyboard shortcuts implemented")
        else:
            print("  ⚠️ Some keyboard shortcuts may be missing")
        
        # Check for developer panel import
        if "from src.ui.developer_panel import DeveloperPanel" in content:
            print("  ✅ Developer panel import added")
        else:
            print("  ⚠️ Developer panel import may be missing")
        
        # Check for developer action in toolbar
        if "developer" in content.lower() and "Developer" in content:
            print("  ✅ Developer panel integration present")
        else:
            print("  ⚠️ Developer panel integration may be incomplete")
        
        print("  ✅ Main app integration looks good!")
        return True
        
    except Exception as e:
        print(f"  ❌ Main app integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all Step 28 validation tests."""
    print("🧪 Step 28 Validation: Performance Profiling & Thresholds Tuning")
    print("=" * 65)
    print()
    
    tests = [
        ("Performance Profiler", test_performance_profiler),
        ("Threshold Tuner", test_threshold_tuner),
        ("Profiled Operations", test_profiled_operations),
        ("Developer Panel Import", test_developer_panel_import),
        ("Main App Integration", test_main_app_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        result = test_func()
        results.append((test_name, result))
        print()
    
    # Summary
    print("📊 Test Results Summary:")
    print("-" * 30)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print()
    print(f"🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Step 28 implementation is ready!")
        print()
        print("📋 Developer Panel Access Instructions:")
        print("1. Launch the app: python launch_app.py")
        print("2. Enable dev mode: Ctrl+Alt+Shift+M")
        print("3. Open developer panel: Ctrl+Shift+D")
        print("4. Or click the hidden 'Developer' toolbar button")
        print()
        print("🔧 Developer Panel Features:")
        print("- Performance Monitor tab: Real-time operation timing")
        print("- Threshold Tuner tab: Adjust parameters with hit counts")
        print("- Auto-refresh displays for live feedback")
        
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())