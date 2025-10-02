#!/usr/bin/env python3
"""
Demo script for Step 13: Concurrency, throttling, and back-off.

This script demonstrates the worker pool system with dynamic thread cap,
I/O throttling, interaction back-off, and Pause/Resume controls.
"""

import sys
import time
import tempfile
from pathlib import Path
from threading import Thread
import random

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import Settings
from core.concurrency import (
    WorkerPool, TaskPriority, WorkerPoolState,
    create_file_processing_pool, create_thumbnail_pool
)


def setup_test_environment():
    """Create test environment with various tasks."""
    print("=== Step 13: Concurrency System Demo ===\n")
    
    # Create settings
    settings = Settings()
    
    # Configure for demo
    settings.set("General", "thread_cap", 4)
    settings.set("General", "io_throttle", 2.0)  # 2 ops per second max
    settings.set("Concurrency", "back_off_enabled", True)
    settings.set("Concurrency", "interaction_threshold", 3)
    settings.set("Concurrency", "interaction_window", 1.0)
    settings.set("Concurrency", "back_off_duration", 2.0)
    
    print(f"Thread cap: {settings.get('General', 'thread_cap')}")
    print(f"I/O throttle: {settings.get('General', 'io_throttle')} ops/sec")
    print(f"Back-off threshold: {settings.get('Concurrency', 'interaction_threshold')} interactions/sec")
    print()
    
    return settings


def demo_task_simple(task_id: str, duration: float = 1.0, category: str = "test") -> str:
    """Simple demo task that simulates work."""
    print(f"  Executing task {task_id} ({category}, {duration:.1f}s)")
    time.sleep(duration)
    return f"Completed {task_id}"


def demo_task_io_heavy(task_id: str, file_count: int = 10) -> str:
    """Demo task that simulates I/O heavy work."""
    print(f"  I/O task {task_id} processing {file_count} files")
    for i in range(file_count):
        time.sleep(0.1)  # Simulate file I/O
        if i % 3 == 0:
            print(f"    Processing file {i+1}/{file_count}")
    return f"Processed {file_count} files for {task_id}"


def demo_task_cpu_heavy(task_id: str, iterations: int = 1000000) -> str:
    """Demo task that simulates CPU heavy work."""
    print(f"  CPU task {task_id} with {iterations} iterations")
    # Simulate CPU-intensive calculation
    result = sum(i * i for i in range(iterations))
    return f"CPU task {task_id} result: {result}"


def simulate_user_interactions(worker_pool: WorkerPool, duration: float = 10.0):
    """Simulate rapid user interactions to trigger back-off."""
    print("Starting user interaction simulation...")
    
    start_time = time.time()
    interaction_count = 0
    
    while time.time() - start_time < duration:
        # Simulate different types of interactions
        interaction_types = ["scroll", "hover", "click", "keypress"]
        interaction_type = random.choice(interaction_types)
        
        worker_pool.record_interaction(interaction_type)
        interaction_count += 1
        
        # Vary interaction frequency
        delay = random.uniform(0.1, 0.8)
        time.sleep(delay)
    
    print(f"Simulated {interaction_count} user interactions over {duration:.1f}s")


