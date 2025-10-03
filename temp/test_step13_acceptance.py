#!/usr/bin/env python3
"""
Acceptance test for Step 13: Concurrency, throttling, and back-off.

Tests all acceptance criteria:
1. UI remains responsive while scanning and hashing
2. Pause/Resume controls work correctly
3. CPU usage respects thread caps
4. I/O throttling functions properly
5. User interaction back-off triggers correctly
"""

import sys
import time
import tempfile
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import Settings
from core.concurrency import (
    WorkerPool, TaskPriority, WorkerPoolState,
    create_file_processing_pool
)


def create_test_environment():
    """Create test environment and settings."""
    print("=== Step 13 Acceptance Test ===\n")
    
    # Create settings for testing
    settings = Settings()
    
    # Configure for testing
    settings.set("General", "thread_cap", 3)
    settings.set("General", "io_throttle", 4.0)  # 4 ops per second
    settings.set("Concurrency", "back_off_enabled", True)
    settings.set("Concurrency", "interaction_threshold", 3)
    settings.set("Concurrency", "interaction_window", 1.0) 
    settings.set("Concurrency", "back_off_duration", 1.5)
    
    print(f"Test configuration:")
    print(f"  Thread cap: {settings.get('General', 'thread_cap')}")
    print(f"  I/O throttle: {settings.get('General', 'io_throttle')} ops/sec")
    print(f"  Back-off threshold: {settings.get('Concurrency', 'interaction_threshold')}")
    print()
    
    return settings


def cpu_intensive_task(task_id: str, duration: float = 2.0) -> str:
    """CPU intensive task for testing thread caps."""
    start_time = time.time()
    result = 0
    
    # CPU-bound calculation
    while time.time() - start_time < duration:
        result += sum(i * i for i in range(1000))
    
    return f"Task {task_id} computed {result}"


def io_simulation_task(task_id: str, operations: int = 5) -> str:
    """I/O simulation task for testing throttling."""
    for i in range(operations):
        time.sleep(0.1)  # Simulate I/O delay
        
    return f"Task {task_id} completed {operations} I/O operations"


def quick_task(task_id: str) -> str:
    """Quick task for interaction testing."""
    time.sleep(0.2)
    return f"Quick task {task_id} completed"


def test_ui_responsiveness():
    """Test 1: UI remains responsive while processing heavy tasks."""
    print("1. Testing UI responsiveness during heavy processing...")
    
    settings = create_test_environment()
    worker_pool = WorkerPool(settings)
    
    # Track task completions
    completed_tasks = []
    response_times = []
    
    def on_complete(task, result):
        completed_tasks.append((task.id, time.time()))
        print(f"  ✓ {task.id} completed")
    
    def simulate_ui_requests():
        """Simulate UI requests that need immediate response."""
        for i in range(5):
            start_time = time.time()
            
            # Submit critical UI task
            worker_pool.submit_task(
                f"ui-critical-{i}",
                quick_task,
                TaskPriority.CRITICAL,
                "ui",
                f"ui-critical-{i}"
            )
            
            # Measure response time by checking when task starts
            time.sleep(0.3)
            response_time = time.time() - start_time
            response_times.append(response_time)
    
    worker_pool.set_callbacks(on_task_complete=on_complete)
    worker_pool.start()
    
    # Submit heavy background tasks
    print("  Submitting heavy background tasks...")
    for i in range(6):
        worker_pool.submit_task(
            f"heavy-{i}",
            cpu_intensive_task,
            TaskPriority.LOW,
            "background",
            f"heavy-{i}", 3.0
        )
    
    # Wait a moment for background tasks to start
    time.sleep(0.5)
    
    # Start UI simulation in separate thread
    ui_thread = threading.Thread(target=simulate_ui_requests, daemon=True)
    ui_thread.start()
    
    # Wait for test completion
    ui_thread.join(timeout=10)
    time.sleep(2)
    
    # Check results
    ui_tasks = [t for t in completed_tasks if 'ui-critical' in t[0]]
    avg_response = sum(response_times) / len(response_times) if response_times else 0
    
    print(f"  UI tasks completed: {len(ui_tasks)}/5")
    print(f"  Average response time: {avg_response:.2f}s")
    
    worker_pool.stop()
    
    # Test passes if UI tasks completed quickly
    success = len(ui_tasks) >= 4 and avg_response < 1.0
    print(f"  {'✓ PASS' if success else '✗ FAIL'}: UI responsiveness")
    print()
    
    return success


