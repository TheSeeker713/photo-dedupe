"""
Tests for Step 22 - Conflict handling & manual overrides.

This module tests:
- Manual override database operations
- Conflict detection and resolution
- GUI banner system integration
- Override persistence across rescans
"""

import pytest
import time
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Test the manual override system
def test_manual_override_manager():
    """Test manual override manager database operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        # Mock database setup
        with patch('ops.manual_override.DatabaseManager') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.lastrowid = 1
            mock_cursor.fetchone.return_value = None
            mock_cursor.fetchall.return_value = []
            mock_conn.execute.return_value = mock_cursor
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.__exit__.return_value = None
            mock_db.return_value.get_connection.return_value = mock_conn
            
            from ops.manual_override import ManualOverrideManager, OverrideType, OverrideReason, ManualOverride
            
            manager = ManualOverrideManager(db_path)
            
            # Test recording override
            override = ManualOverride(
                id=None,
                group_id=1,
                original_file_id=100,
                auto_original_id=101,
                override_type=OverrideType.SINGLE_GROUP,
                reason=OverrideReason.USER_PREFERENCE,
                created_at=time.time(),
                notes="User prefers this file"
            )
            
            override_id = manager.record_override(override)
            assert override_id == 1
            
            # Verify database calls
            assert mock_conn.execute.call_count >= 2  # Deactivate old + insert new


def test_conflict_detection():
    """Test conflict detection between automatic and manual selection."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        with patch('ops.manual_override.DatabaseManager') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            
            # Mock override exists
            mock_cursor.fetchone.return_value = (
                1, 1, 100, 101, 'single_group', 'user_preference', 
                time.time(), 'Test notes', True
            )
            mock_conn.execute.return_value = mock_cursor
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.__exit__.return_value = None
            mock_db.return_value.get_connection.return_value = mock_conn
            
            from ops.manual_override import ManualOverrideManager
            
            manager = ManualOverrideManager(db_path)
            
            # Test getting override for group
            override = manager.get_override_for_group(1)
            assert override is not None
            assert override.group_id == 1
            assert override.original_file_id == 100
            assert override.auto_original_id == 101


