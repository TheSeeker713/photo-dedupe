# Step 22 — Conflict handling & manual overrides

## Overview

Step 22 implements a comprehensive manual override system for original selection conflicts, providing users with the ability to override automatic original selection decisions and maintain those preferences across rescans.

## Features Implemented

### 1. Manual Override Database System

**File**: `src/ops/manual_override.py`

- **Manual Override Manager**: Handles database operations for storing and retrieving manual overrides
- **Conflict Detection**: Identifies when user preferences differ from automatic selection
- **Override Persistence**: Maintains manual selections across application restarts and rescans
- **Override Statistics**: Tracks usage patterns and provides reporting

**Key Components**:
- `ManualOverrideManager`: Core database operations
- `ConflictHandler`: Qt-based conflict resolution system
- `ManualOverride` dataclass: Override record structure
- `ConflictInfo` dataclass: Conflict information structure

### 2. Non-blocking Banner UI System

**File**: `src/gui/conflict_banner.py`

- **Conflict Banner**: Non-intrusive notification widget for original selection conflicts
- **Banner Manager**: Handles multiple concurrent banners with queueing
- **User Interaction**: Provides clear options for resolving conflicts
- **Animated Display**: Smooth slide-in/slide-out animations

**User Options**:
- "Make this the original for this group" (single group override)
- "Make this rule default going forward" (default rule for future selections)
- Optional notes field for documenting decisions
- Auto-dismiss with configurable timeout

### 3. GroupingEngine Integration

**Enhanced**: `src/ops/grouping.py`

- **Override-Aware Selection**: `_select_original` method now checks for manual overrides
- **Conflict Detection**: Identifies when automatic selection differs from user preference
- **Missing File Handling**: Gracefully handles when manually selected originals disappear
- **Statistics Integration**: Tracks override usage in grouping statistics

**New Methods**:
- `check_override_conflicts()`: Detect conflicts after rescanning
- `apply_manual_override()`: Apply user override decisions
- `remove_manual_override()`: Remove overrides and revert to automatic selection

### 4. Database Schema Enhancements

**New Table**: `manual_overrides`

```sql
CREATE TABLE manual_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    original_file_id INTEGER NOT NULL,
    auto_original_id INTEGER NOT NULL,
    override_type TEXT NOT NULL CHECK (override_type IN ('single_group', 'default_rule')),
    reason TEXT NOT NULL CHECK (reason IN ('user_preference', 'quality_better', 'format_preference', 'manual_selection', 'algorithm_error')),
    created_at REAL NOT NULL,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
    FOREIGN KEY (original_file_id) REFERENCES files (id) ON DELETE CASCADE,
    FOREIGN KEY (auto_original_id) REFERENCES files (id) ON DELETE CASCADE,
    UNIQUE (group_id, is_active) -- Only one active override per group
);
```

## Workflow

### 1. Conflict Detection

When the system detects that automatic original selection differs from user preference:

1. **Banner Display**: Non-blocking banner appears showing both options
2. **File Comparison**: Side-by-side display of automatic vs. user-preferred files
3. **User Decision**: Choice between automatic selection or user preference
4. **Override Options**: Single group vs. default rule for future selections

### 2. Override Application

When user makes a decision:

1. **Database Recording**: Override stored with metadata (reason, timestamp, notes)
2. **Group Update**: `group_members` table updated to reflect new original
3. **Conflict Resolution**: Banner dismissed and conflict marked as resolved
4. **Statistics Update**: Override tracking statistics updated

### 3. Persistence Across Rescans

On subsequent scans:

1. **Override Check**: System checks for existing overrides before applying automatic selection
2. **File Validation**: Verifies manually selected original still exists
3. **Graceful Fallback**: Reverts to automatic selection if manual original disappears
4. **Conflict Notification**: Shows banner if new conflicts arise

## Usage Examples

### Basic Override Application

