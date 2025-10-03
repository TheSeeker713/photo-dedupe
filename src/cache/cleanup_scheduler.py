#!/usr/bin/env python3
"""
Step 20: Cache Cleanup Scheduler
Automated cache management with multiple triggers and comprehensive diagnostics.
"""

import os
import sys
import time
import json
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Tuple, List
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from PySide6.QtCore import QObject, QTimer, Signal, QThread, QMutex, QMutexLocker
    from PySide6.QtWidgets import QApplication
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    # Fallback classes
    class QObject: pass
    class QTimer: pass
    def Signal(*args): return lambda x: x
    class QThread: pass
    class QMutex: pass
    class QMutexLocker: pass

# Add src to path for imports
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.settings import Settings
except ImportError:
    Settings = None

class CleanupTrigger(Enum):
    """Types of cleanup triggers."""
    APP_START = "app_start"
    PERIODIC_IDLE = "periodic_idle"
    SIZE_CAP_BREACH = "size_cap_breach"
    MANUAL = "manual"

class CleanupMode(Enum):
    """Cleanup operation modes."""
    FAST_SWEEP = "fast_sweep"           # Quick cleanup of obviously old files
    FULL_SWEEP = "full_sweep"           # Complete cache analysis and cleanup
    SIZE_PURGE = "size_purge"           # Aggressive cleanup to reach target size

@dataclass
class CacheStats:
    """Cache statistics and diagnostics."""
    total_files: int = 0
    total_size_mb: float = 0.0
    reclaimable_files: int = 0
    reclaimable_size_mb: float = 0.0
    oldest_file_date: Optional[datetime] = None
    newest_file_date: Optional[datetime] = None
    last_cleanup_date: Optional[datetime] = None
    last_cleanup_trigger: Optional[str] = None
    cleanup_count: int = 0
    cache_hit_rate: float = 0.0
    fragmentation_level: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Convert datetime objects to strings
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat() if value else None
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheStats':
        """Create from dictionary."""
        # Convert string dates back to datetime objects
        for key in ['oldest_file_date', 'newest_file_date', 'last_cleanup_date']:
            if data.get(key):
                try:
                    data[key] = datetime.fromisoformat(data[key])
                except:
                    data[key] = None
        
        return cls(**data)