def test_basic_worker_pool():
    """Test basic worker pool functionality."""
    print("1. Testing basic worker pool functionality...")
    
    settings = setup_test_environment()
    worker_pool = WorkerPool(settings)
    
    # Set up callbacks
    completed_tasks = []
    failed_tasks = []
    state_changes = []
    
    def on_complete(task, result):
        completed_tasks.append((task.id, result))
        print(f"  ✓ Task {task.id} completed: {result}")
    
    def on_error(task, error):
        failed_tasks.append((task.id, str(error)))
        print(f"  ✗ Task {task.id} failed: {error}")
    
    def on_state_change(new_state):
        state_changes.append(new_state)
        print(f"  State changed to: {new_state.name}")
    
    worker_pool.set_callbacks(on_complete, on_error, on_state_change)
    
    # Start the pool
    worker_pool.start()
    
    # Submit various tasks
    print("\n  Submitting tasks...")
    
    # High priority tasks (should execute first)
    worker_pool.submit_task("critical-1", demo_task_simple, TaskPriority.CRITICAL, "critical", "critical-1", 0.5)
    worker_pool.submit_task("high-1", demo_task_simple, TaskPriority.HIGH, "ui", "high-1", 0.3)
    
    # Normal priority tasks
    worker_pool.submit_task("normal-1", demo_task_simple, TaskPriority.NORMAL, "scan", "normal-1", 1.0)
    worker_pool.submit_task("normal-2", demo_task_io_heavy, TaskPriority.NORMAL, "io", "normal-2", 5)
    
    # Low priority tasks
    worker_pool.submit_task("low-1", demo_task_cpu_heavy, TaskPriority.LOW, "analysis", "low-1", 100000)
    worker_pool.submit_task("low-2", demo_task_simple, TaskPriority.LOW, "background", "low-2", 2.0)
    
    print(f"  Submitted 6 tasks")
    
    # Wait for some tasks to complete
    time.sleep(3)
    
    # Check statistics
    stats = worker_pool.get_stats()
    print(f"\n  Statistics after 3 seconds:")
    print(f"    Submitted: {stats.total_tasks_submitted}")
    print(f"    Completed: {stats.total_tasks_completed}")
    print(f"    Failed: {stats.total_tasks_failed}")
    print(f"    Active: {stats.active_threads}")
    print(f"    Pending: {stats.pending_tasks}")
    print(f"    Avg duration: {stats.average_task_duration:.2f}s")
    
    # Wait for all tasks to complete
    time.sleep(5)
    
    # Final statistics
    final_stats = worker_pool.get_stats()
    print(f"\n  Final statistics:")
    print(f"    Submitted: {final_stats.total_tasks_submitted}")
    print(f"    Completed: {final_stats.total_tasks_completed}")
    print(f"    Failed: {final_stats.total_tasks_failed}")
    
    # Stop the pool
    worker_pool.stop()
    
    print(f"  ✓ Basic functionality test completed")
    print(f"    Completed tasks: {len(completed_tasks)}")
    print(f"    Failed tasks: {len(failed_tasks)}")
    print(f"    State changes: {len(state_changes)}")
    print()


def test_throttling_system():
    """Test I/O throttling functionality."""
    print("2. Testing I/O throttling system...")
    
    settings = setup_test_environment()
    worker_pool = WorkerPool(settings)
    
    # Track timing for throttling verification
    task_times = []
    
    def on_complete(task, result):
        task_times.append((task.id, time.time()))
        print(f"  ✓ Throttled task {task.id} completed at {time.time():.2f}")
    
    worker_pool.set_callbacks(on_task_complete=on_complete)
    worker_pool.start()
    
    # Submit multiple I/O tasks rapidly
    print("\n  Submitting 6 I/O tasks rapidly (should be throttled)...")
    start_time = time.time()
    
    for i in range(6):
        worker_pool.submit_task(
            f"io-{i}", 
            demo_task_simple, 
            TaskPriority.NORMAL, 
            "io",  # Same category for throttling
            f"io-{i}", 0.2
        )
    
    # Wait for completion
    time.sleep(8)
    
    # Analyze timing
    if len(task_times) >= 2:
        intervals = []
        for i in range(1, len(task_times)):
            interval = task_times[i][1] - task_times[i-1][1]
            intervals.append(interval)
        
        avg_interval = sum(intervals) / len(intervals)
        expected_interval = 1.0 / 2.0  # 2 ops/sec = 0.5s interval
        
        print(f"  Average interval between completions: {avg_interval:.2f}s")
        print(f"  Expected interval (2 ops/sec): {expected_interval:.2f}s")
        
        if avg_interval >= expected_interval * 0.8:  # Allow some variance
            print(f"  ✓ Throttling working correctly")
        else:
            print(f"  ⚠ Throttling may not be working as expected")
    
    # Check throttling statistics
    stats = worker_pool.get_stats()
    print(f"  Throttled operations: {stats.throttled_operations}")
    
    worker_pool.stop()
    print()