```python
from ops.grouping import GroupingEngine
from pathlib import Path

# Initialize engine
engine = GroupingEngine(db_path, settings)

# Apply manual override
success = engine.apply_manual_override(
    group_id=123,
    new_original_id=456,
    override_type="single_group",
    reason="user_preference",
    notes="User prefers this file for better quality"
)
```

### Conflict Detection

```python
# Check for conflicts after rescan
conflicts = engine.check_override_conflicts()

for conflict in conflicts:
    print(f"Group {conflict['group_id']}: "
          f"Auto selected {conflict['auto_original_path']}, "
          f"User prefers {conflict['manual_original_path']}")
```

### Banner System Integration

```python
from gui.conflict_banner import ConflictBannerManager, ConflictData

# Create banner manager
banner_manager = ConflictBannerManager(parent_widget)

# Show conflict
conflict = ConflictData(
    group_id=1,
    auto_file_path="/path/to/auto.jpg",
    user_file_path="/path/to/user.jpg",
    auto_file_id=100,
    user_file_id=101,
    reason="Higher resolution detected",
    confidence=0.85
)

banner_manager.show_conflict(conflict, auto_dismiss_ms=30000)

# Connect to override application
banner_manager.override_applied.connect(handle_override_decision)
```

## Configuration Options

### Banner Settings

- **Auto-dismiss timeout**: Default 30 seconds
- **Max concurrent banners**: Default 1
- **Animation duration**: 300ms slide animations

### Override Behavior

- **Override types**: `single_group` or `default_rule`
- **Reason categories**: `user_preference`, `quality_better`, `format_preference`, `manual_selection`, `algorithm_error`
- **Conflict detection**: Automatic during rescans

## Testing

### Integration Test

Run the comprehensive integration test:

```bash
python tests/step22_integration_test.py
```

### Unit Tests

Run specific component tests:

```bash
python -m pytest tests/test_step22_manual_overrides.py -v
```

## Statistics and Monitoring

### Override Statistics

- Total overrides created
- Active overrides by type and reason
- Override success/failure rates
- Conflict detection frequency

### Performance Impact

- Minimal overhead during normal grouping
- Database queries optimized with indexes
- Banner system uses efficient Qt animations
- Override checks only when group_id provided

## Error Handling

### Missing Files

When manually selected original disappears:
1. Override automatically deactivated
2. Reverts to automatic selection
3. Conflict logged for user review
4. Statistics updated

### Database Integrity

- Foreign key constraints ensure data consistency
- Unique constraints prevent duplicate active overrides
- Cascading deletes maintain referential integrity

### UI Graceful Degradation

- System works without Qt GUI components
- Fallback behavior for non-GUI environments
- Banner failures don't affect core functionality

## Future Enhancements

### Potential Improvements

1. **Batch Override Operations**: Apply overrides to multiple groups
2. **Machine Learning Integration**: Learn from user preferences
3. **Advanced Conflict Resolution**: More sophisticated conflict detection
4. **Override Export/Import**: Share override rules between installations
5. **Visual Diff Tools**: Enhanced file comparison in banners

### API Extensions

- REST API for external override management
- Webhook notifications for conflict events
- Bulk override operations via command line

## Dependencies

### Required

- SQLite database support
- Python 3.7+ with dataclasses
- Existing grouping and database infrastructure

### Optional

- PySide6/Qt for GUI banner system
- pytest for testing
- Logging framework for diagnostics

## Architecture Benefits

### Maintainability

- Clear separation of concerns
- Modular design with pluggable components
- Comprehensive test coverage
- Extensive documentation

### Performance

- Efficient database schema with indexes
- Minimal impact on core grouping performance
- Lazy loading of override data
- Optimized conflict detection algorithms

### User Experience

- Non-intrusive conflict notifications
- Clear decision options with context
- Persistent preferences across sessions
- Graceful handling of edge cases

---

**Step 22 Status**: ✅ **COMPLETE**

The manual override system provides a comprehensive solution for handling original selection conflicts while maintaining system performance and user experience quality. The implementation supports both GUI and non-GUI environments with graceful degradation and robust error handling.