"""
Step 14: Logging and diagnostics system.

This module provides comprehensive logging with loguru and real-time diagnostics
for monitoring system health, performance, and data statistics.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta

try:
    from loguru import logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False
    logger = None

try:
    from app.settings import Settings
    from store.db import DatabaseManager
    from store.cache import CacheManager
except ImportError:
    # Handle import issues gracefully for type checking
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from app.settings import Settings
        from store.db import DatabaseManager
        from store.cache import CacheManager
    else:
        Settings = None
        DatabaseManager = None
        CacheManager = None


@dataclass
class SystemStats:
    """System statistics for diagnostics."""
    total_files: int = 0
    total_groups: int = 0
    total_duplicates: int = 0
    safe_duplicates: int = 0
    estimated_reclaimable_mb: float = 0.0
    cache_size_mb: float = 0.0
    last_purge_time: Optional[datetime] = None
    last_scan_time: Optional[datetime] = None
    database_size_mb: float = 0.0
    thumbnail_count: int = 0
    feature_count: int = 0


@dataclass
class PerformanceMetrics:
    """Performance metrics for diagnostics."""
    files_per_second_scan: float = 0.0
    thumbnails_per_second: float = 0.0
    hashes_per_second: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    disk_io_mb_per_second: float = 0.0
    active_threads: int = 0
    queue_depth: int = 0


@dataclass
class DiagnosticsData:
    """Complete diagnostics information."""
    system_stats: SystemStats = field(default_factory=SystemStats)
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    recent_errors: List[str] = field(default_factory=list)
    system_health: str = "unknown"
    uptime_seconds: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


class LoggingManager:
    """Manages application logging with loguru."""
    
    def __init__(self, settings: Optional[Settings] = None, log_dir: Optional[Path] = None):
        self.settings = settings
        self.log_dir = log_dir or Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        self._configured = False
        self._start_time = time.time()
        
        if not LOGURU_AVAILABLE:
            print("Warning: loguru not available, using basic logging")
            return
        
        self._configure_logging()
    
    def _configure_logging(self) -> None:
        """Configure loguru logging with rotation and levels."""
        if not LOGURU_AVAILABLE or self._configured:
            return
        
        # Remove default handler
        logger.remove()
        
        # Console handler with INFO level
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True
        )
        
        # File handler with DEBUG level and rotation
        log_file = self.log_dir / "photo_dedupe.log"
        logger.add(
            log_file,
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="30 days",
            compression="zip",
            encoding="utf-8"
        )
        
        # Error-only file with immediate rotation
        error_log_file = self.log_dir / "errors.log"
        logger.add(
            error_log_file,
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="5 MB",
            retention="60 days",
            compression="zip",
            encoding="utf-8"
        )
        
        # Performance log for timing and metrics
        perf_log_file = self.log_dir / "performance.log"
        logger.add(
            perf_log_file,
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
            rotation="20 MB",
            retention="14 days",
            filter=lambda record: "performance" in record["extra"],
            encoding="utf-8"
        )
        
        self._configured = True
        logger.info("Logging system initialized", log_dir=str(self.log_dir))
    
    def log_error_with_context(self, message: str, error: Exception, file_path: Optional[Path] = None, **kwargs) -> None:
        """Log error with file path context and exception details."""
        if not LOGURU_AVAILABLE:
            print(f"ERROR: {message} - {error} - File: {file_path}")
            return
        
        context = {
            "file_path": str(file_path) if file_path else "unknown",
            **kwargs
        }
        
        logger.bind(**context).error(f"{message}: {type(error).__name__}: {error}")
    
    def log_performance(self, operation: str, duration_ms: float, items_count: int = 1, **kwargs) -> None:
        """Log performance metrics."""
        if not LOGURU_AVAILABLE:
            return
        
        context = {
            "performance": True,
            "operation": operation,
            "duration_ms": f"{duration_ms:.2f}",
            "items_count": str(items_count),
            **kwargs
        }
        
        rate = items_count / (duration_ms / 1000.0) if duration_ms > 0 else 0
        logger.bind(**context).debug(f"{operation} completed: {items_count} items in {duration_ms:.2f}ms ({rate:.1f} items/sec)")
    
    def get_recent_errors(self, hours: int = 24) -> List[str]:
        """Get recent errors from log files."""
        if not LOGURU_AVAILABLE:
            return []
        
        error_log = self.log_dir / "errors.log"
        if not error_log.exists():
            return []
        
        try:
            recent_errors = []
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with open(error_log, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        # Parse timestamp from log line
                        if '|' in line:
                            timestamp_str = line.split('|')[0].strip()
                            log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                            
                            if log_time >= cutoff_time:
                                recent_errors.append(line.strip())
                    except (ValueError, IndexError):
                        continue
            
            return recent_errors[-50:]  # Return last 50 errors
            
        except Exception as e:
            logger.error(f"Failed to read error log: {e}")
            return []
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics."""
        stats = {
            "log_dir": str(self.log_dir),
            "configured": self._configured,
            "uptime_seconds": time.time() - self._start_time,
            "log_files": []
        }
        
        if self.log_dir.exists():
            for log_file in self.log_dir.glob("*.log*"):
                file_stats = log_file.stat()
                stats["log_files"].append({
                    "name": log_file.name,
                    "size_mb": file_stats.st_size / (1024 * 1024),
                    "modified": datetime.fromtimestamp(file_stats.st_mtime)
                })
        
        return stats


