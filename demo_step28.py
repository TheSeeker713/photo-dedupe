#!/usr/bin/env python3
"""
Step 28 Demo: Performance Profiling & Thresholds Tuning
=======================================================

Demonstration of the developer panel functionality.
This script shows how to use the profiling and threshold tuning features.

Usage:
    python demo_step28.py
"""

import sys
import time
import random
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def demo_performance_profiling():
    """Demonstrate the performance profiling system."""
    print("🔧 Performance Profiling Demo")
    print("=" * 40)
    
    from src.core.profiler import get_profiler
    from src.core.profiled_ops import ProfiledImageScanner, ProfiledDuplicateGrouper, ProfiledUIRenderer
    
    profiler = get_profiler()
    
    # Create profiled operations
    scanner = ProfiledImageScanner()
    grouper = ProfiledDuplicateGrouper()
    renderer = ProfiledUIRenderer()
    
    # Simulate some operations
    print("📊 Simulating operations...")
    
    # Simulate scanning
    test_dir = Path("test_images")
    print(f"  Scanning {test_dir}...")
    
    # Simulate grouping
    test_data = [
        {'hashes': {'perceptual': 'abc123', 'average': 'def456'}, 'file_size': 1024000},
        {'hashes': {'perceptual': 'abc124', 'average': 'def457'}, 'file_size': 1025000},  # Similar
        {'hashes': {'perceptual': 'xyz789', 'average': 'uvw012'}, 'file_size': 2048000},
        {'hashes': {'perceptual': 'abc123', 'average': 'def456'}, 'file_size': 1024500},  # Duplicate
    ]
    
    print(f"  Grouping {len(test_data)} images...")
    groups = grouper.group_by_hash(test_data, 'perceptual')
    similarity_groups = grouper.group_by_similarity(test_data, 0.05)
    
    print(f"  Found {len(groups)} hash groups")
    print(f"  Found {len(similarity_groups)} similarity groups")
    
    # Simulate UI rendering
    print("  Rendering UI...")
    renderer.render_image_grid(test_data[:2])
    renderer.update_progress(75, 100, "Finalizing...")
    
    # Show profiler stats
    print("\n📈 Performance Statistics:")
    stats = profiler.get_stats()
    
    for operation, stat in stats.items():
        print(f"  {operation}:")
        print(f"    Calls: {stat.count}")
        print(f"    Total: {stat.total_time * 1000:.2f}ms")
        print(f"    Average: {stat.avg_time * 1000:.2f}ms")
        print(f"    Min: {stat.min_time * 1000:.2f}ms")
        print(f"    Max: {stat.max_time * 1000:.2f}ms")
        print()

def demo_threshold_tuning():
    """Demonstrate the threshold tuning system."""
    print("🎛️ Threshold Tuning Demo")
    print("=" * 40)
    
    from src.core.profiler import get_threshold_tuner
    
    tuner = get_threshold_tuner()
    
    # Set up sample data for threshold testing
    sample_data = []
    for i in range(20):
        sample_data.append({
            'size': random.randint(800000, 2000000),
            'perceptual_hash': f"hash{i:04d}",
            'file_path': f"test_image_{i:03d}.jpg"
        })
    
    # Add some similar items
    sample_data.append({
        'size': 1024000,
        'perceptual_hash': 'hash0001',  # Similar to item 1
        'file_path': 'duplicate_of_001.jpg'
    })
    
    sample_data.append({
        'size': 1025000,  # Similar size to above
        'perceptual_hash': 'hash0002',  # Similar to item 2
        'file_path': 'duplicate_of_002.jpg'
    })
    
    tuner.set_sample_data(sample_data)
    
    print(f"📊 Loaded {len(sample_data)} sample images")
    
    # Test different threshold values
    thresholds_to_test = [3, 5, 7, 10, 15]
    
    print("\n🔬 Testing Perceptual Hash Thresholds:")
    for threshold in thresholds_to_test:
        tuner.update_threshold('perceptual_hash_threshold', threshold)
        group_count = tuner.get_group_count()
        total_dupes = tuner.get_total_duplicates()
        
        print(f"  Threshold {threshold}: {group_count} groups, {total_dupes} duplicates")
    
    # Test size difference thresholds
    size_thresholds = [0.05, 0.1, 0.2, 0.3]
    
    print("\n📏 Testing Size Difference Thresholds:")
    for threshold in size_thresholds:
        tuner.update_threshold('size_difference_threshold', threshold)
        group_count = tuner.get_group_count()
        total_dupes = tuner.get_total_duplicates()
        
        print(f"  Threshold {threshold:.2f}: {group_count} groups, {total_dupes} duplicates")
    
    # Show final configuration
    config = tuner.config
    print("\n⚙️ Final Threshold Configuration:")
    print(f"  Perceptual Hash Threshold: {config.perceptual_hash_threshold}")
    print(f"  ORB Match Threshold: {config.orb_match_threshold}")
    print(f"  Size Difference Threshold: {config.size_difference_threshold}")
    print(f"  Minimum Matches: {config.minimum_matches}")

def demo_developer_panel_access():
    """Show how to access the developer panel."""
    print("🖥️ Developer Panel Access Demo")
    print("=" * 40)
    
    print("🚀 To access the hidden Developer Panel:")
    print()
    print("Method 1 - Keyboard Shortcuts:")
    print("  1. Launch app: python launch_app.py")
    print("  2. Enable dev mode: Ctrl+Alt+Shift+M")
    print("  3. Open developer panel: Ctrl+Shift+D")
    print()
    print("Method 2 - Hidden Toolbar Button:")
    print("  1. Launch app: python launch_app.py") 
    print("  2. Look for hidden 'Developer' button in toolbar")
    print("  3. Click it to open the panel")
    print()
    print("🔧 Developer Panel Features:")
    print("  📊 Performance Monitor Tab:")
    print("    - Real-time operation timing display")
    print("    - Statistics for scan/decode/hash/group/UI operations")
    print("    - Activity log with metadata")
    print("    - Color-coded performance indicators")
    print()
    print("  🎛️ Threshold Tuner Tab:")
    print("    - Adjust duplicate detection parameters")
    print("    - Real-time group count updates")
    print("    - Detection rate feedback")
    print("    - Preset configurations for different scenarios")
    print()
    print("  ⚡ Auto-refresh:")
    print("    - Live updates every 1 second")
    print("    - Toggle profiling on/off")
    print("    - Reset statistics")
    print()
    print("💡 Professional Use Cases:")
    print("  - Fine-tune detection algorithms for specific image types")
    print("  - Optimize performance for large image collections") 
    print("  - Debug slow operations and bottlenecks")
    print("  - Validate detection accuracy with test datasets")
    print("  - Export performance profiles for analysis")

def main():
    """Run the Step 28 demonstration."""
    print("🎮 Step 28 Demonstration")
    print("Performance Profiling & Thresholds Tuning")
    print("=" * 50)
    print()
    
    demos = [
        demo_performance_profiling,
        demo_threshold_tuning,
        demo_developer_panel_access,
    ]
    
    for i, demo_func in enumerate(demos, 1):
        print(f"Demo {i}/{len(demos)}:")
        demo_func()
        print()
        
        if i < len(demos):
            input("Press Enter to continue to next demo...")
            print()
    
    print("🎉 Step 28 demonstration complete!")
    print()
    print("Next steps:")
    print("- Launch the full app to see the developer panel in action")
    print("- Try the keyboard shortcuts to access hidden features")
    print("- Experiment with threshold tuning on real image data")
    print("- Use profiling to optimize performance for your use case")

if __name__ == "__main__":
    main()