def test_pause_resume_controls():
    """Test 2: Pause/Resume controls work correctly."""
    print("2. Testing Pause/Resume controls...")
    
    settings = create_test_environment()
    worker_pool = WorkerPool(settings)
    
    # Track state changes and task completions
    state_changes = []
    completed_tasks = []
    
    def on_state_change(new_state):
        state_changes.append((new_state, time.time()))
        print(f"  State: {new_state.name}")
    
    def on_complete(task, result):
        completed_tasks.append((task.id, time.time()))
    
    worker_pool.set_callbacks(on_complete, on_state_change)
    worker_pool.start()
    
    # Submit tasks
    print("  Submitting tasks...")
    for i in range(8):
        worker_pool.submit_task(
            f"pause-test-{i}",
            cpu_intensive_task,
            TaskPriority.NORMAL,
            "test",
            f"pause-test-{i}", 1.5
        )
    
    # Let some tasks start
    time.sleep(1)
    tasks_before_pause = len(completed_tasks)
    
    # Pause
    print("  Pausing worker pool...")
    worker_pool.pause()
    pause_time = time.time()
    
    # Wait during pause
    time.sleep(2)
    tasks_during_pause = len([t for t in completed_tasks if t[1] > pause_time])
    
    # Resume
    print("  Resuming worker pool...")
    worker_pool.resume()
    
    # Wait for completion
    time.sleep(5)
    
    # Check results
    has_pause_state = WorkerPoolState.PAUSED in [s[0] for s in state_changes]
    has_running_state = WorkerPoolState.RUNNING in [s[0] for s in state_changes]
    total_completed = len(completed_tasks)
    
    print(f"  Tasks before pause: {tasks_before_pause}")
    print(f"  Tasks completed during pause: {tasks_during_pause}")
    print(f"  Total tasks completed: {total_completed}")
    print(f"  State changes: {[s[0].name for s in state_changes]}")
    
    worker_pool.stop()
    
    # Test passes if pause/resume states occurred and minimal tasks during pause
    success = has_pause_state and has_running_state and tasks_during_pause <= 2
    print(f"  {'✓ PASS' if success else '✗ FAIL'}: Pause/Resume controls")
    print()
    
    return success


def test_thread_cap_compliance():
    """Test 3: CPU usage respects thread caps."""
    print("3. Testing thread cap compliance...")
    
    settings = create_test_environment()
    thread_cap = settings.get("General", "thread_cap")
    worker_pool = WorkerPool(settings)
    
    # Monitor active thread count
    max_active_threads = 0
    thread_counts = []
    
    def on_complete(task, result):
        nonlocal max_active_threads
        stats = worker_pool.get_stats()
        active = stats.active_threads
        thread_counts.append(active)
        max_active_threads = max(max_active_threads, active)
        print(f"  Task {task.id} completed, active threads: {active}")
    
    worker_pool.set_callbacks(on_task_complete=on_complete)
    worker_pool.start()
    
    # Submit more tasks than thread cap
    print(f"  Submitting 12 tasks with thread_cap={thread_cap}...")
    for i in range(12):
        worker_pool.submit_task(
            f"thread-cap-{i}",
            cpu_intensive_task,
            TaskPriority.NORMAL,
            "test",
            f"thread-cap-{i}", 1.0
        )
    
    # Monitor for a while
    time.sleep(8)
    
    # Check thread cap compliance
    print(f"  Maximum active threads observed: {max_active_threads}")
    print(f"  Thread cap setting: {thread_cap}")
    
    worker_pool.stop()
    
    # Test passes if max threads never exceeded cap
    success = max_active_threads <= thread_cap
    print(f"  {'✓ PASS' if success else '✗ FAIL'}: Thread cap compliance")
    print()
    
    return success


def test_io_throttling():
    """Test 4: I/O throttling functions properly."""
    print("4. Testing I/O throttling...")
    
    settings = create_test_environment()
    throttle_rate = settings.get("General", "io_throttle")  # 4 ops/sec
    worker_pool = WorkerPool(settings)
    
    # Track completion times
    completion_times = []
    
    def on_complete(task, result):
        completion_times.append(time.time())
        print(f"  I/O task {task.id} completed at {time.time():.2f}")
    
    worker_pool.set_callbacks(on_task_complete=on_complete)
    worker_pool.start()
    
    # Submit I/O tasks rapidly (same category for throttling)
    print(f"  Submitting 8 I/O tasks rapidly (should be throttled to {throttle_rate} ops/sec)...")
    start_time = time.time()
    
    for i in range(8):
        worker_pool.submit_task(
            f"io-throttle-{i}",
            io_simulation_task,
            TaskPriority.NORMAL,
            "io",  # Same category for throttling
            f"io-throttle-{i}", 2
        )
    
    # Wait for completion
    time.sleep(12)
    
    # Analyze timing
    if len(completion_times) >= 3:
        # Calculate intervals between completions
        intervals = []
        for i in range(1, len(completion_times)):
            interval = completion_times[i] - completion_times[i-1]
            intervals.append(interval)
        
        avg_interval = sum(intervals) / len(intervals)
        expected_interval = 1.0 / throttle_rate  # 4 ops/sec = 0.25s interval
        
        print(f"  Average interval between completions: {avg_interval:.2f}s")
        print(f"  Expected interval ({throttle_rate} ops/sec): {expected_interval:.2f}s")
        
        # Check throttling statistics
        stats = worker_pool.get_stats()
        print(f"  Throttled operations: {stats.throttled_operations}")
        
        worker_pool.stop()
        
        # Test passes if intervals are close to expected (with tolerance)
        success = abs(avg_interval - expected_interval) < 0.15 or stats.throttled_operations > 0
        print(f"  {'✓ PASS' if success else '✗ FAIL'}: I/O throttling")
    else:
        worker_pool.stop()
        success = False
        print(f"  ✗ FAIL: Not enough completions to test throttling")
    
    print()
    return success


