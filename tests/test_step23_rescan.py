"""
Tests for Step 23 - Rescan & Delta Updates System.

This module tests:
- Delta rescan with change detection
- Missing features processing  
- Full rebuild with data preservation
- Performance and efficiency metrics
"""

import pytest
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

def test_rescan_manager_initialization():
    """Test RescanManager initialization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        # Mock settings
        mock_settings = Mock()
        mock_settings._data = {
            "Performance": {"current_preset": "Balanced"},
            "Cache": {"cache_dir": temp_dir}
        }
        
        # Mock dependencies
        with patch('ops.rescan.DatabaseManager') as mock_db, \
             patch('ops.rescan.FileScanner') as mock_scanner, \
             patch('ops.rescan.FeatureExtractor') as mock_features, \
             patch('ops.rescan.ThumbnailGenerator') as mock_thumbs:
            
            from ops.rescan import RescanManager
            
            manager = RescanManager(db_path, mock_settings)
            
            assert manager.db_path == db_path
            assert manager.settings == mock_settings
            assert manager.current_stats is None


def test_delta_rescan_change_detection():
    """Test delta rescan change detection logic."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        test_dir = Path(temp_dir) / "images"
        test_dir.mkdir()
        
        # Create test files
        file1 = test_dir / "image1.jpg"
        file2 = test_dir / "image2.jpg"
        file3 = test_dir / "image3.jpg"
        
        file1.write_text("test image 1")
        file2.write_text("test image 2")
        
        mock_settings = Mock()
        mock_settings._data = {"Performance": {"current_preset": "Balanced"}}
        
        with patch('ops.rescan.DatabaseManager') as mock_db, \
             patch('ops.rescan.FileScanner'), \
             patch('ops.rescan.FeatureExtractor'), \
             patch('ops.rescan.ThumbnailGenerator'):
            
            # Mock database responses for change detection
            mock_conn = Mock()
            mock_cursor = Mock()
            
            # Simulate existing files in database
            existing_files_data = [
                (1, str(file1), 100, time.time() - 3600, 'active'),  # Unchanged file
                (2, str(file2), 200, time.time() - 7200, 'active'),  # File that will be "changed"
            ]
            mock_cursor.fetchall.return_value = existing_files_data
            mock_conn.execute.return_value = mock_cursor
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.__exit__.return_value = None
            mock_db.return_value.get_connection.return_value = mock_conn
            
            from ops.rescan import RescanManager, ChangeDetectionResult
            
            manager = RescanManager(db_path, mock_settings)
            
            # Mock the file walking to return our test files
            def mock_walk_files(root_path):
                return [file1, file2, file3]  # file3 is new
            
            manager._walk_image_files = mock_walk_files
            
            # Mock file needs checks
            manager._file_needs_features = lambda file_id: file_id == 2  # file2 needs features
            manager._file_needs_thumbnail = lambda file_id: file_id == 2  # file2 needs thumbnail
            
            # Perform change detection
            changes = manager._detect_file_changes([test_dir])
            
            # Verify results
            assert len(changes) == 3
            
            # Check file1 (unchanged)
            file1_change = next(c for c in changes if c.file_path == file1)
            assert not file1_change.is_new
            assert not file1_change.is_changed
            
            # Check file3 (new)
            file3_change = next(c for c in changes if c.file_path == file3)
            assert file3_change.is_new
            assert file3_change.needs_features
            assert file3_change.needs_thumbnail


