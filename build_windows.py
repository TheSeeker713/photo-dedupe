#!/usr/bin/env python3
"""
Step 27 - Windows Packaging Build Script
Automates the PyInstaller build process for creating a Windows distribution.
"""

import subprocess
import sys
import shutil
from pathlib import Path
import os

def setup_environment():
    """Setup the build environment."""
    print("🏗️  Setting up build environment...")
    
    # Ensure we're in the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Clean previous builds
    dist_dir = project_root / 'dist'
    build_dir = project_root / 'build'
    
    if dist_dir.exists():
        print(f"🧹 Cleaning previous dist: {dist_dir}")
        shutil.rmtree(dist_dir)
    
    if build_dir.exists():
        print(f"🧹 Cleaning previous build: {build_dir}")
        shutil.rmtree(build_dir)
    
    return project_root

def check_dependencies():
    """Check that PyInstaller and required packages are available."""
    print("📦 Checking dependencies...")
    
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("❌ PyInstaller not found. Installing...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
        print("✅ PyInstaller installed")
    
    # Check other critical dependencies
    required_packages = [
        'PySide6', 'Pillow', 'pillow_heif', 'imagehash', 
        'opencv-python', 'piexif', 'xxhash', 'blake3',
        'send2trash', 'platformdirs', 'loguru', 'tqdm'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Installing missing packages...")
        subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing_packages, check=True)
        print("✅ Missing packages installed")
    else:
        print("✅ All required packages found")

def verify_assets():
    """Verify that required assets exist."""
    print("🎨 Verifying assets...")
    
    project_root = Path.cwd()
    assets_dir = project_root / 'assets'
    
    # Check for app icon
    icon_path = assets_dir / 'app_icon.ico'
    if not icon_path.exists():
        print("⚠️  App icon not found, creating...")
        subprocess.run([sys.executable, str(assets_dir / 'create_icon.py')], check=True)
    
    if icon_path.exists():
        print(f"✅ App icon found: {icon_path}")
    else:
        print("❌ Failed to create app icon")
        return False
    
    # Check for version info
    version_info = project_root / 'version_info.txt'
    if version_info.exists():
        print(f"✅ Version info found: {version_info}")
    else:
        print("❌ Version info not found")
        return False
    
    return True

def run_pyinstaller():
    """Run PyInstaller with the spec file."""
    print("🔨 Running PyInstaller...")
    
    spec_file = Path.cwd() / 'photo_dedupe.spec'
    if not spec_file.exists():
        print(f"❌ Spec file not found: {spec_file}")
        return False
    
    try:
        # Run PyInstaller
        cmd = [sys.executable, '-m', 'PyInstaller', '--clean', str(spec_file)]
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ PyInstaller completed successfully")
            return True
        else:
            print(f"❌ PyInstaller failed with return code {result.returncode}")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error running PyInstaller: {e}")
        return False

def verify_build():
    """Verify that the build was successful."""
    print("🔍 Verifying build...")
    
    dist_dir = Path.cwd() / 'dist' / 'PhotoDedupe'
    exe_file = dist_dir / 'PhotoDedupe.exe'
    
    if not dist_dir.exists():
        print(f"❌ Distribution directory not found: {dist_dir}")
        return False
    
    if not exe_file.exists():
        print(f"❌ Executable not found: {exe_file}")
        return False
    
    print(f"✅ Executable found: {exe_file}")
    
    # Check file size
    exe_size = exe_file.stat().st_size / (1024 * 1024)  # MB
    print(f"📊 Executable size: {exe_size:.1f} MB")
    
    # List directory contents
    print(f"📁 Distribution contents:")
    for item in sorted(dist_dir.iterdir()):
        if item.is_file():
            size = item.stat().st_size / 1024  # KB
            print(f"   📄 {item.name} ({size:.1f} KB)")
        else:
            print(f"   📁 {item.name}/")
    
    return True

def create_test_folder():
    """Create a small test folder for acceptance testing."""
    print("📂 Creating test folder...")
    
    test_dir = Path.cwd() / 'test_images'
    test_dir.mkdir(exist_ok=True)
    
    # Create a simple test image using Pillow
    try:
        from PIL import Image, ImageDraw
        
        # Create a few simple test images
        for i in range(3):
            img = Image.new('RGB', (100, 100), color=(255 * i // 2, 100, 150))
            draw = ImageDraw.Draw(img)
            draw.text((20, 40), f"Test {i+1}", fill=(255, 255, 255))
            img.save(test_dir / f'test_image_{i+1}.jpg')
        
        # Create a duplicate
        shutil.copy2(test_dir / 'test_image_1.jpg', test_dir / 'test_image_1_copy.jpg')
        
        print(f"✅ Test images created in: {test_dir}")
        return test_dir
        
    except Exception as e:
        print(f"⚠️  Could not create test images: {e}")
        return test_dir

def main():
    """Main build process."""
    print("=" * 60)
    print("🏗️  Step 27 - Windows Packaging Build")
    print("=" * 60)
    
    try:
        # Setup
        project_root = setup_environment()
        check_dependencies()
        
        if not verify_assets():
            print("❌ Asset verification failed")
            return False
        
        # Build
        if not run_pyinstaller():
            print("❌ Build failed")
            return False
        
        # Verify
        if not verify_build():
            print("❌ Build verification failed")
            return False
        
        # Create test data
        test_dir = create_test_folder()
        
        print("=" * 60)
        print("🎉 Build completed successfully!")
        print("=" * 60)
        print(f"📦 Distribution: {project_root / 'dist' / 'PhotoDedupe'}")
        print(f"🎯 Executable: {project_root / 'dist' / 'PhotoDedupe' / 'PhotoDedupe.exe'}")
        print(f"🧪 Test folder: {test_dir}")
        print()
        print("🚀 To test the build:")
        print(f"   1. Navigate to: {project_root / 'dist' / 'PhotoDedupe'}")
        print("   2. Double-click PhotoDedupe.exe")
        print(f"   3. Test scanning the folder: {test_dir}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Build failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)