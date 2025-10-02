"""
Step 13: Concurrency, throttling, and back-off system.

This module provides a worker pool using ThreadPoolExecutor with dynamic thread cap,
I/O throttling, interaction back-off, and Pause/Resume controls for responsive UI.
"""

from __future__ import annotations

import time
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union
from contextlib import contextmanager

try:
    from app.settings import Settings
except ImportError:
    from ..app.settings import Settings


class TaskPriority(Enum):
    """Task priority levels for back-off system."""
    CRITICAL = auto()    # User-requested operations (never deprioritized)
    HIGH = auto()        # UI-responsive operations (thumbnail generation)
    NORMAL = auto()      # Background operations (scanning, hashing)
    LOW = auto()         # Heavy operations (feature extraction, duplicate detection)


class WorkerPoolState(Enum):
    """Worker pool execution states."""
    STOPPED = auto()     # Not running
    RUNNING = auto()     # Normal operation
    PAUSED = auto()      # Temporarily suspended
    DRAINING = auto()    # Completing current tasks, no new tasks accepted


@dataclass
class Task:
    """A task to be executed by the worker pool."""
    id: str
    priority: TaskPriority
    func: Callable[..., Any]
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    category: str = "general"  # For throttling groups
    future: Optional[Future] = None


@dataclass
class WorkerPoolStats:
    """Statistics for worker pool performance monitoring."""
    total_tasks_submitted: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    active_threads: int = 0
    pending_tasks: int = 0
    throttled_operations: int = 0
    back_off_events: int = 0
    state_changes: int = 0
    average_task_duration: float = 0.0
    last_interaction_time: float = 0.0


class InteractionMonitor:
    """Monitors user interactions to trigger back-off behavior."""
    
    def __init__(self):
        self._interaction_times: List[float] = []
        self._lock = threading.Lock()
        self._back_off_threshold = 3  # interactions per second
        self._back_off_window = 1.0   # 1 second window
        self._back_off_duration = 2.0 # 2 seconds back-off
        self._last_back_off = 0.0
        self._total_interactions = 0  # Track total for debugging
    
    def record_interaction(self, interaction_type: str = "general") -> None:
        """Record a user interaction (scroll, hover, click, etc.)."""
        now = time.time()
        
        with self._lock:
            # Remove old interactions outside the window
            cutoff = now - self._back_off_window
            self._interaction_times = [t for t in self._interaction_times if t > cutoff]
            
            # Add current interaction
            self._interaction_times.append(now)
            self._total_interactions += 1
    
    def should_back_off(self) -> bool:
        """Check if we should back off due to rapid interactions."""
        now = time.time()
        
        with self._lock:
            # Clean old interactions
            cutoff = now - self._back_off_window
            self._interaction_times = [t for t in self._interaction_times if t > cutoff]
            
            # Check if we're in a back-off period
            if now - self._last_back_off < self._back_off_duration:
                return True
            
            # Check if interaction rate exceeds threshold
            if len(self._interaction_times) >= self._back_off_threshold:
                self._last_back_off = now
                return True
        
        return False
    
    def configure(self, threshold: int = 3, window: float = 1.0, duration: float = 2.0) -> None:
        """Configure back-off parameters."""
        with self._lock:
            self._back_off_threshold = threshold
            self._back_off_window = window
            self._back_off_duration = duration


