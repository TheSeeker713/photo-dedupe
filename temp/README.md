# 🗂️ Temporary Storage - Legacy Test Files

This folder contains legacy test files that were moved from the main project structure during cleanup. These files were development validation tests for individual steps that are no longer actively needed since the project now has a complete, integrated application.

## 📋 Moved Files

### Core System Tests (Steps 10, 13-14)
- **test_step10_acceptance.py** - Near-duplicate search (BK-tree) validation
- **test_step13_acceptance.py** - Concurrency system acceptance tests
- **test_step13_simple.py** - Concurrency system simplified tests  
- **test_step14_acceptance.py** - CLI interface validation tests

### Operations Tests (Steps 11-12)
- **test_step11_acceptance.py** - Grouping engine validation
- **test_step12_acceptance.py** - Safe duplicate classification acceptance tests
- **test_step12_simple.py** - Safe duplicate classification simplified tests

### GUI Tests (Step 15)
- **test_step15_acceptance.py** - GUI shell validation tests

## 🔍 Why These Were Moved

### **Development Context**
These test files were created during incremental development to validate individual components as they were built. They served their purpose during the development phase but are now superseded by:

1. **Integrated Testing**: Current test files (test_step16.py, test_step17.py, test_step18.py) test complete workflows
2. **Application-Level Validation**: The main application now provides comprehensive testing of all features together
3. **Component Demos**: Individual component demos (demo_*.py files) provide better component-level testing

### **Current Active Tests**
The following test files remain active in the main project:
- `test_step16.py` - Selection model & keyboard shortcuts (current feature)
- `test_step17.py` - Delete manager & safe deletion (current feature)
- `test_step18.py` - Reports & export system (current feature)
- `test_dot_fix.py` - Easter egg game mechanics validation
- `test_easter_egg_simple.py` - Easter egg component validation
- `test_main_easter_egg.py` - Main application integration

### **Integration Status**
All features tested by these legacy files are now:
- ✅ Fully integrated into the main application
- ✅ Tested through application-level workflows
- ✅ Validated through current step tests (16-18)
- ✅ Accessible via GUI and CLI interfaces

## 📁 File Status

### **Safe to Archive**
These files can be safely archived or deleted as:
- All tested functionality is now part of the integrated application
- Component-level testing is handled by demo files
- Application-level testing is handled by current test files
- No external dependencies or references to these files exist

### **Restoration Instructions**
If any of these tests need to be restored:
1. Move the desired file back to its original location in `src/`
2. Update any import paths if the project structure has changed
3. Run the test to verify it still works with current code

## 🎯 Project Cleanup Benefits

Moving these files provides:
- **Cleaner Structure**: Reduced clutter in source directories
- **Clear Current Tests**: Only active, current tests remain visible
- **Better Navigation**: Developers can focus on current functionality
- **Preserved History**: Legacy tests are preserved but not in the way

## 📅 Archive Date

**Moved**: October 2, 2025  
**Reason**: Project cleanup and organization  
**Project Status**: Feature complete through Step 18  

---

*These files represent the development journey of the photo deduplication tool. While no longer actively needed, they document the incremental validation approach used during development.* 📚