def test_missing_features_rescan():
    """Test rescan for missing features and thumbnails."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        mock_settings = Mock()
        
        with patch('ops.rescan.DatabaseManager') as mock_db, \
             patch('ops.rescan.FileScanner'), \
             patch('ops.rescan.FeatureExtractor') as mock_features, \
             patch('ops.rescan.ThumbnailGenerator') as mock_thumbs:
            
            # Mock database for missing features
            mock_conn = Mock()
            mock_cursor = Mock()
            
            # Files missing features
            missing_features_data = [
                (1, "/test/file1.jpg"),
                (2, "/test/file2.jpg")
            ]
            
            # Mock cursor to return different data for different queries
            def mock_execute(query, params=None):
                if "LEFT JOIN features" in query:
                    mock_cursor.fetchall.return_value = missing_features_data
                elif "LEFT JOIN thumbs" in query:
                    mock_cursor.fetchall.return_value = [(3, "/test/file3.jpg")]
                return mock_cursor
            
            mock_conn.execute = mock_execute
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.__exit__.return_value = None
            mock_db.return_value.get_connection.return_value = mock_conn
            
            from ops.rescan import RescanManager
            
            manager = RescanManager(db_path, mock_settings)
            
            # Test finding files needing work
            files_needing_work = manager._find_files_needing_processing()
            
            # Should include files missing features and thumbnails
            assert len(files_needing_work) == 3
            
            file_ids = [item[0] for item in files_needing_work]
            assert 1 in file_ids  # Missing features
            assert 2 in file_ids  # Missing features  
            assert 3 in file_ids  # Missing thumbnails


def test_full_rebuild_data_preservation():
    """Test full rebuild with user data preservation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        mock_settings = Mock()
        
        with patch('ops.rescan.DatabaseManager') as mock_db, \
             patch('ops.rescan.FileScanner'), \
             patch('ops.rescan.FeatureExtractor'), \
             patch('ops.rescan.ThumbnailGenerator'):
            
            # Mock database for backup/restore operations
            mock_conn = Mock()
            mock_cursor = Mock()
            
            # Mock user data
            groups_data = [
                {'id': 1, 'reason': 'exact_duplicates', 'score_summary': 'confidence:1.0', 'created_at': time.time()}
            ]
            
            group_members_data = [
                {'group_id': 1, 'file_id': 1, 'role': 'original', 'similarity_score': 1.0, 'notes': None},
                {'group_id': 1, 'file_id': 2, 'role': 'duplicate', 'similarity_score': 0.95, 'notes': None}
            ]
            
            overrides_data = [
                {'id': 1, 'group_id': 1, 'original_file_id': 1, 'auto_original_id': 2, 
                 'override_type': 'single_group', 'reason': 'user_preference', 
                 'created_at': time.time(), 'notes': 'User selected', 'is_active': True}
            ]
            
            def mock_execute(query, params=None):
                if "SELECT * FROM groups" in query:
                    mock_cursor.fetchall.return_value = [tuple(g.values()) for g in groups_data]
                elif "SELECT * FROM group_members" in query:
                    mock_cursor.fetchall.return_value = [tuple(gm.values()) for gm in group_members_data]
                elif "SELECT * FROM manual_overrides" in query:
                    mock_cursor.fetchall.return_value = [tuple(o.values()) for o in overrides_data]
                elif "SELECT COUNT(*)" in query:
                    mock_cursor.fetchone.return_value = (5,)  # Mock count
                else:
                    mock_cursor.fetchall.return_value = []
                    mock_cursor.fetchone.return_value = (0,)
                return mock_cursor
            
            mock_conn.execute = mock_execute
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.__exit__.return_value = None
            mock_db.return_value.get_connection.return_value = mock_conn
            
            from ops.rescan import RescanManager
            
            manager = RescanManager(db_path, mock_settings)
            
            # Test backup
            backup_data = manager._backup_user_data(
                preserve_overrides=True, 
                preserve_groups=True
            )
            
            assert 'groups' in backup_data
            assert 'group_members' in backup_data
            assert 'overrides' in backup_data
            assert len(backup_data['groups']) == 1
            assert len(backup_data['group_members']) == 2
            assert len(backup_data['overrides']) == 1
            
            # Test restore
            restore_stats = manager._restore_user_data(backup_data)
            
            assert restore_stats['groups_restored'] == 1
            # Note: overrides_restored depends on file existence checks


def test_rescan_statistics():
    """Test rescan statistics calculation."""
    from ops.rescan import RescanStats, RescanMode
    
    # Test basic statistics
    stats = RescanStats(
        mode=RescanMode.DELTA_ONLY,
        start_time=time.time() - 100,
        end_time=time.time(),
        files_new=10,
        files_changed=5,
        files_unchanged=85,
        files_processed=15,
        features_extracted=10,
        features_reused=5,
        thumbnails_created=8,
        thumbnails_reused=7
    )
    
    stats.total_duration = 100.0
    
    # Test computed properties
    assert stats.files_total == 100  # 10 + 5 + 85
    assert stats.speed_files_per_second == 0.15  # 15 / 100
    
    # Test efficiency ratio
    total_items = 10 + 5 + 8 + 7  # features_extracted + reused + thumbs_created + reused
    reused_items = 5 + 7  # features_reused + thumbnails_reused
    expected_efficiency = reused_items / total_items
    assert abs(stats.efficiency_ratio - expected_efficiency) < 0.001