class ThrottleController:
    """Controls I/O throttling with configurable delays."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._category_timers: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def should_throttle(self, category: str) -> float:
        """Check if operation should be throttled, returns delay in seconds."""
        io_throttle = self.settings.get("General", "io_throttle", 0.0)
        
        if io_throttle <= 0:
            return 0.0
        
        now = time.time()
        with self._lock:
            last_time = self._category_timers.get(category, 0)
            min_interval = 1.0 / io_throttle  # Convert ops/sec to interval
            
            if now - last_time < min_interval:
                return min_interval - (now - last_time)
            
            return 0.0
    
    def record_operation(self, category: str) -> None:
        """Record that an operation was performed."""
        with self._lock:
            self._category_timers[category] = time.time()


class WorkerPool:
    """
    Advanced worker pool with dynamic thread cap, throttling, and back-off.
    
    Features:
    - Dynamic thread count based on settings
    - I/O throttling with configurable delays
    - User interaction back-off for UI responsiveness
    - Pause/Resume controls with safe task draining
    - Priority-based task scheduling
    - Comprehensive statistics and monitoring
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._state = WorkerPoolState.STOPPED
        self._executor: Optional[ThreadPoolExecutor] = None
        self._state_lock = threading.RLock()
        
        # Task management
        self._task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self._active_tasks: Dict[str, Task] = {}
        self._completed_tasks: Set[str] = set()
        
        # Control systems
        self._interaction_monitor = InteractionMonitor()
        self._throttle_controller = ThrottleController(settings)
        
        # Statistics
        self._stats = WorkerPoolStats()
        self._stats_lock = threading.Lock()
        
        # Worker thread management
        self._worker_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._running_tasks: Dict[str, Task] = {}  # Track actually running tasks
        self._running_lock = threading.Lock()
        
        # Callbacks
        self._on_task_complete: Optional[Callable[[Task, Any], None]] = None
        self._on_task_error: Optional[Callable[[Task, Exception], None]] = None
        self._on_state_change: Optional[Callable[[WorkerPoolState], None]] = None
    
    def start(self) -> None:
        """Start the worker pool."""
        with self._state_lock:
            if self._state != WorkerPoolState.STOPPED:
                return
            
            thread_cap = self.settings.get("General", "thread_cap", 4)
            self._executor = ThreadPoolExecutor(
                max_workers=thread_cap,
                thread_name_prefix="photo-dedupe-worker"
            )
            
            self._shutdown_event.clear()
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                name="worker-pool-manager",
                daemon=True
            )
            self._worker_thread.start()
            
            self._change_state(WorkerPoolState.RUNNING)
    
    def stop(self, timeout: float = 30.0) -> bool:
        """Stop the worker pool, waiting for tasks to complete."""
        with self._state_lock:
            if self._state == WorkerPoolState.STOPPED:
                return True
            
            self._change_state(WorkerPoolState.DRAINING)
            self._shutdown_event.set()
        
        # Wait for worker thread to finish
        if self._worker_thread:
            self._worker_thread.join(timeout=timeout)
            success = not self._worker_thread.is_alive()
        else:
            success = True
        
        # Cleanup
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._executor = None
        
        with self._state_lock:
            self._change_state(WorkerPoolState.STOPPED)
        
        return success
    
    def pause(self) -> None:
        """Pause task execution (current tasks continue, no new tasks start)."""
        with self._state_lock:
            if self._state == WorkerPoolState.RUNNING:
                old_state = self._state
                self._state = WorkerPoolState.PAUSED
                self._change_state_notification(old_state, self._state)
    
    def resume(self) -> None:
        """Resume task execution."""
        with self._state_lock:
            if self._state == WorkerPoolState.PAUSED:
                old_state = self._state
                self._state = WorkerPoolState.RUNNING
                self._change_state_notification(old_state, self._state)
    
    def submit_task(self, 
                    task_id: str,
                    func: Callable[..., Any],
                    priority: TaskPriority = TaskPriority.NORMAL,
                    category: str = "general",
                    *args, **kwargs) -> Optional[str]:
        """
        Submit a task for execution.
        
        Returns task ID if submitted, None if rejected (e.g., during draining).
        """
        with self._state_lock:
            if self._state in (WorkerPoolState.STOPPED, WorkerPoolState.DRAINING):
                return None
            
            task = Task(
                id=task_id,
                priority=priority,
                func=func,
                args=args,
                kwargs=kwargs,
                category=category
            )
            
            # Use negative priority value for priority queue (lower number = higher priority)
            priority_value = -priority.value
            self._task_queue.put((priority_value, time.time(), task))
            
            with self._stats_lock:
                self._stats.total_tasks_submitted += 1
                self._stats.pending_tasks += 1
            
            return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or active task."""
        # Cancel active task
        if task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            if task.future and not task.future.done():
                return task.future.cancel()
        
        # For pending tasks in queue, we can't easily remove them
        # They'll be filtered out during processing
        return False
    
    def get_stats(self) -> WorkerPoolStats:
        """Get current worker pool statistics."""
        with self._stats_lock:
            # Count only tasks that are actually running (not just submitted)
            with self._running_lock:
                actual_active_threads = len(self._running_tasks)
            
            stats = WorkerPoolStats(
                total_tasks_submitted=self._stats.total_tasks_submitted,
                total_tasks_completed=self._stats.total_tasks_completed,
                total_tasks_failed=self._stats.total_tasks_failed,
                active_threads=actual_active_threads,
                pending_tasks=self._task_queue.qsize(),
                throttled_operations=self._stats.throttled_operations,
                back_off_events=self._stats.back_off_events,
                state_changes=self._stats.state_changes,
                average_task_duration=self._stats.average_task_duration,
                last_interaction_time=self._stats.last_interaction_time
            )
        return stats
    
    def record_interaction(self, interaction_type: str = "scroll") -> None:
        """Record user interaction for back-off calculation."""
        self._interaction_monitor.record_interaction(interaction_type)
        with self._stats_lock:
            self._stats.last_interaction_time = time.time()
    
    def configure_back_off(self, threshold: int = 3, window: float = 1.0, duration: float = 2.0) -> None:
        """Configure interaction back-off parameters."""
        self._interaction_monitor.configure(threshold, window, duration)
    
    def set_callbacks(self,
                     on_task_complete: Optional[Callable[[Task, Any], None]] = None,
                     on_task_error: Optional[Callable[[Task, Exception], None]] = None,
                     on_state_change: Optional[Callable[[WorkerPoolState], None]] = None) -> None:
        """Set callback functions for task and state events."""
        self._on_task_complete = on_task_complete
        self._on_task_error = on_task_error
        self._on_state_change = on_state_change
    
    @contextmanager
    def batch_submit(self):
        """Context manager for efficient batch task submission."""
        # Could implement batching optimizations here
        yield self
    
    def _worker_loop(self) -> None:
        """Main worker loop that processes tasks from the queue."""
        while not self._shutdown_event.is_set():
            try:
                # Check if we should process tasks
                with self._state_lock:
                    current_state = self._state
                    
                    if current_state == WorkerPoolState.PAUSED:
                        time.sleep(0.1)
                        continue
                    
                    if current_state == WorkerPoolState.DRAINING:
                        if self._task_queue.empty() and not self._active_tasks:
                            break
                
                # Get next task with timeout
                try:
                    priority_value, submit_time, task = self._task_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # Check pause state again after getting task
                with self._state_lock:
                    if self._state == WorkerPoolState.PAUSED:
                        # Re-queue the task and wait
                        self._task_queue.put((priority_value, submit_time, task))
                        time.sleep(0.1)
                        continue
                
                # Check if we should back off due to user interactions
                if self._should_back_off_task(task):
                    # Re-queue the task with slight delay
                    self._task_queue.put((priority_value, submit_time, task))
                    with self._stats_lock:
                        self._stats.back_off_events += 1
                    time.sleep(0.2)
                    continue
                
                # Apply throttling
                throttle_delay = self._throttle_controller.should_throttle(task.category)
                if throttle_delay > 0:
                    time.sleep(throttle_delay)
                    with self._stats_lock:
                        self._stats.throttled_operations += 1
                
                # Submit task to executor
                if self._executor:
                    task.future = self._executor.submit(self._execute_task, task)
                    self._active_tasks[task.id] = task
                
                # Record operation for throttling
                self._throttle_controller.record_operation(task.category)
                
                with self._stats_lock:
                    self._stats.pending_tasks -= 1
                
            except Exception as e:
                # Log error but continue processing
                print(f"Worker loop error: {e}")
                time.sleep(0.1)
    
    def _execute_task(self, task: Task) -> Any:
        """Execute a single task and handle completion."""
        start_time = time.time()
        
        # Mark task as actually running
        with self._running_lock:
            self._running_tasks[task.id] = task
        
        try:
            # Execute the task function
            result = task.func(*task.args, **task.kwargs)
            
            # Record completion
            duration = time.time() - start_time
            self._record_task_completion(task, duration, None)
            
            # Call completion callback
            if self._on_task_complete:
                try:
                    self._on_task_complete(task, result)
                except Exception as e:
                    print(f"Task completion callback error: {e}")
            
            return result
            
        except Exception as e:
            # Record failure
            duration = time.time() - start_time
            self._record_task_completion(task, duration, e)
            
            # Call error callback
            if self._on_task_error:
                try:
                    self._on_task_error(task, e)
                except Exception as callback_error:
                    print(f"Task error callback error: {callback_error}")
            
            raise
        
        finally:
            # Cleanup tracking
            self._active_tasks.pop(task.id, None)
            with self._running_lock:
                self._running_tasks.pop(task.id, None)
    
    def _should_back_off_task(self, task: Task) -> bool:
        """Check if task should be delayed due to user interactions."""
        # Critical tasks are never delayed
        if task.priority == TaskPriority.CRITICAL:
            return False
        
        # Check interaction monitor
        if self._interaction_monitor.should_back_off():
            # Only delay lower priority tasks during interactions
            return task.priority in (TaskPriority.NORMAL, TaskPriority.LOW)
        
        return False
    
    def _record_task_completion(self, task: Task, duration: float, error: Optional[Exception]) -> None:
        """Record task completion statistics."""
        with self._stats_lock:
            if error:
                self._stats.total_tasks_failed += 1
            else:
                self._stats.total_tasks_completed += 1
            
            # Update average duration
            total_completed = self._stats.total_tasks_completed + self._stats.total_tasks_failed
            if total_completed > 0:
                current_avg = self._stats.average_task_duration
                self._stats.average_task_duration = (
                    (current_avg * (total_completed - 1) + duration) / total_completed
                )
        
        # Track completed tasks
        self._completed_tasks.add(task.id)
    
    def _change_state(self, new_state: WorkerPoolState) -> None:
        """Change worker pool state and notify callbacks."""
        old_state = self._state
        self._state = new_state
        
        with self._stats_lock:
            self._stats.state_changes += 1
        
        if self._on_state_change and old_state != new_state:
            try:
                self._on_state_change(new_state)
            except Exception as e:
                print(f"State change callback error: {e}")
    
    def _change_state_notification(self, old_state: WorkerPoolState, new_state: WorkerPoolState) -> None:
        """Notify state change without updating stats again."""
        with self._stats_lock:
            self._stats.state_changes += 1
        
        if self._on_state_change and old_state != new_state:
            try:
                self._on_state_change(new_state)
            except Exception as e:
                print(f"State change callback error: {e}")
    
    @property
    def state(self) -> WorkerPoolState:
        """Get current worker pool state."""
        return self._state
    
    @property
    def is_running(self) -> bool:
        """Check if worker pool is actively processing tasks."""
        return self._state == WorkerPoolState.RUNNING
    
    @property
    def is_paused(self) -> bool:
        """Check if worker pool is paused."""
        return self._state == WorkerPoolState.PAUSED


# Convenience functions for common task patterns
def create_file_processing_pool(settings: Settings) -> WorkerPool:
    """Create a worker pool optimized for file processing operations."""
    pool = WorkerPool(settings)
    
    # Configure back-off for UI responsiveness
    pool.configure_back_off(
        threshold=3,    # 3 interactions per second
        window=1.0,     # 1 second window
        duration=2.0    # 2 second back-off
    )
    
    return pool


def create_thumbnail_pool(settings: Settings) -> WorkerPool:
    """Create a worker pool optimized for thumbnail generation."""
    pool = WorkerPool(settings)
    
    # More aggressive back-off for thumbnail generation
    pool.configure_back_off(
        threshold=2,    # 2 interactions per second
        window=0.5,     # 0.5 second window
        duration=1.0    # 1 second back-off
    )
    
    return pool


__all__ = [
    "WorkerPool", "Task", "TaskPriority", "WorkerPoolState", "WorkerPoolStats",
    "InteractionMonitor", "ThrottleController",
    "create_file_processing_pool", "create_thumbnail_pool"
]