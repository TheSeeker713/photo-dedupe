# GUI Resources for Photo Deduplicator

This directory contains the PySide6-based GUI application for the photo deduplication tool.

## Files

- `__init__.py` - Module initialization
- `main_window.py` - Main application window with all UI components
- `demo_gui.py` - Demo script to test the GUI
- `test_step15_acceptance.py` - Acceptance tests for Step 15
- `launch.py` - Convenience launcher script

## Features

### Main Window Components

1. **Top Toolbar**:
   - 📁 Pick Folder(s) - Select directories to scan
   - Include Subfolders checkbox - Recursive scanning option
   - ▶️ Start/⏸️ Pause/⏯️ Resume - Scan control buttons
   - Dry Run checkbox - Preview mode without actual changes
   - 🗑️ Delete Selected - Remove duplicate files
   - 📊 Export Report - Generate analysis reports
   - ⚙️ Settings - Application configuration

2. **Left Pane**:
   - Filters dropdown (All, Exact, Near, Safe Only, Conflicts)
   - Groups list with duplicate group information
   - Space-saved estimate display

3. **Right Pane**:
   - Overview tab: Original file preview + candidates grid
   - Compare tab: Side-by-side file comparison with zoom controls
   - Similarity scores and file details

4. **Status Bar**:
   - Worker status and progress indicators
   - Thread count display
   - Cache status information

### Key Classes

- `MainWindow` - Main application window
- `GroupsListWidget` - Tree widget for duplicate groups
- `FilePreviewWidget` - Individual file preview with thumbnail
- `CandidateGridWidget` - Grid layout for candidate files
- `CompareWidget` - Side-by-side comparison view
- `WorkerStatusWidget` - Status display for background operations

## Usage

### Running the Application

```bash
# Launch GUI directly
python src/gui/main_window.py

# Or use the launcher
python src/gui/launch.py

# Or run the demo
python src/gui/demo_gui.py
```

### Running Tests

```bash
# Run acceptance tests
python src/gui/test_step15_acceptance.py
```

## Sample Data

The application includes sample data for demonstration:
- 4 duplicate groups with different types (exact, near, safe, conflict)
- File information with sizes, roles, and similarity scores
- Space reclamation estimates

## Integration

The GUI integrates with the core photo deduplication components:
- `Settings` - Application configuration
- `DatabaseManager` - File and group data storage
- `CacheManager` - Thumbnail and cache management
- `DiagnosticsPanel` - System monitoring
- `DuplicateGrouper` - Duplicate detection logic

## Dependencies

- PySide6 - Qt6 Python bindings for GUI
- Core application modules (settings, database, cache, etc.)

## Architecture

The GUI follows a modular design with:
- Separation of concerns between UI and business logic
- Signal/slot communication between components
- Responsive layout with proper widget hierarchies
- Error handling and graceful fallbacks