def test_rescan_recommendations():
    """Test rescan recommendations logic."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        mock_settings = Mock()
        
        with patch('ops.rescan.DatabaseManager') as mock_db:
            # Mock database statistics
            mock_conn = Mock()
            mock_cursor = Mock()
            
            # Scenario 1: Most files missing features (should recommend full rebuild)
            def mock_execute_scenario1(query, params=None):
                if "active_files" in query:
                    mock_cursor.fetchone.return_value = (100, 20, 30, 5)  # files, features, thumbs, groups
                elif "LEFT JOIN features" in query:
                    mock_cursor.fetchone.return_value = (60,)  # 60 files missing features
                elif "LEFT JOIN thumbs" in query:
                    mock_cursor.fetchone.return_value = (55,)  # 55 files missing thumbs
                return mock_cursor
            
            mock_conn.execute = mock_execute_scenario1
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.__exit__.return_value = None
            mock_db.return_value.get_connection.return_value = mock_conn
            
            from ops.rescan import RescanManager, RescanMode
            
            manager = RescanManager(db_path, mock_settings)
            recommendations = manager.get_rescan_recommendations()
            
            assert recommendations['recommended_mode'] == RescanMode.FULL_REBUILD
            assert "More than 50%" in " ".join(recommendations['reasons'])
            
            # Scenario 2: Few files missing (should recommend missing features)
            def mock_execute_scenario2(query, params=None):
                if "active_files" in query:
                    mock_cursor.fetchone.return_value = (100, 95, 98, 10)
                elif "LEFT JOIN features" in query:
                    mock_cursor.fetchone.return_value = (5,)  # 5 files missing features
                elif "LEFT JOIN thumbs" in query:
                    mock_cursor.fetchone.return_value = (2,)  # 2 files missing thumbs
                return mock_cursor
            
            mock_conn.execute = mock_execute_scenario2
            
            recommendations = manager.get_rescan_recommendations()
            
            assert recommendations['recommended_mode'] == RescanMode.MISSING_FEATURES
            assert "5 files missing features, 2 missing thumbnails" in " ".join(recommendations['reasons'])
            
            # Scenario 3: No missing files (should recommend delta)
            def mock_execute_scenario3(query, params=None):
                if "active_files" in query:
                    mock_cursor.fetchone.return_value = (100, 100, 100, 15)
                elif "LEFT JOIN features" in query or "LEFT JOIN thumbs" in query:
                    mock_cursor.fetchone.return_value = (0,)  # No missing files
                return mock_cursor
            
            mock_conn.execute = mock_execute_scenario3
            
            recommendations = manager.get_rescan_recommendations()
            
            assert recommendations['recommended_mode'] == RescanMode.DELTA_ONLY
            assert "appears complete" in " ".join(recommendations['reasons'])


def test_file_change_detection_edge_cases():
    """Test edge cases in file change detection."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        mock_settings = Mock()
        
        with patch('ops.rescan.DatabaseManager') as mock_db, \
             patch('ops.rescan.FileScanner'), \
             patch('ops.rescan.FeatureExtractor'), \
             patch('ops.rescan.ThumbnailGenerator'):
            
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.execute.return_value = mock_cursor
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.__exit__.return_value = None
            mock_db.return_value.get_connection.return_value = mock_conn
            
            from ops.rescan import RescanManager, ChangeDetectionResult
            
            manager = RescanManager(db_path, mock_settings)
            
            # Test file that no longer exists
            missing_file = Path(temp_dir) / "missing.jpg"
            
            # Mock existing files in database including the missing one
            existing_files_data = [
                (1, str(missing_file), 100, time.time(), 'active')
            ]
            mock_cursor.fetchall.return_value = existing_files_data
            
            # Mock empty filesystem scan (no files found)
            manager._walk_image_files = lambda root_path: []
            
            changes = manager._detect_file_changes([Path(temp_dir)])
            
            # Should detect the missing file
            assert len(changes) == 1
            missing_change = changes[0]
            assert missing_change.file_path == missing_file
            assert not missing_change.is_new
            assert not missing_change.is_changed


def test_rescan_performance_metrics():
    """Test rescan performance monitoring and metrics."""
    from ops.rescan import RescanStats, RescanMode
    
    # Simulate a realistic rescan scenario
    start_time = time.time()
    
    stats = RescanStats(
        mode=RescanMode.DELTA_ONLY,
        start_time=start_time
    )
    
    # Simulate processing
    time.sleep(0.1)  # Small delay for realistic timing
    
    stats.end_time = time.time()
    stats.total_duration = stats.end_time - stats.start_time
    
    # Add processing data
    stats.files_processed = 1000
    stats.features_extracted = 50
    stats.features_reused = 950
    stats.thumbnails_created = 30
    stats.thumbnails_reused = 970
    
    # Test performance calculations
    assert stats.speed_files_per_second > 0
    assert stats.efficiency_ratio > 0.8  # High reuse ratio
    
    # Test that efficiency ratio is calculated correctly
    total_work = stats.features_extracted + stats.features_reused + stats.thumbnails_created + stats.thumbnails_reused
    reused_work = stats.features_reused + stats.thumbnails_reused
    expected_efficiency = reused_work / total_work
    
    assert abs(stats.efficiency_ratio - expected_efficiency) < 0.001


if __name__ == "__main__":
    # Run specific tests for manual execution
    test_rescan_manager_initialization()
    test_delta_rescan_change_detection() 
    test_missing_features_rescan()
    test_full_rebuild_data_preservation()
    test_rescan_statistics()
    test_rescan_recommendations()
    test_file_change_detection_edge_cases()
    test_rescan_performance_metrics()
    
    print("All Step 23 tests passed!")