class CacheAnalyzer:
    """Analyzes cache directory for statistics and cleanup opportunities."""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.stats = CacheStats()
    
    def analyze_cache(self, quick_mode: bool = False) -> CacheStats:
        """Analyze cache directory and return comprehensive statistics."""
        if not self.cache_dir.exists():
            return CacheStats()
        
        stats = CacheStats()
        now = datetime.now()
        
        try:
            files = []
            total_size = 0
            reclaimable_size = 0
            reclaimable_count = 0
            
            # Collect file information
            for file_path in self.cache_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                
                try:
                    file_stat = file_path.stat()
                    file_size = file_stat.st_size
                    file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
                    
                    files.append({
                        'path': file_path,
                        'size': file_size,
                        'mtime': file_mtime,
                        'age_days': (now - file_mtime).days
                    })
                    
                    total_size += file_size
                    
                    # Quick mode: basic age-based reclaimable detection
                    if quick_mode:
                        if (now - file_mtime).days > 7:  # Files older than 7 days
                            reclaimable_size += file_size
                            reclaimable_count += 1
                    
                except (OSError, PermissionError):
                    continue
            
            # Calculate comprehensive statistics
            stats.total_files = len(files)
            stats.total_size_mb = total_size / (1024 * 1024)
            
            if files:
                file_times = [f['mtime'] for f in files]
                stats.oldest_file_date = min(file_times)
                stats.newest_file_date = max(file_times)
                
                if not quick_mode:
                    # Advanced reclaimable analysis
                    stats.reclaimable_files, stats.reclaimable_size_mb = self._calculate_reclaimable(files, now)
                    stats.fragmentation_level = self._calculate_fragmentation(files)
                else:
                    stats.reclaimable_files = reclaimable_count
                    stats.reclaimable_size_mb = reclaimable_size / (1024 * 1024)
            
            self.stats = stats
            return stats
            
        except Exception as e:
            print(f"Error analyzing cache: {e}")
            return CacheStats()
    
    def _calculate_reclaimable(self, files: List[Dict], now: datetime) -> Tuple[int, float]:
        """Calculate reclaimable files using advanced heuristics."""
        reclaimable_count = 0
        reclaimable_size = 0
        
        # Heuristics for reclaimable files:
        # 1. Files older than 30 days
        # 2. Duplicate thumbnails with same name pattern
        # 3. Temporary files that weren't cleaned up
        # 4. Files accessed less frequently
        
        file_patterns = {}
        
        for file_info in files:
            file_path = file_info['path']
            age_days = file_info['age_days']
            size = file_info['size']
            
            # Age-based cleanup
            if age_days > 30:
                reclaimable_count += 1
                reclaimable_size += size
                continue
            
            # Pattern-based duplicate detection
            file_pattern = self._get_file_pattern(file_path)
            if file_pattern in file_patterns:
                # Keep the newest, mark older as reclaimable
                existing_file = file_patterns[file_pattern]
                if file_info['mtime'] > existing_file['mtime']:
                    # Current file is newer, mark existing as reclaimable
                    reclaimable_count += 1
                    reclaimable_size += existing_file['size']
                    file_patterns[file_pattern] = file_info
                else:
                    # Existing file is newer, mark current as reclaimable
                    reclaimable_count += 1
                    reclaimable_size += size
            else:
                file_patterns[file_pattern] = file_info
            
            # Temporary file cleanup
            if self._is_temporary_file(file_path):
                if age_days > 1:  # Temp files older than 1 day
                    reclaimable_count += 1
                    reclaimable_size += size
        
        return reclaimable_count, reclaimable_size / (1024 * 1024)
    
    def _get_file_pattern(self, file_path: Path) -> str:
        """Extract pattern from file path for duplicate detection."""
        name = file_path.name
        # Remove hash suffixes and timestamps
        import re
        pattern = re.sub(r'_[a-f0-9]{8,}', '_HASH', name)
        pattern = re.sub(r'_\d{8}_\d{6}', '_TIMESTAMP', pattern)
        return pattern
    
    def _is_temporary_file(self, file_path: Path) -> bool:
        """Check if file appears to be temporary."""
        name = file_path.name.lower()
        temp_indicators = ['.tmp', '.temp', '_temp', '.partial', '.download']
        return any(indicator in name for indicator in temp_indicators)
    
    def _calculate_fragmentation(self, files: List[Dict]) -> float:
        """Calculate cache fragmentation level (0.0 = optimal, 1.0 = highly fragmented)."""
        if len(files) < 10:
            return 0.0
        
        # Simple fragmentation metric based on:
        # 1. Age distribution spread
        # 2. Size distribution spread
        # 3. Directory depth variance
        
        ages = [f['age_days'] for f in files]
        sizes = [f['size'] for f in files]
        
        age_variance = self._calculate_variance(ages)
        size_variance = self._calculate_variance(sizes)
        
        # Normalize and combine metrics (simplified)
        age_frag = min(age_variance / 100, 1.0)  # Normalize age variance
        size_frag = min(size_variance / (1024 * 1024), 1.0)  # Normalize size variance
        
        return (age_frag + size_frag) / 2
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values."""
        if not values:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance

class CacheCleanupWorker(QThread):
    """Background worker for cache cleanup operations."""
    
    progress_updated = Signal(int, str)  # progress percentage, status message
    cleanup_completed = Signal(bool, str, dict)  # success, message, stats
    
    def __init__(self, cache_dir: Path, mode: CleanupMode, target_size_mb: Optional[float] = None):
        super().__init__()
        self.cache_dir = cache_dir
        self.mode = mode
        self.target_size_mb = target_size_mb
        self.cancelled = False
        self.mutex = QMutex()
    
    def cancel(self):
        """Cancel the cleanup operation."""
        with QMutexLocker(self.mutex):
            self.cancelled = True
    
    def run(self):
        """Execute the cleanup operation."""
        try:
            if self.mode == CleanupMode.FAST_SWEEP:
                self._fast_sweep()
            elif self.mode == CleanupMode.FULL_SWEEP:
                self._full_sweep()
            elif self.mode == CleanupMode.SIZE_PURGE:
                self._size_purge()
            
        except Exception as e:
            self.cleanup_completed.emit(False, f"Cleanup failed: {str(e)}", {})
    
    def _fast_sweep(self):
        """Quick cleanup of obviously old files."""
        self.progress_updated.emit(0, "Starting fast sweep...")
        
        if not self.cache_dir.exists():
            self.cleanup_completed.emit(True, "Cache directory doesn't exist", {})
            return
        
        deleted_files = 0
        deleted_size = 0
        total_files = 0
        
        # Count files first
        all_files = list(self.cache_dir.rglob("*"))
        file_list = [f for f in all_files if f.is_file()]
        total_files = len(file_list)
        
        if total_files == 0:
            self.cleanup_completed.emit(True, "Cache is empty", {})
            return
        
        now = datetime.now()
        
        for i, file_path in enumerate(file_list):
            if self.cancelled:
                break
            
            try:
                file_stat = file_path.stat()
                file_age = now - datetime.fromtimestamp(file_stat.st_mtime)
                
                # Fast sweep: remove files older than 7 days
                if file_age.days > 7:
                    file_size = file_stat.st_size
                    file_path.unlink()
                    deleted_files += 1
                    deleted_size += file_size
                
                progress = int((i + 1) / total_files * 100)
                self.progress_updated.emit(progress, f"Processed {i + 1}/{total_files} files...")
                
            except (OSError, PermissionError):
                continue
        
        # Clean up empty directories
        self._cleanup_empty_dirs()
        
        stats = {
            'deleted_files': deleted_files,
            'deleted_size_mb': deleted_size / (1024 * 1024),
            'processed_files': total_files
        }
        
        message = f"Fast sweep complete: {deleted_files} files removed ({deleted_size / (1024 * 1024):.1f} MB)"
        self.cleanup_completed.emit(True, message, stats)
    
    def _full_sweep(self):
        """Complete cache analysis and cleanup."""
        self.progress_updated.emit(0, "Analyzing cache...")
        
        analyzer = CacheAnalyzer(self.cache_dir)
        cache_stats = analyzer.analyze_cache(quick_mode=False)
        
        self.progress_updated.emit(25, "Identifying reclaimable files...")
        
        # Implement comprehensive cleanup logic
        deleted_files = 0
        deleted_size = 0
        
        if not self.cache_dir.exists():
            self.cleanup_completed.emit(True, "Cache directory doesn't exist", {})
            return
        
        files_to_process = list(self.cache_dir.rglob("*"))
        file_list = [f for f in files_to_process if f.is_file()]
        
        now = datetime.now()
        
        for i, file_path in enumerate(file_list):
            if self.cancelled:
                break
            
            try:
                file_stat = file_path.stat()
                file_age = now - datetime.fromtimestamp(file_stat.st_mtime)
                should_delete = False
                
                # Full sweep criteria:
                # 1. Files older than 30 days
                # 2. Temporary files older than 1 day
                # 3. Zero-byte files
                # 4. Files with obvious error patterns
                
                if file_age.days > 30:
                    should_delete = True
                elif file_stat.st_size == 0:
                    should_delete = True
                elif self._is_error_file(file_path):
                    should_delete = True
                elif self._is_temporary_file(file_path) and file_age.days > 1:
                    should_delete = True
                
                if should_delete:
                    file_size = file_stat.st_size
                    file_path.unlink()
                    deleted_files += 1
                    deleted_size += file_size
                
                progress = 25 + int((i + 1) / len(file_list) * 65)
                self.progress_updated.emit(progress, f"Cleaning {i + 1}/{len(file_list)} files...")
                
            except (OSError, PermissionError):
                continue
        
        self.progress_updated.emit(90, "Cleaning up empty directories...")
        self._cleanup_empty_dirs()
        
        stats = {
            'deleted_files': deleted_files,
            'deleted_size_mb': deleted_size / (1024 * 1024),
            'processed_files': len(file_list),
            'cache_stats': cache_stats.to_dict()
        }
        
        message = f"Full sweep complete: {deleted_files} files removed ({deleted_size / (1024 * 1024):.1f} MB)"
        self.cleanup_completed.emit(True, message, stats)
    
    def _size_purge(self):
        """Aggressive cleanup to reach target size."""
        if not self.target_size_mb:
            self.cleanup_completed.emit(False, "No target size specified for purge", {})
            return
        
        self.progress_updated.emit(0, f"Purging cache to {self.target_size_mb:.1f} MB...")
        
        analyzer = CacheAnalyzer(self.cache_dir)
        current_stats = analyzer.analyze_cache(quick_mode=True)
        
        if current_stats.total_size_mb <= self.target_size_mb:
            self.cleanup_completed.emit(True, "Cache size already within target", {})
            return
        
        # Calculate how much we need to delete
        size_to_delete_mb = current_stats.total_size_mb - self.target_size_mb
        
        self.progress_updated.emit(20, "Collecting file information...")
        
        # Collect all files with metadata
        files_info = []
        for file_path in self.cache_dir.rglob("*"):
            if not file_path.is_file():
                continue
            
            try:
                file_stat = file_path.stat()
                files_info.append({
                    'path': file_path,
                    'size': file_stat.st_size,
                    'mtime': datetime.fromtimestamp(file_stat.st_mtime),
                    'age_days': (datetime.now() - datetime.fromtimestamp(file_stat.st_mtime)).days
                })
            except (OSError, PermissionError):
                continue
        
        # Sort by deletion priority (oldest first, then largest)
        files_info.sort(key=lambda x: (x['age_days'], -x['size']), reverse=True)
        
        deleted_files = 0
        deleted_size = 0
        target_bytes = size_to_delete_mb * 1024 * 1024
        
        self.progress_updated.emit(40, "Deleting files to reach target size...")
        
        for i, file_info in enumerate(files_info):
            if self.cancelled or deleted_size >= target_bytes:
                break
            
            try:
                file_info['path'].unlink()
                deleted_files += 1
                deleted_size += file_info['size']
                
                progress = 40 + int((deleted_size / target_bytes) * 50)
                progress = min(progress, 90)
                self.progress_updated.emit(progress, 
                    f"Deleted {deleted_files} files ({deleted_size / (1024 * 1024):.1f} MB)...")
                
            except (OSError, PermissionError):
                continue
        
        self.progress_updated.emit(95, "Cleaning up empty directories...")
        self._cleanup_empty_dirs()
        
        stats = {
            'deleted_files': deleted_files,
            'deleted_size_mb': deleted_size / (1024 * 1024),
            'target_size_mb': self.target_size_mb,
            'final_size_mb': current_stats.total_size_mb - (deleted_size / (1024 * 1024))
        }
        
        message = f"Size purge complete: {deleted_files} files removed ({deleted_size / (1024 * 1024):.1f} MB)"
        self.cleanup_completed.emit(True, message, stats)
    
    def _cleanup_empty_dirs(self):
        """Remove empty directories."""
        try:
            for dir_path in sorted(self.cache_dir.rglob("*"), reverse=True):
                if dir_path.is_dir() and dir_path != self.cache_dir:
                    try:
                        if not any(dir_path.iterdir()):
                            dir_path.rmdir()
                    except OSError:
                        pass
        except Exception:
            pass
    
    def _is_error_file(self, file_path: Path) -> bool:
        """Check if file appears to be an error or corruption artifact."""
        name = file_path.name.lower()
        error_indicators = ['.error', '.corrupt', '.failed', '.retry']
        return any(indicator in name for indicator in error_indicators)
    
    def _is_temporary_file(self, file_path: Path) -> bool:
        """Check if file appears to be temporary."""
        name = file_path.name.lower()
        temp_indicators = ['.tmp', '.temp', '_temp', '.partial', '.download']
        return any(indicator in name for indicator in temp_indicators)

class IdleDetector(QObject):
    """Detects application idle state for periodic cleanup triggers."""
    
    idle_detected = Signal()
    
    def __init__(self, idle_threshold_minutes: int = 10):
        super().__init__()
        self.idle_threshold_minutes = idle_threshold_minutes
        self.last_activity = datetime.now()
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._check_idle)
        self.check_timer.start(60000)  # Check every minute
    
    def record_activity(self):
        """Record user activity to reset idle timer."""
        self.last_activity = datetime.now()
    
    def _check_idle(self):
        """Check if application has been idle long enough."""
        idle_time = datetime.now() - self.last_activity
        if idle_time.total_seconds() >= (self.idle_threshold_minutes * 60):
            self.idle_detected.emit()
            # Reset to prevent immediate re-triggering
            self.last_activity = datetime.now()

class CacheCleanupScheduler(QObject):
    """Main cache cleanup scheduler with multiple triggers and diagnostics."""
    
    cleanup_started = Signal(str, str)  # trigger, mode
    cleanup_progress = Signal(int, str)  # progress, message
    cleanup_completed = Signal(bool, str, dict)  # success, message, stats
    stats_updated = Signal(dict)  # updated cache statistics
    
    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings or Settings() if Settings else None
        
        # Configuration
        self.cache_dir = self._get_cache_dir()
        self.size_cap_mb = 1024  # Default 1GB cache cap
        self.purge_target_percentage = 80  # Purge to 80% of cap when breached
        self.idle_threshold_minutes = 10
        
        # State tracking
        self.current_stats = CacheStats()
        self.stats_file = self.cache_dir / "cache_stats.json"
        self.cleanup_worker = None
        self.last_idle_cleanup = datetime.now() - timedelta(hours=1)  # Allow initial cleanup
        
        # Timers and detectors
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(30000)  # Update stats every 30 seconds
        
        self.idle_detector = IdleDetector(self.idle_threshold_minutes)
        self.idle_detector.idle_detected.connect(self._on_idle_detected)
        
        # Load existing stats
        self._load_stats()
        
        # Perform startup cleanup
        QTimer.singleShot(5000, self._startup_cleanup)  # 5 second delay
    
    def _get_cache_dir(self) -> Path:
        """Get cache directory from settings or use default."""
        if self.settings:
            cache_dir_str = self.settings.get("Cache", "cache_dir", "")
            if cache_dir_str:
                return Path(cache_dir_str)
        
        # Default cache directory
        if sys.platform == "win32":
            cache_root = Path.home() / "AppData" / "Local" / "PhotoDedupe" / "cache"
        else:
            cache_root = Path.home() / ".cache" / "photo-dedupe"
        
        cache_root.mkdir(parents=True, exist_ok=True)
        return cache_root
    
    def record_user_activity(self):
        """Record user activity for idle detection."""
        self.idle_detector.record_activity()
    
    def get_current_stats(self) -> CacheStats:
        """Get current cache statistics."""
        return self.current_stats
    
    def get_diagnostics_card_data(self) -> Dict[str, Any]:
        """Get data for diagnostics card display."""
        stats = self.current_stats
        
        return {
            'current_size_mb': stats.total_size_mb,
            'current_files': stats.total_files,
            'size_cap_mb': self.size_cap_mb,
            'usage_percentage': (stats.total_size_mb / self.size_cap_mb * 100) if self.size_cap_mb > 0 else 0,
            'reclaimable_size_mb': stats.reclaimable_size_mb,
            'reclaimable_files': stats.reclaimable_files,
            'last_cleanup_date': stats.last_cleanup_date,
            'last_cleanup_trigger': stats.last_cleanup_trigger,
            'cleanup_count': stats.cleanup_count,
            'fragmentation_level': stats.fragmentation_level,
            'cache_hit_rate': stats.cache_hit_rate,
            'oldest_file_age_days': (datetime.now() - stats.oldest_file_date).days if stats.oldest_file_date else 0,
            'is_size_cap_breached': stats.total_size_mb > self.size_cap_mb,
            'recommended_action': self._get_recommended_action(stats)
        }
    
    def trigger_manual_cleanup(self, mode: CleanupMode = CleanupMode.FULL_SWEEP):
        """Manually trigger cache cleanup."""
        self._start_cleanup(CleanupTrigger.MANUAL, mode)
    
    def force_size_purge(self):
        """Force immediate size purge to target."""
        target_size = self.size_cap_mb * (self.purge_target_percentage / 100)
        self._start_cleanup(CleanupTrigger.SIZE_CAP_BREACH, CleanupMode.SIZE_PURGE, target_size)
    
    def update_settings(self, new_size_cap_mb: float):
        """Update cache settings."""
        old_cap = self.size_cap_mb
        self.size_cap_mb = new_size_cap_mb
        
        # Check if we need immediate purge
        if self.current_stats.total_size_mb > new_size_cap_mb:
            print(f"Cache size ({self.current_stats.total_size_mb:.1f} MB) exceeds new cap ({new_size_cap_mb:.1f} MB)")
            self.force_size_purge()
    
    def _startup_cleanup(self):
        """Perform fast cleanup on application startup."""
        print("🧹 Performing startup cache cleanup...")
        self._start_cleanup(CleanupTrigger.APP_START, CleanupMode.FAST_SWEEP)
    
    def _on_idle_detected(self):
        """Handle idle detection for periodic cleanup."""
        # Prevent too frequent idle cleanups
        time_since_last = datetime.now() - self.last_idle_cleanup
        if time_since_last.total_seconds() < (self.idle_threshold_minutes * 60):
            return
        
        print(f"🏃‍♂️ Idle detected after {self.idle_threshold_minutes} minutes - triggering cleanup")
        self.last_idle_cleanup = datetime.now()
        self._start_cleanup(CleanupTrigger.PERIODIC_IDLE, CleanupMode.FULL_SWEEP)
    
    def _update_stats(self):
        """Update cache statistics."""
        if self.cleanup_worker and self.cleanup_worker.isRunning():
            return  # Don't update stats during cleanup
        
        analyzer = CacheAnalyzer(self.cache_dir)
        self.current_stats = analyzer.analyze_cache(quick_mode=True)
        
        # Check for size cap breach
        if self.current_stats.total_size_mb > self.size_cap_mb:
            print(f"⚠️ Cache size cap breached: {self.current_stats.total_size_mb:.1f} MB > {self.size_cap_mb:.1f} MB")
            target_size = self.size_cap_mb * (self.purge_target_percentage / 100)
            self._start_cleanup(CleanupTrigger.SIZE_CAP_BREACH, CleanupMode.SIZE_PURGE, target_size)
        
        self.stats_updated.emit(self.get_diagnostics_card_data())
        self._save_stats()
    
    def _start_cleanup(self, trigger: CleanupTrigger, mode: CleanupMode, target_size_mb: Optional[float] = None):
        """Start a cleanup operation."""
        if self.cleanup_worker and self.cleanup_worker.isRunning():
            print("Cleanup already in progress, skipping...")
            return
        
        print(f"🚀 Starting cleanup: {trigger.value} -> {mode.value}")
        
        # Store current trigger for stats
        self._current_trigger = trigger
        
        self.cleanup_worker = CacheCleanupWorker(self.cache_dir, mode, target_size_mb)
        self.cleanup_worker.progress_updated.connect(self.cleanup_progress.emit)
        self.cleanup_worker.cleanup_completed.connect(self._on_cleanup_completed)
        
        self.cleanup_started.emit(trigger.value, mode.value)
        self.cleanup_worker.start()
    
    def _on_cleanup_completed(self, success: bool, message: str, stats: Dict[str, Any]):
        """Handle cleanup completion."""
        print(f"✅ Cleanup completed: {message}")
        
        # Update our stats
        self.current_stats.last_cleanup_date = datetime.now()
        self.current_stats.cleanup_count += 1
        if hasattr(self, '_current_trigger'):
            self.current_stats.last_cleanup_trigger = self._current_trigger.value
        
        self.cleanup_completed.emit(success, message, stats)
        
        # Save updated stats
        self._save_stats()
        
        # Force stats update
        QTimer.singleShot(1000, self._update_stats)
    
    def _get_recommended_action(self, stats: CacheStats) -> str:
        """Get recommended action based on current stats."""
        if stats.total_size_mb > self.size_cap_mb:
            return "Immediate purge recommended"
        elif stats.reclaimable_size_mb > 100:  # More than 100MB reclaimable
            return "Cleanup recommended"
        elif stats.fragmentation_level > 0.7:
            return "Defragmentation recommended"
        elif not stats.last_cleanup_date or (datetime.now() - stats.last_cleanup_date).days > 7:
            return "Regular maintenance due"
        else:
            return "Cache healthy"
    
    def _save_stats(self):
        """Save cache statistics to file."""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.current_stats.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving cache stats: {e}")
    
    def _load_stats(self):
        """Load cache statistics from file."""
        try:
            if self.stats_file.exists():
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    self.current_stats = CacheStats.from_dict(data)
        except Exception as e:
            print(f"Error loading cache stats: {e}")
            self.current_stats = CacheStats()

def create_cache_scheduler(settings=None):
    """Create and configure a cache cleanup scheduler."""
    if not PYSIDE6_AVAILABLE:
        print("Warning: PySide6 not available, cache scheduler will have limited functionality")
        return None
    
    scheduler = CacheCleanupScheduler(settings)
    return scheduler

if __name__ == "__main__":
    """Demo the cache cleanup scheduler."""
    print("🧹 Cache Cleanup Scheduler Demo")
    print("=" * 40)
    
    if not PYSIDE6_AVAILABLE:
        print("❌ PySide6 not available - demo cannot run")
        sys.exit(1)
    
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    
    # Create scheduler
    scheduler = create_cache_scheduler()
    
    def on_cleanup_started(trigger, mode):
        print(f"🚀 Cleanup started: {trigger} -> {mode}")
    
    def on_cleanup_progress(progress, message):
        print(f"📊 Progress: {progress}% - {message}")
    
    def on_cleanup_completed(success, message, stats):
        print(f"✅ Cleanup completed: {message}")
        print(f"📈 Stats: {stats}")
    
    def on_stats_updated(diagnostics):
        print(f"📊 Cache stats updated:")
        print(f"   Size: {diagnostics['current_size_mb']:.1f} MB ({diagnostics['current_files']} files)")
        print(f"   Usage: {diagnostics['usage_percentage']:.1f}% of {diagnostics['size_cap_mb']:.1f} MB cap")
        print(f"   Reclaimable: {diagnostics['reclaimable_size_mb']:.1f} MB ({diagnostics['reclaimable_files']} files)")
        print(f"   Recommendation: {diagnostics['recommended_action']}")
        print()
    
    # Connect signals
    scheduler.cleanup_started.connect(on_cleanup_started)
    scheduler.cleanup_progress.connect(on_cleanup_progress)
    scheduler.cleanup_completed.connect(on_cleanup_completed)
    scheduler.stats_updated.connect(on_stats_updated)
    
    print("🎯 Scheduler created and monitoring started")
    print("💡 Try manually triggering cleanup:")
    print("   scheduler.trigger_manual_cleanup()")
    print("   scheduler.force_size_purge()")
    
    # Run for a short demo
    QTimer.singleShot(10000, app.quit)  # Exit after 10 seconds
    app.exec()