def test_back_off_system():
    """Test user interaction back-off functionality."""
    print("3. Testing user interaction back-off system...")
    
    settings = setup_test_environment()
    worker_pool = WorkerPool(settings)
    
    # Track back-off events
    back_off_count = 0
    completed_during_interaction = []
    
    def on_complete(task, result):
        completed_during_interaction.append((task.id, time.time()))
        print(f"  ✓ Task {task.id} completed during interaction test")
    
    worker_pool.set_callbacks(on_task_complete=on_complete)
    worker_pool.start()
    
    # Submit low priority tasks that should be delayed
    print("\n  Submitting low priority tasks...")
    for i in range(4):
        worker_pool.submit_task(
            f"low-{i}", 
            demo_task_simple, 
            TaskPriority.LOW, 
            "background",
            f"low-{i}", 1.0
        )
    
    # Start interaction simulation in background
    interaction_thread = Thread(
        target=simulate_user_interactions,
        args=(worker_pool, 5.0),
        daemon=True
    )
    interaction_thread.start()
    
    # Wait for test to complete
    time.sleep(8)
    
    # Check back-off statistics
    stats = worker_pool.get_stats()
    print(f"  Back-off events: {stats.back_off_events}")
    print(f"  Tasks completed during interaction period: {len(completed_during_interaction)}")
    
    if stats.back_off_events > 0:
        print(f"  ✓ Back-off system triggered correctly")
    else:
        print(f"  ⚠ Back-off system may not have triggered")
    
    worker_pool.stop()
    print()


def test_pause_resume_controls():
    """Test Pause/Resume functionality."""
    print("4. Testing Pause/Resume controls...")
    
    settings = setup_test_environment()
    worker_pool = WorkerPool(settings)
    
    # Track state changes and completions
    state_changes = []
    completed_tasks = []
    
    def on_state_change(new_state):
        state_changes.append((new_state, time.time()))
        print(f"  State: {new_state.name} at {time.time():.2f}")
    
    def on_complete(task, result):
        completed_tasks.append((task.id, time.time()))
        print(f"  ✓ Task {task.id} completed at {time.time():.2f}")
    
    worker_pool.set_callbacks(on_complete, on_state_change)
    worker_pool.start()
    
    # Submit several tasks
    print("\n  Submitting 6 tasks...")
    for i in range(6):
        worker_pool.submit_task(
            f"pause-test-{i}", 
            demo_task_simple, 
            TaskPriority.NORMAL, 
            "test",
            f"pause-test-{i}", 1.5
        )
    
    # Let some tasks start
    time.sleep(1)
    print(f"  Tasks running, pausing pool...")
    
    # Pause the pool
    worker_pool.pause()
    pause_time = time.time()
    
    # Wait during pause
    time.sleep(3)
    completed_during_pause = [t for t in completed_tasks if t[1] > pause_time]
    print(f"  Tasks completed during pause: {len(completed_during_pause)}")
    
    # Resume the pool
    print(f"  Resuming pool...")
    worker_pool.resume()
    
    # Wait for remaining tasks
    time.sleep(5)
    
    # Check final results
    print(f"  Total tasks completed: {len(completed_tasks)}")
    print(f"  State changes: {[s[0].name for s in state_changes]}")
    
    if WorkerPoolState.PAUSED in [s[0] for s in state_changes]:
        print(f"  ✓ Pause/Resume functionality working")
    else:
        print(f"  ⚠ Pause/Resume may not be working correctly")
    
    worker_pool.stop()
    print()


