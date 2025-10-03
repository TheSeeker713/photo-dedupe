"""
Step 28 - Performance Profiling & Thresholds Tuning
Developer panel for monitoring performance and tuning parameters.
"""

import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from contextlib import contextmanager
import statistics


@dataclass
class TimingData:
    """Stores timing information for a specific operation."""
    operation: str
    start_time: float
    end_time: float
    duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        return self.duration * 1000


@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""
    operation: str
    count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def add_timing(self, duration: float):
        """Add a new timing measurement."""
        self.count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.avg_time = self.total_time / self.count
        self.recent_times.append(duration)
    
    @property
    def recent_avg(self) -> float:
        """Average of recent timings."""
        if not self.recent_times:
            return 0.0
        return statistics.mean(self.recent_times)
    
    @property
    def recent_p95(self) -> float:
        """95th percentile of recent timings."""
        if not self.recent_times:
            return 0.0
        sorted_times = sorted(self.recent_times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[min(index, len(sorted_times) - 1)]


class PerformanceProfiler:
    """
    Central performance profiler for the photo deduplication application.
    Tracks timing for scan, decode, hashing, grouping, and UI operations.
    """
    
    def __init__(self):
        self._stats: Dict[str, PerformanceStats] = {}
        self._current_timings: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._enabled = True
        self._listeners: List[Callable[[str, TimingData], None]] = []
    
    def set_enabled(self, enabled: bool):
        """Enable or disable profiling."""
        self._enabled = enabled
    
    def add_listener(self, listener: Callable[[str, TimingData], None]):
        """Add a listener for timing events."""
        self._listeners.append(listener)
    
    def remove_listener(self, listener: Callable[[str, TimingData], None]):
        """Remove a listener for timing events."""
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    @contextmanager
    def time_operation(self, operation: str, **metadata):
        """Context manager for timing operations."""
        if not self._enabled:
            yield
            return
        
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            timing_data = TimingData(
                operation=operation,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                metadata=metadata
            )
            
            self._record_timing(timing_data)
    
    def _record_timing(self, timing_data: TimingData):
        """Record a timing measurement."""
        with self._lock:
            operation = timing_data.operation
            
            if operation not in self._stats:
                self._stats[operation] = PerformanceStats(operation=operation)
            
            self._stats[operation].add_timing(timing_data.duration)
            
            # Notify listeners
            for listener in self._listeners:
                try:
                    listener(operation, timing_data)
                except Exception as e:
                    print(f"Error in performance listener: {e}")
    
    def get_stats(self, operation: str = None) -> Dict[str, PerformanceStats]:
        """Get performance statistics."""
        with self._lock:
            if operation:
                return {operation: self._stats.get(operation)} if operation in self._stats else {}
            return self._stats.copy()
    
    def get_recent_timings(self, operation: str, count: int = 10) -> List[float]:
        """Get recent timings for an operation."""
        with self._lock:
            if operation in self._stats:
                recent = list(self._stats[operation].recent_times)
                return recent[-count:] if len(recent) > count else recent
            return []
    
    def reset_stats(self, operation: str = None):
        """Reset statistics."""
        with self._lock:
            if operation:
                if operation in self._stats:
                    del self._stats[operation]
            else:
                self._stats.clear()
    
    def get_summary(self) -> Dict[str, Dict[str, float]]:
        """Get a summary of all operations."""
        with self._lock:
            summary = {}
            for op, stats in self._stats.items():
                summary[op] = {
                    'count': stats.count,
                    'total_ms': stats.total_time * 1000,
                    'avg_ms': stats.avg_time * 1000,
                    'min_ms': stats.min_time * 1000,
                    'max_ms': stats.max_time * 1000,
                    'recent_avg_ms': stats.recent_avg * 1000,
                    'recent_p95_ms': stats.recent_p95 * 1000,
                }
            return summary


@dataclass
class ThresholdConfig:
    """Configuration for duplicate detection thresholds."""
    perceptual_hash_threshold: int = 5  # Hamming distance for perceptual hash
    orb_match_threshold: float = 0.7    # Ratio threshold for ORB matches
    size_difference_threshold: float = 0.1  # Max size difference ratio
    minimum_matches: int = 10           # Minimum ORB matches required
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'perceptual_hash_threshold': self.perceptual_hash_threshold,
            'orb_match_threshold': self.orb_match_threshold,
            'size_difference_threshold': self.size_difference_threshold,
            'minimum_matches': self.minimum_matches,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThresholdConfig':
        """Create from dictionary."""
        return cls(**data)


class ThresholdTuner:
    """
    System for tuning duplicate detection thresholds and observing their effects.
    Provides real-time feedback on how threshold changes affect group counts.
    """
    
    def __init__(self):
        self.config = ThresholdConfig()
        self._sample_data: List[Dict[str, Any]] = []
        self._current_groups: List[List[int]] = []
        self._listeners: List[Callable[[ThresholdConfig, int], None]] = []
        self._lock = threading.Lock()
    
    def set_sample_data(self, sample_data: List[Dict[str, Any]]):
        """Set the sample data for threshold testing."""
        with self._lock:
            self._sample_data = sample_data.copy()
            self._recompute_groups()
    
    def add_listener(self, listener: Callable[[ThresholdConfig, int], None]):
        """Add a listener for threshold changes."""
        self._listeners.append(listener)
    
    def remove_listener(self, listener: Callable[[ThresholdConfig, int], None]):
        """Remove a listener for threshold changes."""
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def update_threshold(self, threshold_name: str, value: Any):
        """Update a specific threshold value."""
        with self._lock:
            if hasattr(self.config, threshold_name):
                setattr(self.config, threshold_name, value)
                self._recompute_groups()
                self._notify_listeners()
    
    def update_config(self, config: ThresholdConfig):
        """Update the entire configuration."""
        with self._lock:
            self.config = config
            self._recompute_groups()
            self._notify_listeners()
    
    def _recompute_groups(self):
        """Recompute duplicate groups based on current thresholds."""
        if not self._sample_data:
            self._current_groups = []
            return
        
        # Simple grouping algorithm for demonstration
        # In a real implementation, this would use the actual duplicate detection logic
        groups = []
        used_indices = set()
        
        for i, item1 in enumerate(self._sample_data):
            if i in used_indices:
                continue
            
            group = [i]
            used_indices.add(i)
            
            for j, item2 in enumerate(self._sample_data):
                if j <= i or j in used_indices:
                    continue
                
                if self._items_are_similar(item1, item2):
                    group.append(j)
                    used_indices.add(j)
            
            if len(group) > 1:  # Only include actual groups
                groups.append(group)
        
        self._current_groups = groups
    
    def _items_are_similar(self, item1: Dict[str, Any], item2: Dict[str, Any]) -> bool:
        """Check if two items are similar based on current thresholds."""
        # Mock similarity check - replace with actual logic
        # This would normally use perceptual hash, ORB features, etc.
        
        # Check size difference
        size1 = item1.get('size', 0)
        size2 = item2.get('size', 0)
        if size1 > 0 and size2 > 0:
            size_ratio = abs(size1 - size2) / max(size1, size2)
            if size_ratio > self.config.size_difference_threshold:
                return False
        
        # Check perceptual hash (mock)
        hash1 = item1.get('perceptual_hash', '')
        hash2 = item2.get('perceptual_hash', '')
        if hash1 and hash2:
            # Mock hamming distance calculation
            hamming_distance = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
            if hamming_distance > self.config.perceptual_hash_threshold:
                return False
        
        # If we get here, items are considered similar
        return True
    
    def _notify_listeners(self):
        """Notify listeners of threshold changes."""
        group_count = len(self._current_groups)
        for listener in self._listeners:
            try:
                listener(self.config, group_count)
            except Exception as e:
                print(f"Error in threshold listener: {e}")
    
    def get_current_groups(self) -> List[List[int]]:
        """Get current duplicate groups."""
        with self._lock:
            return self._current_groups.copy()
    
    def get_group_count(self) -> int:
        """Get current number of duplicate groups."""
        with self._lock:
            return len(self._current_groups)
    
    def get_total_duplicates(self) -> int:
        """Get total number of duplicate items."""
        with self._lock:
            return sum(len(group) for group in self._current_groups)


# Global instances
_profiler = PerformanceProfiler()
_tuner = ThresholdTuner()


def get_profiler() -> PerformanceProfiler:
    """Get the global performance profiler."""
    return _profiler


def get_threshold_tuner() -> ThresholdTuner:
    """Get the global threshold tuner."""
    return _tuner


# Convenience functions for common operations
def time_scan_operation(metadata=None):
    """Time a scan operation."""
    return _profiler.time_operation('scan', **(metadata or {}))


def time_decode_operation(metadata=None):
    """Time a decode operation."""
    return _profiler.time_operation('decode', **(metadata or {}))


def time_hashing_operation(metadata=None):
    """Time a hashing operation."""
    return _profiler.time_operation('hashing', **(metadata or {}))


def time_grouping_operation(metadata=None):
    """Time a grouping operation."""
    return _profiler.time_operation('grouping', **(metadata or {}))


def time_ui_paint_operation(metadata=None):
    """Time a UI paint operation."""
    return _profiler.time_operation('ui_paint', **(metadata or {}))