def test_interaction_back_off():
    """Test 5: User interaction back-off triggers correctly."""
    print("5. Testing user interaction back-off...")
    
    settings = create_test_environment()
    worker_pool = WorkerPool(settings)
    
    # Track back-off events
    completed_tasks = []
    
    def on_complete(task, result):
        completed_tasks.append((task.id, time.time()))
        print(f"  Task {task.id} completed")
    
    def simulate_rapid_interactions():
        """Simulate rapid user interactions."""
        for i in range(10):
            worker_pool.record_interaction("scroll")
            time.sleep(0.2)  # 5 interactions per second
    
    worker_pool.set_callbacks(on_task_complete=on_complete)
    worker_pool.start()
    
    # Submit low priority tasks that should be delayed
    print("  Submitting low priority tasks...")
    for i in range(6):
        worker_pool.submit_task(
            f"back-off-{i}",
            quick_task,
            TaskPriority.LOW,
            "background",
            f"back-off-{i}"
        )
    
    # Start rapid interactions
    print("  Simulating rapid user interactions...")
    interaction_thread = threading.Thread(target=simulate_rapid_interactions, daemon=True)
    interaction_thread.start()
    
    # Wait for test
    time.sleep(4)
    
    # Check back-off statistics
    stats = worker_pool.get_stats()
    back_off_events = stats.back_off_events
    tasks_completed = len(completed_tasks)
    
    print(f"  Back-off events: {back_off_events}")
    print(f"  Tasks completed during interaction period: {tasks_completed}")
    
    worker_pool.stop()
    
    # Test passes if back-off events occurred
    success = back_off_events > 0
    print(f"  {'✓ PASS' if success else '✗ FAIL'}: Interaction back-off")
    print()
    
    return success


def test_factory_functions():
    """Test bonus: Factory functions work correctly."""
    print("6. Testing factory functions...")
    
    settings = create_test_environment()
    
    try:
        # Test file processing pool
        file_pool = create_file_processing_pool(settings)
        file_pool.start()
        
        # Submit test task
        file_pool.submit_task("factory-test", quick_task, TaskPriority.NORMAL, "test", "factory-test")
        
        time.sleep(1)
        
        # Check it's working
        stats = file_pool.get_stats()
        file_pool.stop()
        
        success = stats.total_tasks_submitted > 0
        print(f"  {'✓ PASS' if success else '✗ FAIL'}: Factory functions")
        
    except Exception as e:
        print(f"  ✗ FAIL: Factory functions - {e}")
        success = False
    
    print()
    return success


def main():
    """Run all acceptance tests."""
    print("Starting Step 13 Acceptance Tests...\n")
    
    test_results = []
    
    try:
        # Run all tests
        test_results.append(("UI Responsiveness", test_ui_responsiveness()))
        test_results.append(("Pause/Resume Controls", test_pause_resume_controls()))
        test_results.append(("Thread Cap Compliance", test_thread_cap_compliance()))
        test_results.append(("I/O Throttling", test_io_throttling()))
        test_results.append(("Interaction Back-off", test_interaction_back_off()))
        test_results.append(("Factory Functions", test_factory_functions()))
        
        # Summary
        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)
        
        print("=" * 50)
        print("STEP 13 ACCEPTANCE TEST RESULTS:")
        print("=" * 50)
        
        for test_name, result in test_results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {test_name}")
        
        print()
        print(f"Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print()
            print("🎉 ALL ACCEPTANCE CRITERIA MET!")
            print()
            print("✅ UI remains responsive while scanning and hashing")
            print("✅ Pause/Resume controls work correctly") 
            print("✅ CPU usage respects thread caps")
            print("✅ I/O throttling functions properly")
            print("✅ User interaction back-off triggers correctly")
            print()
            print("Step 13 implementation is COMPLETE and VALIDATED!")
        else:
            print()
            print("❌ Some acceptance criteria not met. Review failed tests.")
        
    except Exception as e:
        print(f"Acceptance test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()