def test_grouping_engine_with_overrides():
    """Test GroupingEngine integration with manual overrides."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        # Mock settings
        mock_settings = Mock()
        mock_settings._data = {
            "Performance": {"current_preset": "Balanced"},
            "Grouping": {
                "enable_sha256_confirmation": True,
                "strict_mode_exif_match": False,
                "dimension_tolerance": 0.1
            }
        }
        
        # Mock database and search index
        with patch('ops.grouping.DatabaseManager') as mock_db, \
             patch('ops.grouping.NearDuplicateSearchIndex') as mock_search, \
             patch('ops.manual_override.DatabaseManager') as mock_override_db:
            
            # Setup mocks
            mock_db_instance = Mock()
            mock_db.return_value = mock_db_instance
            mock_search.return_value = Mock()
            
            mock_override_conn = Mock()
            mock_override_cursor = Mock()
            mock_override_cursor.fetchone.return_value = None  # No existing override
            mock_override_conn.execute.return_value = mock_override_cursor
            mock_override_conn.__enter__.return_value = mock_override_conn
            mock_override_conn.__exit__.return_value = None
            mock_override_db.return_value.get_connection.return_value = mock_override_conn
            
            from ops.grouping import GroupingEngine, FileRecord, FileFormat
            
            engine = GroupingEngine(db_path, mock_settings)
            
            # Test original selection without override
            files = [
                FileRecord(
                    id=1, path="/test1.jpg", size=1000, fast_hash="hash1",
                    sha256_hash="sha1", phash="phash1", width=800, height=600,
                    resolution=480000, exif_datetime=datetime.now(),
                    file_format=FileFormat.JPEG
                ),
                FileRecord(
                    id=2, path="/test2.jpg", size=2000, fast_hash="hash2",
                    sha256_hash="sha2", phash="phash2", width=1920, height=1080,
                    resolution=2073600, exif_datetime=datetime.now(),
                    file_format=FileFormat.JPEG
                )
            ]
            
            original_id, duplicate_ids, conflict_info = engine._select_original(files)
            
            # Higher resolution file should be selected as original
            assert original_id == 2  # File with higher resolution
            assert duplicate_ids == [1]
            assert conflict_info is None  # No manual override


def test_conflict_banner_creation():
    """Test conflict banner widget creation and display."""
    try:
        from gui.conflict_banner import ConflictBanner, ConflictData
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer
        
        # Create QApplication if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create test conflict data
        conflict_data = ConflictData(
            group_id=1,
            auto_file_path="/test/auto.jpg",
            user_file_path="/test/user.jpg", 
            auto_file_id=100,
            user_file_id=101,
            reason="Higher resolution detected",
            confidence=0.85
        )
        
        # Create banner widget
        banner = ConflictBanner()
        
        # Test showing conflict
        banner.show_conflict(conflict_data, auto_dismiss_ms=1000)
        
        # Verify banner is showing
        assert banner.isVisible()
        assert banner.is_showing_conflict(1)
        assert not banner.is_showing_conflict(2)
        
        # Test dismissal
        banner._dismiss()
        
        # Wait for animation to complete
        QTimer.singleShot(500, app.quit)
        app.exec()
        
        assert not banner.isVisible()
        
    except ImportError:
        pytest.skip("PySide6 not available for GUI testing")


def test_conflict_banner_manager():
    """Test conflict banner manager queue and capacity handling."""
    try:
        from gui.conflict_banner import ConflictBannerManager, ConflictData
        from PySide6.QtWidgets import QApplication
        
        # Create QApplication if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create manager with capacity of 1
        manager = ConflictBannerManager(max_concurrent_banners=1)
        
        # Create test conflicts
        conflict1 = ConflictData(1, "/auto1.jpg", "/user1.jpg", 100, 101, "Test reason 1", 0.8)
        conflict2 = ConflictData(2, "/auto2.jpg", "/user2.jpg", 102, 103, "Test reason 2", 0.9)
        
        # Show first conflict
        manager.show_conflict(conflict1)
        assert len(manager.get_active_conflicts()) == 1
        assert manager.get_queue_size() == 0
        
        # Show second conflict (should be queued)
        manager.show_conflict(conflict2)
        assert len(manager.get_active_conflicts()) == 1  # Still only 1 active
        assert manager.get_queue_size() == 1  # Second is queued
        
        # Dismiss first conflict
        manager.dismiss_conflict(1)
        
        # Process events to handle queue
        app.processEvents()
        
        # Queue should be processed
        assert manager.get_queue_size() == 0
        
    except ImportError:
        pytest.skip("PySide6 not available for GUI testing")


def test_override_persistence():
    """Test that manual overrides persist across rescans."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        with patch('ops.manual_override.DatabaseManager') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            
            # Mock database calls for persistence test
            override_data = (
                1, 1, 100, 101, 'single_group', 'user_preference',
                time.time(), 'User prefers this file', True
            )
            
            mock_cursor.fetchone.return_value = override_data
            mock_cursor.fetchall.return_value = [override_data]
            mock_cursor.lastrowid = 1
            mock_conn.execute.return_value = mock_cursor
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.__exit__.return_value = None
            mock_db.return_value.get_connection.return_value = mock_conn
            
            from ops.manual_override import ManualOverrideManager
            
            manager = ManualOverrideManager(db_path)
            
            # Get all overrides (simulating app restart)
            overrides = manager.get_all_overrides(active_only=True)
            assert len(overrides) == 1
            assert overrides[0].group_id == 1
            assert overrides[0].original_file_id == 100
            assert overrides[0].is_active


