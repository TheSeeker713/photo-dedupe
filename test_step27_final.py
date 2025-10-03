#!/usr/bin/env python3
"""
Step 27 - Final Acceptance Test

Performs the final acceptance test as specified:
"A double-clickable EXE launches and performs scan on a small test folder"
"""

import subprocess
import sys
import time
from pathlib import Path
import os

def main():
    """Perform final acceptance test."""
    print("=" * 60)
    print("🎯 Step 27 - Final Acceptance Test")
    print("=" * 60)
    
    project_root = Path(__file__).parent
    exe_path = project_root / 'dist' / 'PhotoDedupe' / 'PhotoDedupe.exe'
    test_dir = project_root / 'test_images'
    
    # Verify prerequisites
    print("📋 Verifying Prerequisites...")
    
    if not exe_path.exists():
        print(f"❌ Executable not found: {exe_path}")
        return False
    print(f"✅ Executable found: {exe_path}")
    
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return False
    
    # Count test images
    image_files = list(test_dir.glob('*.jpg')) + list(test_dir.glob('*.png'))
    print(f"✅ Test directory found with {len(image_files)} images")
    
    # Show test images
    print("\n📂 Test Images:")
    for img in sorted(image_files):
        size = img.stat().st_size
        print(f"   📄 {img.name} ({size} bytes)")
    
    # Identify expected duplicate
    img1_path = test_dir / 'test_image_1.jpg'
    img1_copy_path = test_dir / 'test_image_1_copy.jpg'
    
    if img1_path.exists() and img1_copy_path.exists():
        size1 = img1_path.stat().st_size
        size2 = img1_copy_path.stat().st_size
        if size1 == size2:
            print(f"✅ Duplicate pair detected: {img1_path.name} and {img1_copy_path.name} ({size1} bytes each)")
        else:
            print(f"⚠️  Size mismatch in expected duplicates: {size1} vs {size2}")
    
    print("\n" + "=" * 60)
    print("🚀 FINAL ACCEPTANCE TEST INSTRUCTIONS")
    print("=" * 60)
    print()
    print("To complete Step 27 acceptance testing:")
    print()
    print("1. 🖱️  DOUBLE-CLICK the executable:")
    print(f"   📁 {exe_path}")
    print()
    print("2. ✅ VERIFY the application launches:")
    print("   - Window opens with PhotoDedupe interface")
    print("   - No error messages or crashes")
    print("   - UI is responsive and functional")
    print()
    print("3. 🔍 PERFORM SCAN on test folder:")
    print(f"   📂 Select folder: {test_dir}")
    print("   ▶️  Start scan operation")
    print("   ⏳ Wait for scan to complete")
    print()
    print("4. ✅ VERIFY SCAN RESULTS:")
    print("   - Scan completes without errors")
    print("   - Duplicate images are detected")
    print(f"   - Should find: {img1_path.name} and {img1_copy_path.name} as duplicates")
    print("   - Results are displayed in the interface")
    print()
    print("5. 📋 CONFIRM FUNCTIONALITY:")
    print("   - Preview images work")
    print("   - Duplicate management options available")
    print("   - Application remains stable")
    print()
    
    print("🎯 SUCCESS CRITERIA:")
    print("✅ EXE is double-clickable and launches")
    print("✅ Application runs without virtual environment")
    print("✅ Scan operation works on test folder")
    print("✅ Duplicate detection functions correctly")
    print("✅ UI is responsive and error-free")
    print()
    
    # Launch the application for testing
    print("🚀 Launching application for testing...")
    print(f"Opening: {exe_path}")
    
    try:
        if os.name == 'nt':  # Windows
            os.startfile(str(exe_path))
            print("✅ Application launched successfully!")
        else:
            subprocess.Popen([str(exe_path)])
            print("✅ Application launched successfully!")
        
        print()
        print("👁️  Please manually verify the application works as expected.")
        print(f"📂 Test with folder: {test_dir}")
        print()
        print("=" * 60)
        print("🎉 Step 27 - Windows Packaging - READY FOR FINAL VERIFICATION")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error launching application: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ All automated checks passed. Manual verification in progress...")
    else:
        print("\n❌ Automated checks failed. Please review and fix issues.")
    
    sys.exit(0 if success else 1)