class DiagnosticsPanel:
    """Comprehensive diagnostics panel for system monitoring."""
    
    def __init__(self, db_path: Path, settings: Settings, cache_manager: Optional[CacheManager] = None):
        self.db_path = db_path
        self.settings = settings
        self.cache_manager = cache_manager or CacheManager(settings)
        self.db_manager = DatabaseManager(db_path)
        
        self._last_update = datetime.now()
        self._update_interval = 30  # seconds
        self._cached_data: Optional[DiagnosticsData] = None
    
    def get_diagnostics(self, force_refresh: bool = False) -> DiagnosticsData:
        """Get comprehensive diagnostics data."""
        now = datetime.now()
        
        # Use cached data if recent and not forcing refresh
        if (not force_refresh and 
            self._cached_data and 
            (now - self._last_update).seconds < self._update_interval):
            return self._cached_data
        
        # Gather fresh diagnostics
        data = DiagnosticsData()
        
        try:
            # System statistics
            data.system_stats = self._collect_system_stats()
            
            # Performance metrics
            data.performance_metrics = self._collect_performance_metrics()
            
            # System health assessment
            data.system_health = self._assess_system_health(data.system_stats, data.performance_metrics)
            
            # Recent errors (if logging manager available)
            data.recent_errors = self._get_recent_errors()
            
            data.last_updated = now
            
        except Exception as e:
            if LOGURU_AVAILABLE and logger:
                logger.error(f"Failed to collect diagnostics: {e}")
            else:
                print(f"Diagnostics error: {e}")
        
        self._cached_data = data
        self._last_update = now
        
        return data
    
    def _collect_system_stats(self) -> SystemStats:
        """Collect system statistics from database."""
        stats = SystemStats()
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Total files
                cursor.execute("SELECT COUNT(*) FROM files")
                stats.total_files = cursor.fetchone()[0]
                
                # Total groups
                cursor.execute("SELECT COUNT(*) FROM groups")
                stats.total_groups = cursor.fetchone()[0]
                
                # Total duplicates and safe duplicates
                cursor.execute("""
                    SELECT role, COUNT(*) 
                    FROM group_members 
                    WHERE role IN ('duplicate', 'safe_duplicate')
                    GROUP BY role
                """)
                
                role_counts = dict(cursor.fetchall())
                stats.total_duplicates = role_counts.get('duplicate', 0)
                stats.safe_duplicates = role_counts.get('safe_duplicate', 0)
                
                # Estimated reclaimable space (safe duplicates only)
                cursor.execute("""
                    SELECT SUM(f.file_size) 
                    FROM files f
                    JOIN group_members gm ON f.id = gm.file_id
                    WHERE gm.role = 'safe_duplicate'
                """)
                
                result = cursor.fetchone()[0]
                stats.estimated_reclaimable_mb = (result or 0) / (1024 * 1024)
                
                # Thumbnail count
                cursor.execute("SELECT COUNT(*) FROM thumbs")
                stats.thumbnail_count = cursor.fetchone()[0]
                
                # Feature count
                cursor.execute("SELECT COUNT(*) FROM features")
                stats.feature_count = cursor.fetchone()[0]
                
                # Database size
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                stats.database_size_mb = db_size / (1024 * 1024)
                
                # Last scan time (approximate from most recent file)
                cursor.execute("SELECT MAX(scan_time) FROM files")
                last_scan = cursor.fetchone()[0]
                if last_scan:
                    stats.last_scan_time = datetime.fromtimestamp(last_scan)
                
        except Exception as e:
            if LOGURU_AVAILABLE and logger:
                logger.error(f"Failed to collect system stats: {e}")
        
        # Cache statistics
        try:
            cache_stats = self.cache_manager.get_cache_stats()
            stats.cache_size_mb = cache_stats.get('total_size_mb', 0.0)
            
            # Last purge time from cache stats
            last_purge = cache_stats.get('last_cleanup_time')
            if last_purge:
                stats.last_purge_time = datetime.fromtimestamp(last_purge)
                
        except Exception as e:
            if LOGURU_AVAILABLE and logger:
                logger.error(f"Failed to collect cache stats: {e}")
        
        return stats
    
    def _collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect performance metrics."""
        metrics = PerformanceMetrics()
        
        try:
            # Try to get memory usage with psutil if available
            try:
                import psutil
                process = psutil.Process()
                metrics.memory_usage_mb = process.memory_info().rss / (1024 * 1024)
                metrics.cpu_usage_percent = process.cpu_percent()
            except ImportError:
                # psutil not available, skip detailed metrics
                pass
            
        except Exception as e:
            if LOGURU_AVAILABLE and logger:
                logger.error(f"Failed to collect performance metrics: {e}")
        
        # TODO: Integrate with worker pool stats when available
        # This would include active_threads, queue_depth, etc.
        
        return metrics
    
    def _assess_system_health(self, system_stats: SystemStats, performance_metrics: PerformanceMetrics) -> str:
        """Assess overall system health."""
        issues = []
        
        # Check for basic functionality
        if system_stats.total_files == 0:
            issues.append("No files scanned")
        
        # Check database size vs file count ratio
        if system_stats.total_files > 0:
            db_per_file = system_stats.database_size_mb / system_stats.total_files
            if db_per_file > 0.1:  # More than 100KB per file seems excessive
                issues.append("Database size large relative to file count")
        
        # Check cache size
        if system_stats.cache_size_mb > 5000:  # Over 5GB
            issues.append("Cache size very large")
        
        # Check memory usage
        if performance_metrics.memory_usage_mb > 2000:  # Over 2GB
            issues.append("High memory usage")
        
        # Determine health status
        if not issues:
            return "excellent"
        elif len(issues) == 1:
            return "good"
        elif len(issues) <= 2:
            return "fair"
        else:
            return "poor"
    
    def _get_recent_errors(self) -> List[str]:
        """Get recent errors from logging system."""
        # This would integrate with LoggingManager if available
        return []
    
    def render_diagnostics_text(self) -> str:
        """Render diagnostics as formatted text."""
        data = self.get_diagnostics()
        
        lines = [
            "📊 PHOTO-DEDUPE DIAGNOSTICS PANEL",
            "=" * 50,
            "",
            "🗂️  SYSTEM STATISTICS",
            f"   Total Files:           {data.system_stats.total_files:,}",
            f"   Duplicate Groups:      {data.system_stats.total_groups:,}",
            f"   Regular Duplicates:    {data.system_stats.total_duplicates:,}",
            f"   Safe Duplicates:       {data.system_stats.safe_duplicates:,}",
            f"   Reclaimable Space:     {data.system_stats.estimated_reclaimable_mb:.1f} MB",
            f"   Thumbnails Generated:  {data.system_stats.thumbnail_count:,}",
            f"   Features Extracted:    {data.system_stats.feature_count:,}",
            "",
            "💾 STORAGE & CACHE",
            f"   Database Size:         {data.system_stats.database_size_mb:.1f} MB",
            f"   Cache Size:            {data.system_stats.cache_size_mb:.1f} MB",
            f"   Last Purge:            {data.system_stats.last_purge_time or 'Never'}",
            "",
            "⚡ PERFORMANCE",
            f"   Memory Usage:          {data.performance_metrics.memory_usage_mb:.1f} MB",
            f"   CPU Usage:             {data.performance_metrics.cpu_usage_percent:.1f}%",
            f"   Active Threads:        {data.performance_metrics.active_threads}",
            f"   Queue Depth:           {data.performance_metrics.queue_depth}",
            "",
            "🏥 SYSTEM HEALTH",
            f"   Overall Status:        {data.system_health.upper()}",
            f"   Last Scan:             {data.system_stats.last_scan_time or 'Never'}",
            f"   Uptime:                {data.uptime_seconds:.0f} seconds",
            f"   Last Updated:          {data.last_updated.strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        
        # Add recent errors if any
        if data.recent_errors:
            lines.extend([
                "",
                "🚨 RECENT ERRORS",
                *[f"   {error[:80]}..." if len(error) > 80 else f"   {error}" 
                  for error in data.recent_errors[-5:]]
            ])
        
        lines.append("")
        lines.append("=" * 50)
        
        return "\n".join(lines)
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a compact health summary."""
        data = self.get_diagnostics()
        
        return {
            "health_status": data.system_health,
            "total_files": data.system_stats.total_files,
            "duplicates_found": data.system_stats.total_duplicates + data.system_stats.safe_duplicates,
            "reclaimable_mb": data.system_stats.estimated_reclaimable_mb,
            "memory_usage_mb": data.performance_metrics.memory_usage_mb,
            "recent_error_count": len(data.recent_errors),
            "last_updated": data.last_updated.isoformat()
        }


# Integration functions
def setup_logging(settings: Settings, log_dir: Optional[Path] = None) -> LoggingManager:
    """Set up application logging."""
    return LoggingManager(settings, log_dir)


def create_diagnostics_panel(db_path: Path, settings: Settings, cache_manager: Optional[CacheManager] = None) -> DiagnosticsPanel:
    """Create diagnostics panel for system monitoring."""
    return DiagnosticsPanel(db_path, settings, cache_manager)


__all__ = [
    "LoggingManager", "DiagnosticsPanel", "DiagnosticsData", 
    "SystemStats", "PerformanceMetrics",
    "setup_logging", "create_diagnostics_panel"
]