def test_default_rule_application():
    """Test application of default rules for future selections."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        with patch('ops.manual_override.DatabaseManager') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.lastrowid = 1
            mock_cursor.fetchone.return_value = None
            mock_cursor.fetchall.return_value = []
            mock_conn.execute.return_value = mock_cursor
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.__exit__.return_value = None
            mock_db.return_value.get_connection.return_value = mock_conn
            
            from ops.manual_override import ManualOverrideManager, OverrideType, OverrideReason, ManualOverride
            
            manager = ManualOverrideManager(db_path)
            
            # Create default rule override
            override = ManualOverride(
                id=None,
                group_id=1,
                original_file_id=100,
                auto_original_id=101,
                override_type=OverrideType.DEFAULT_RULE,
                reason=OverrideReason.FORMAT_PREFERENCE,
                created_at=time.time(),
                notes="Always prefer JPEG over PNG"
            )
            
            override_id = manager.record_override(override)
            assert override_id == 1
            
            # Verify the override type is DEFAULT_RULE
            assert override.override_type == OverrideType.DEFAULT_RULE


def test_missing_original_file_handling():
    """Test handling when manually selected original file disappears."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        # Mock settings
        mock_settings = Mock()
        mock_settings._data = {
            "Performance": {"current_preset": "Balanced"},
            "Grouping": {
                "enable_sha256_confirmation": True,
                "strict_mode_exif_match": False,
                "dimension_tolerance": 0.1
            }
        }
        
        with patch('ops.grouping.DatabaseManager') as mock_db, \
             patch('ops.grouping.NearDuplicateSearchIndex') as mock_search, \
             patch('ops.manual_override.DatabaseManager') as mock_override_db:
            
            # Setup mocks
            mock_db_instance = Mock()
            mock_db.return_value = mock_db_instance
            mock_search.return_value = Mock()
            
            # Mock override that points to missing file
            mock_override_conn = Mock()
            mock_override_cursor = Mock()
            mock_override_cursor.fetchone.return_value = (
                1, 1, 999, 101, 'single_group', 'user_preference',  # File ID 999 doesn't exist
                time.time(), 'Test notes', True
            )
            mock_override_conn.execute.return_value = mock_override_cursor
            mock_override_conn.__enter__.return_value = mock_override_conn
            mock_override_conn.__exit__.return_value = None
            mock_override_db.return_value.get_connection.return_value = mock_override_conn
            
            from ops.grouping import GroupingEngine, FileRecord, FileFormat
            
            engine = GroupingEngine(db_path, mock_settings)
            
            # Test file group without the missing file
            files = [
                FileRecord(
                    id=100, path="/test1.jpg", size=1000, fast_hash="hash1",
                    sha256_hash="sha1", phash="phash1", width=800, height=600,
                    resolution=480000, exif_datetime=datetime.now(),
                    file_format=FileFormat.JPEG
                ),
                FileRecord(
                    id=101, path="/test2.jpg", size=2000, fast_hash="hash2", 
                    sha256_hash="sha2", phash="phash2", width=1920, height=1080,
                    resolution=2073600, exif_datetime=datetime.now(),
                    file_format=FileFormat.JPEG
                )
            ]
            
            # Mock override manager remove_override method
            if engine.override_manager:
                engine.override_manager.remove_override = Mock(return_value=True)
            
            original_id, duplicate_ids, conflict_info = engine._select_original(files, group_id=1)
            
            # Should fall back to automatic selection
            assert original_id == 101  # Higher resolution file
            assert duplicate_ids == [100]
            
            # Should indicate conflict due to missing file
            if engine.override_manager:
                engine.override_manager.remove_override.assert_called_once_with(1)


def test_override_statistics():
    """Test manual override statistics collection."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        
        with patch('ops.manual_override.DatabaseManager') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            
            # Mock statistics data
            stats_data = [
                (5,),  # total_overrides
                (3,),  # active_overrides
                [('single_group', 2), ('default_rule', 1)],  # by type
                [('user_preference', 2), ('quality_better', 1)]  # by reason
            ]
            
            mock_cursor.fetchone.side_effect = stats_data[:2]
            mock_cursor.fetchall.side_effect = stats_data[2:]
            mock_conn.execute.return_value = mock_cursor
            mock_conn.__enter__.return_value = mock_conn
            mock_conn.__exit__.return_value = None
            mock_db.return_value.get_connection.return_value = mock_conn
            
            from ops.manual_override import ManualOverrideManager
            
            manager = ManualOverrideManager(db_path)
            
            stats = manager.get_override_stats()
            
            assert stats['total_overrides'] == 5
            assert stats['active_overrides'] == 3
            assert stats['overrides_by_type']['single_group'] == 2
            assert stats['overrides_by_reason']['user_preference'] == 2
            assert stats['override_percentage'] == 60.0  # 3/5 * 100


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])