"""
Integration module for Step 13: Concurrency-aware operations.

This module shows how to integrate the worker pool system with existing
photo-dedupe operations like scanning, hashing, and thumbnail generation.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from app.settings import Settings
    from core.concurrency import WorkerPool, TaskPriority, WorkerPoolState
    from core.thumbs import ThumbnailGenerator
    from ops.scan import FilesystemScanner
    from core.features import FeatureExtractor
    from store.db import DatabaseManager
except ImportError:
    # Handle import issues gracefully for type checking
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from app.settings import Settings
        from core.concurrency import WorkerPool, TaskPriority, WorkerPoolState
        from core.thumbs import ThumbnailGenerator
        from ops.scan import FilesystemScanner
        from core.features import FeatureExtractor
        from store.db import DatabaseManager
    else:
        Settings = None
        WorkerPool = None
        TaskPriority = None
        WorkerPoolState = None
        ThumbnailGenerator = None
        FilesystemScanner = None
        FeatureExtractor = None
        DatabaseManager = None


class ConcurrentThumbnailGenerator:
    """Thumbnail generator with concurrency support and back-off."""
    
    def __init__(self, db_path: Path, settings: Settings, worker_pool: WorkerPool):
        self.thumbnail_generator = ThumbnailGenerator(db_path, settings)
        self.worker_pool = worker_pool
        self.settings = settings
        self.db_path = db_path
        
        # Progress tracking
        self._progress_callback: Optional[Callable[[int, int, Path], None]] = None
        self._completed_count = 0
        self._total_count = 0
        self._generation_stats = {
            'started_at': 0.0,
            'completed': 0,
            'failed': 0,
            'skipped': 0,
            'average_time': 0.0
        }
    
    def set_progress_callback(self, callback: Callable[[int, int, Path], None]) -> None:
        """Set progress callback for thumbnail generation."""
        self._progress_callback = callback
    
    def generate_thumbnails_concurrent(self, file_ids: List[int], batch_size: Optional[int] = None) -> Dict[str, Any]:
        """Generate thumbnails concurrently with UI responsiveness."""
        if not file_ids:
            return {'completed': 0, 'failed': 0, 'skipped': 0}
        
        # Get batch size from settings
        if batch_size is None:
            batch_size = self.settings.get("Concurrency", "batch_size_thumbnails", 25)
        
        # Reset stats
        self._generation_stats = {
            'started_at': time.time(),
            'completed': 0,
            'failed': 0,
            'skipped': 0,
            'average_time': 0.0
        }
        self._completed_count = 0
        self._total_count = len(file_ids)
        
        # Process in batches to avoid overwhelming the system
        batches = [file_ids[i:i + batch_size] for i in range(0, len(file_ids), batch_size)]
        
        print(f"Generating thumbnails for {len(file_ids)} files in {len(batches)} batches...")
        
        # Submit batches as tasks
        batch_futures = []
        for i, batch in enumerate(batches):
            task_id = f"thumbnail-batch-{i}"
            # Use HIGH priority for thumbnails (UI responsiveness)
            self.worker_pool.submit_task(
                task_id,
                self._process_thumbnail_batch,
                TaskPriority.HIGH,
                "thumbnail",
                batch, i + 1, len(batches)
            )
        
        # Wait for completion or monitor progress
        self._wait_for_thumbnail_completion(len(batches))
        
        return {
            'completed': self._generation_stats['completed'],
            'failed': self._generation_stats['failed'],
            'skipped': self._generation_stats['skipped'],
            'total_time': time.time() - self._generation_stats['started_at'],
            'average_time': self._generation_stats['average_time']
        }
    
    def _process_thumbnail_batch(self, file_ids: List[int], batch_num: int, total_batches: int) -> Dict[str, Any]:
        """Process a batch of thumbnail generation tasks."""
        batch_stats = {'completed': 0, 'failed': 0, 'skipped': 0}
        batch_start = time.time()
        
        # Get file information from database
        with self.thumbnail_generator.db_path.open() if hasattr(self.thumbnail_generator.db_path, 'open') else None:
            pass  # Database connection handled by ThumbnailGenerator
        
        for file_id in file_ids:
            try:
                # Get file path from database
                from store.db import DatabaseManager
                db_manager = DatabaseManager(self.db_path)
                
                with db_manager.get_connection() as conn:
                    cursor = conn.execute("SELECT file_path FROM files WHERE id = ?", (file_id,))
                    result = cursor.fetchone()
                    
                    if not result:
                        batch_stats['skipped'] += 1
                        continue
                    
                    file_path = Path(result[0])
                
                # Check if thumbnail already exists
                existing_thumb = self.thumbnail_generator.get_or_create_thumbnail(file_id, file_path)
                
                if existing_thumb:
                    batch_stats['completed'] += 1
                else:
                    batch_stats['failed'] += 1
                
                # Update progress
                self._completed_count += 1
                if self._progress_callback:
                    self._progress_callback(self._completed_count, self._total_count, file_path)
                
            except Exception as e:
                print(f"Error processing thumbnail for file {file_id}: {e}")
                batch_stats['failed'] += 1
        
        # Update global stats
        batch_time = time.time() - batch_start
        self._update_generation_stats(batch_stats, batch_time)
        
        print(f"Batch {batch_num}/{total_batches} completed: {batch_stats['completed']} thumbnails, {batch_stats['failed']} failed")
        
        return batch_stats
    
    def _update_generation_stats(self, batch_stats: Dict[str, Any], batch_time: float) -> None:
        """Update global generation statistics."""
        self._generation_stats['completed'] += batch_stats['completed']
        self._generation_stats['failed'] += batch_stats['failed']
        self._generation_stats['skipped'] += batch_stats['skipped']
        
        # Update average time
        total_items = self._generation_stats['completed'] + self._generation_stats['failed']
        if total_items > 0:
            current_avg = self._generation_stats['average_time']
            items_in_batch = batch_stats['completed'] + batch_stats['failed']
            if items_in_batch > 0:
                batch_avg = batch_time / items_in_batch
                new_avg = ((current_avg * (total_items - items_in_batch)) + (batch_avg * items_in_batch)) / total_items
                self._generation_stats['average_time'] = new_avg
    
    def _wait_for_thumbnail_completion(self, expected_batches: int) -> None:
        """Wait for thumbnail generation to complete."""
        start_time = time.time()
        timeout = 300  # 5 minutes timeout
        
        while time.time() - start_time < timeout:
            stats = self.worker_pool.get_stats()
            
            # Check if we're done (simplified check)
            if stats.pending_tasks == 0 and stats.active_threads == 0:
                break
            
            time.sleep(0.5)
        
        print(f"Thumbnail generation completed in {time.time() - start_time:.2f}s")


class ConcurrentFilesystemScanner:
    """Filesystem scanner with concurrency support."""
    
    def __init__(self, db_path: Path, settings: Settings, worker_pool: WorkerPool):
        self.scanner = FilesystemScanner(db_path, settings)
        self.worker_pool = worker_pool
        self.settings = settings
        self.db_path = db_path
    
    def scan_directories_concurrent(self, directories: List[Path]) -> Dict[str, Any]:
        """Scan directories concurrently."""
        batch_size = self.settings.get("Concurrency", "batch_size_scanning", 100)
        
        print(f"Scanning {len(directories)} directories concurrently...")
        
        # Submit each directory as a separate task
        for i, directory in enumerate(directories):
            task_id = f"scan-dir-{i}"
            # Use NORMAL priority for scanning
            self.worker_pool.submit_task(
                task_id,
                self._scan_single_directory,
                TaskPriority.NORMAL,
                "scan",
                directory
            )
        
        # Wait for completion
        self._wait_for_scan_completion(len(directories))
        
        return self.scanner.get_scan_summary()
    
    def _scan_single_directory(self, directory: Path) -> Dict[str, Any]:
        """Scan a single directory."""
        print(f"Scanning directory: {directory}")
        
        try:
            # Use existing scanner to process directory
            files_found = self.scanner.scan_directory(directory)
            return {'directory': str(directory), 'files_found': len(files_found)}
            
        except Exception as e:
            print(f"Error scanning {directory}: {e}")
            return {'directory': str(directory), 'error': str(e)}
    
    def _wait_for_scan_completion(self, expected_tasks: int) -> None:
        """Wait for scanning to complete."""
        start_time = time.time()
        timeout = 600  # 10 minutes timeout
        
        while time.time() - start_time < timeout:
            stats = self.worker_pool.get_stats()
            
            if stats.pending_tasks == 0 and stats.active_threads == 0:
                break
            
            time.sleep(1.0)
        
        print(f"Directory scanning completed in {time.time() - start_time:.2f}s")


class ConcurrentFeatureExtractor:
    """Feature extractor with concurrency support."""
    
    def __init__(self, db_path: Path, settings: Settings, worker_pool: WorkerPool):
        self.feature_extractor = FeatureExtractor(db_path, settings)
        self.worker_pool = worker_pool
        self.settings = settings
        self.db_path = db_path
    
    def extract_features_concurrent(self, file_ids: List[int]) -> Dict[str, Any]:
        """Extract features concurrently."""
        if not file_ids:
            return {'completed': 0, 'failed': 0}
        
        batch_size = self.settings.get("Concurrency", "batch_size_hashing", 50)
        batches = [file_ids[i:i + batch_size] for i in range(0, len(file_ids), batch_size)]
        
        print(f"Extracting features for {len(file_ids)} files in {len(batches)} batches...")
        
        # Submit batches
        for i, batch in enumerate(batches):
            task_id = f"features-batch-{i}"
            # Use LOW priority for feature extraction (CPU intensive)
            self.worker_pool.submit_task(
                task_id,
                self._extract_features_batch,
                TaskPriority.LOW,
                "analysis",
                batch
            )
        
        # Wait for completion
        self._wait_for_feature_completion(len(batches))
        
        return {'batches_processed': len(batches), 'total_files': len(file_ids)}
    
    def _extract_features_batch(self, file_ids: List[int]) -> Dict[str, Any]:
        """Extract features for a batch of files."""
        batch_stats = {'completed': 0, 'failed': 0}
        
        for file_id in file_ids:
            try:
                # Extract features using existing extractor
                features = self.feature_extractor.extract_all_features(file_id)
                if features:
                    batch_stats['completed'] += 1
                else:
                    batch_stats['failed'] += 1
                    
            except Exception as e:
                print(f"Error extracting features for file {file_id}: {e}")
                batch_stats['failed'] += 1
        
        return batch_stats
    
    def _wait_for_feature_completion(self, expected_batches: int) -> None:
        """Wait for feature extraction to complete."""
        start_time = time.time()
        timeout = 1200  # 20 minutes timeout
        
        while time.time() - start_time < timeout:
            stats = self.worker_pool.get_stats()
            
            if stats.pending_tasks == 0 and stats.active_threads == 0:
                break
            
            time.sleep(2.0)
        
        print(f"Feature extraction completed in {time.time() - start_time:.2f}s")


class ResponsiveUIController:
    """Controller that manages UI responsiveness with back-off."""
    
    def __init__(self, worker_pool: WorkerPool):
        self.worker_pool = worker_pool
        self._ui_events = []
        self._last_ui_update = 0.0
    
    def handle_scroll_event(self) -> None:
        """Handle UI scroll event."""
        self.worker_pool.record_interaction("scroll")
        self._ui_events.append(("scroll", time.time()))
        self._update_ui_if_needed()
    
    def handle_hover_event(self) -> None:
        """Handle UI hover event."""
        self.worker_pool.record_interaction("hover")
        self._ui_events.append(("hover", time.time()))
        self._update_ui_if_needed()
    
    def handle_click_event(self) -> None:
        """Handle UI click event."""
        self.worker_pool.record_interaction("click")
        self._ui_events.append(("click", time.time()))
        self._update_ui_if_needed()
    
    def request_thumbnail(self, file_id: int, file_path: Path) -> None:
        """Request thumbnail with CRITICAL priority for immediate UI needs."""
        task_id = f"ui-thumbnail-{file_id}"
        
        # Cancel any existing lower priority thumbnail requests for this file
        # (Implementation would depend on more sophisticated task management)
        
        # Submit as critical priority
        self.worker_pool.submit_task(
            task_id,
            self._generate_single_thumbnail,
            TaskPriority.CRITICAL,
            "ui-thumbnail",
            file_id, file_path
        )
    
    def _generate_single_thumbnail(self, file_id: int, file_path: Path) -> Optional[Path]:
        """Generate a single thumbnail for immediate UI use."""
        try:
            # This would use the actual thumbnail generator
            print(f"Generating critical thumbnail for {file_path.name}")
            time.sleep(0.2)  # Simulate thumbnail generation
            return file_path  # Return thumbnail path
            
        except Exception as e:
            print(f"Error generating thumbnail for {file_path}: {e}")
            return None
    
    def _update_ui_if_needed(self) -> None:
        """Update UI if enough time has passed since last update."""
        now = time.time()
        if now - self._last_ui_update > 0.1:  # Max 10 FPS UI updates
            self._last_ui_update = now
            # Trigger UI update here
            pass
    
    def get_ui_responsiveness_stats(self) -> Dict[str, Any]:
        """Get UI responsiveness statistics."""
        recent_events = [e for e in self._ui_events if time.time() - e[1] < 10.0]
        
        event_counts = {}
        for event_type, _ in recent_events:
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        return {
            'recent_events': len(recent_events),
            'event_breakdown': event_counts,
            'worker_pool_state': self.worker_pool.state.name,
            'back_off_events': self.worker_pool.get_stats().back_off_events
        }


# Factory function to create integrated system
def create_concurrent_processing_system(db_path: Path, settings: Settings) -> Dict[str, Any]:
    """Create a complete concurrent processing system."""
    from core.concurrency import create_file_processing_pool
    
    # Create worker pool
    worker_pool = create_file_processing_pool(settings)
    
    # Create concurrent components
    thumbnail_gen = ConcurrentThumbnailGenerator(db_path, settings, worker_pool)
    scanner = ConcurrentFilesystemScanner(db_path, settings, worker_pool)
    feature_extractor = ConcurrentFeatureExtractor(db_path, settings, worker_pool)
    ui_controller = ResponsiveUIController(worker_pool)
    
    # Set up callbacks for monitoring
    def on_task_complete(task, result):
        print(f"Task {task.id} completed: {task.category}")
    
    def on_task_error(task, error):
        print(f"Task {task.id} failed: {error}")
    
    def on_state_change(new_state):
        print(f"Worker pool state changed to: {new_state.name}")
    
    worker_pool.set_callbacks(on_task_complete, on_task_error, on_state_change)
    
    return {
        'worker_pool': worker_pool,
        'thumbnail_generator': thumbnail_gen,
        'scanner': scanner,
        'feature_extractor': feature_extractor,
        'ui_controller': ui_controller
    }


__all__ = [
    "ConcurrentThumbnailGenerator",
    "ConcurrentFilesystemScanner", 
    "ConcurrentFeatureExtractor",
    "ResponsiveUIController",
    "create_concurrent_processing_system"
]