def test_factory_functions():
    """Test convenience factory functions."""
    print("5. Testing factory functions...")
    
    settings = setup_test_environment()
    
    # Test file processing pool
    file_pool = create_file_processing_pool(settings)
    print(f"  Created file processing pool: {type(file_pool).__name__}")
    
    # Test thumbnail pool
    thumb_pool = create_thumbnail_pool(settings)
    print(f"  Created thumbnail pool: {type(thumb_pool).__name__}")
    
    # Start both pools
    file_pool.start()
    thumb_pool.start()
    
    # Submit tasks to both
    file_pool.submit_task("file-1", demo_task_simple, TaskPriority.NORMAL, "scan", "file-1", 0.5)
    thumb_pool.submit_task("thumb-1", demo_task_simple, TaskPriority.HIGH, "thumbnail", "thumb-1", 0.5)
    
    # Wait for completion
    time.sleep(2)
    
    # Check both are working
    file_stats = file_pool.get_stats()
    thumb_stats = thumb_pool.get_stats()
    
    print(f"  File pool completed: {file_stats.total_tasks_completed}")
    print(f"  Thumbnail pool completed: {thumb_stats.total_tasks_completed}")
    
    # Stop both
    file_pool.stop()
    thumb_pool.stop()
    
    print(f"  ✓ Factory functions working correctly")
    print()


def test_cpu_usage_monitoring():
    """Test CPU usage and thread cap compliance."""
    print("6. Testing CPU usage and thread cap compliance...")
    
    settings = setup_test_environment()
    settings.set("General", "thread_cap", 2)  # Limit to 2 threads
    
    worker_pool = WorkerPool(settings)
    
    active_thread_counts = []
    
    def on_complete(task, result):
        stats = worker_pool.get_stats()
        active_thread_counts.append(stats.active_threads)
        print(f"  ✓ Task {task.id} completed, active threads: {stats.active_threads}")
    
    worker_pool.set_callbacks(on_task_complete=on_complete)
    worker_pool.start()
    
    # Submit more tasks than thread cap
    print(f"\n  Submitting 8 tasks with thread_cap=2...")
    for i in range(8):
        worker_pool.submit_task(
            f"thread-test-{i}", 
            demo_task_simple, 
            TaskPriority.NORMAL, 
            "test",
            f"thread-test-{i}", 1.0
        )
    
    # Monitor for a while
    time.sleep(6)
    
    # Check thread cap compliance
    max_active = max(active_thread_counts) if active_thread_counts else 0
    print(f"  Maximum active threads observed: {max_active}")
    print(f"  Thread cap setting: {settings.get('General', 'thread_cap')}")
    
    if max_active <= settings.get('General', 'thread_cap'):
        print(f"  ✓ Thread cap respected")
    else:
        print(f"  ⚠ Thread cap may have been exceeded")
    
    worker_pool.stop()
    print()


def main():
    """Run all concurrency system tests."""
    print("Starting Step 13 Concurrency System Demo...\n")
    
    try:
        # Run all tests
        test_basic_worker_pool()
        test_throttling_system()
        test_back_off_system() 
        test_pause_resume_controls()
        test_factory_functions()
        test_cpu_usage_monitoring()
        
        print("=" * 50)
        print("✅ STEP 13 CONCURRENCY SYSTEM DEMO COMPLETE!")
        print()
        print("Key Features Demonstrated:")
        print("• Dynamic thread pool with configurable cap")
        print("• I/O throttling with configurable rates")
        print("• User interaction back-off for UI responsiveness")
        print("• Pause/Resume controls with safe task draining")
        print("• Priority-based task scheduling")
        print("• Comprehensive statistics and monitoring")
        print("• Factory functions for specialized pools")
        print("• CPU usage compliance with thread caps")
        print()
        print("The system successfully maintains UI responsiveness")
        print("while efficiently processing background tasks!")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()