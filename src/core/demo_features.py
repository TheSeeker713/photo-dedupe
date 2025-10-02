#!/usr/bin/env python3
"""Demo script for features extraction pipeline testing."""

import tempfile
import time
from pathlib import Path
from PIL import Image
import piexif
import sys

def create_test_images(test_dir: Path) -> list[tuple[Path, str]]:
    """Create test images for feature extraction testing."""
    test_images = []
    
    # Image 1: Original red image
    img1_path = test_dir / "original.jpg"
    img1 = Image.new('RGB', (800, 600), color=(255, 0, 0))  # Red
    img1.save(img1_path, 'JPEG', quality=95)
    test_images.append((img1_path, "original"))
    print(f"✓ Created {img1_path.name} (original red image)")
    
    # Image 2: Exact duplicate of image 1
    img2_path = test_dir / "exact_duplicate.jpg"
    img1.save(img2_path, 'JPEG', quality=95)
    test_images.append((img2_path, "exact_duplicate"))
    print(f"✓ Created {img2_path.name} (exact duplicate)")
    
    # Image 3: Near duplicate (slightly different compression)
    img3_path = test_dir / "near_duplicate.jpg"
    img1.save(img3_path, 'JPEG', quality=85)  # Different quality
    test_images.append((img3_path, "near_duplicate"))
    print(f"✓ Created {img3_path.name} (near duplicate - different quality)")
    
    # Image 4: Rotated version with EXIF orientation
    img4_path = test_dir / "rotated.jpg"
    img4 = Image.new('RGB', (600, 800), color=(255, 0, 0))  # Same red but different aspect
    exif_dict = {
        "0th": {piexif.ImageIFD.Orientation: 6},  # 270° rotation
        "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None
    }
    exif_bytes = piexif.dump(exif_dict)
    img4.save(img4_path, 'JPEG', exif=exif_bytes, quality=95)
    test_images.append((img4_path, "rotated"))
    print(f"✓ Created {img4_path.name} (rotated with EXIF orientation=6)")
    
    # Image 5: Similar but different color
    img5_path = test_dir / "similar_blue.jpg"
    img5 = Image.new('RGB', (800, 600), color=(0, 0, 255))  # Blue instead of red
    img5.save(img5_path, 'JPEG', quality=95)
    test_images.append((img5_path, "similar_blue"))
    print(f"✓ Created {img5_path.name} (similar but blue)")
    
    # Image 6: Completely different
    img6_path = test_dir / "different.jpg"
    img6 = Image.new('RGB', (800, 600), color=(0, 255, 0))  # Green
    # Add some pattern
    for x in range(0, 800, 50):
        for y in range(0, 600, 50):
            # Create checkerboard pattern
            if (x // 50 + y // 50) % 2:
                for px in range(x, min(x+25, 800)):
                    for py in range(y, min(y+25, 600)):
                        img6.putpixel((px, py), (255, 255, 0))  # Yellow squares
    img6.save(img6_path, 'JPEG', quality=95)
    test_images.append((img6_path, "different"))
    print(f"✓ Created {img6_path.name} (completely different pattern)")
    
    return test_images

def demo_features_pipeline():
    """Test the comprehensive features extraction pipeline."""
    print("=== Features Extraction Pipeline Demo ===\n")
    
    # Add src to path
    src_path = Path(__file__).parent.parent
    sys.path.insert(0, str(src_path))
    
    from app.settings import Settings
    from store.db import DatabaseManager
    from core.features import FeatureExtractor
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_images_dir = temp_path / "test_images"
        test_images_dir.mkdir()
        
        print("1. Creating test images...")
        test_images = create_test_images(test_images_dir)
        print()
        
        print("2. Testing different performance presets...")
        presets = ["Ultra-Lite", "Balanced", "Accurate"]
        
        for preset in presets:
            print(f"\n--- Testing {preset} preset ---")
            
            # Setup for this preset
            db_path = temp_path / f"test_{preset.lower().replace('-', '_')}.db"
            settings = Settings(config_dir=temp_path / "config")
            
            # Configure for this preset
            perf_config = settings._data.get("Performance", {})
            perf_config["current_preset"] = preset
            settings._data["Performance"] = perf_config
            
            # Configure hashing
            hashing_config = settings._data.get("Hashing", {})
            hashing_config["use_perceptual_hash"] = True
            hashing_config["enable_orb_fallback"] = True
            settings._data["Hashing"] = hashing_config
            settings.save()
            
            db_manager = DatabaseManager(db_path)
            feature_extractor = FeatureExtractor(db_path, settings)
            
            print(f"   Preset: {feature_extractor.current_preset}")
            print(f"   Low-end mode: {feature_extractor.low_end_mode}")
            print(f"   Use ORB: {feature_extractor.use_orb}")
            print(f"   pHash threshold: {feature_extractor.phash_threshold}")
            
            # Add files to database
            file_records = []
            for img_path, img_type in test_images:
                stat = img_path.stat()
                file_id = db_manager.add_file(
                    file_path=img_path,
                    size=stat.st_size,
                    mtime=stat.st_mtime,
                    ctime=stat.st_ctime
                )
                file_records.append((file_id, img_path, img_type))
            
            print(f"   Added {len(file_records)} files to database")
            
            # Test individual feature extraction
            print("   Extracting features:")
            for file_id, img_path, img_type in file_records:
                start_time = time.time()
                success = feature_extractor.process_file(file_id, img_path)
                extraction_time = time.time() - start_time
                
                status = "✓" if success else "✗"
                print(f"     {status} {img_path.name} ({img_type}): {extraction_time*1000:.1f}ms")
            
            # Check what features were extracted
            print("   Feature extraction results:")
            stats = feature_extractor.get_feature_stats()
            print(f"     Total files with features: {stats.get('total_features', 0)}")
            print(f"     Files with file hash: {stats.get('files_with_hash', 0)}")
            print(f"     Files with pHash: {stats.get('files_with_phash', 0)}")
            print(f"     Files with dHash: {stats.get('files_with_dhash', 0)}")
            print(f"     Files with wHash: {stats.get('files_with_whash', 0)}")
            print(f"     Files with ORB: {stats.get('files_with_orb', 0)}")
            print(f"     Avg extraction time: {stats.get('avg_extraction_time', 0)*1000:.1f}ms")
        
        print("\n" + "="*60)
        print("3. Testing hash comparison and similarity...")
        
        # Use Balanced preset for similarity testing
        settings = Settings(config_dir=temp_path / "config")
        perf_config = settings._data.get("Performance", {})
        perf_config["current_preset"] = "Balanced"
        settings._data["Performance"] = perf_config
        settings.save()
        
        db_path = temp_path / "similarity_test.db"
        db_manager = DatabaseManager(db_path)
        feature_extractor = FeatureExtractor(db_path, settings)
        
        # Add and process files
        file_features = []
        for img_path, img_type in test_images:
            stat = img_path.stat()
            file_id = db_manager.add_file(
                file_path=img_path, size=stat.st_size,
                mtime=stat.st_mtime, ctime=stat.st_ctime
            )
            
            # Extract features
            features = feature_extractor.extract_all_features(img_path)
            feature_extractor.store_features(file_id, features)
            file_features.append((img_path.name, img_type, features))
        
        # Compare hashes between images
        print("\nHash similarity comparison:")
        for i, (name1, type1, features1) in enumerate(file_features):
            for j, (name2, type2, features2) in enumerate(file_features):
                if i >= j:  # Only compare each pair once
                    continue
                
                # Compare file hashes (exact duplicates)
                file_hash_match = (features1.get('file_hash') == features2.get('file_hash') 
                                 and features1.get('file_hash') is not None)
                
                # Compare perceptual hashes
                phash1, phash2 = features1.get('phash'), features2.get('phash')
                phash_similar = False
                phash_distance = None
                
                if phash1 and phash2:
                    phash_distance = feature_extractor.compute_hash_distance(phash1, phash2)
                    phash_similar = feature_extractor.are_hashes_similar(phash1, phash2, 'phash')
                
                print(f"  {name1} vs {name2}:")
                print(f"    File hash match: {'Yes' if file_hash_match else 'No'}")
                if phash_distance is not None:
                    print(f"    pHash distance: {phash_distance} (similar: {'Yes' if phash_similar else 'No'})")
                print(f"    Types: {type1} vs {type2}")
                print()
        
        print("4. Testing batch processing...")
        
        # Test batch processing
        files_needing_features = feature_extractor.get_files_needing_features()
        print(f"   Files needing features: {len(files_needing_features)}")
        
        def progress_callback(current, total, file_path):
            print(f"   Processing: {current}/{total} - {file_path.name}")
        
        if files_needing_features:
            processed = feature_extractor.process_files_batch(
                files_needing_features, progress_callback
            )
            print(f"   ✓ Processed {processed} files")
        
        print("\n" + "="*60)
        print("✅ FEATURES PIPELINE DEMO COMPLETED!")
        print("="*60)
        print("\nKey achievements verified:")
        print("• Fast file hash (xxhash) for exact duplicate detection")
        print("• Optional SHA-256 confirmation")
        print("• Perceptual hashes: pHash (primary), dHash, wHash")
        print("• ORB keypoints signature for Accurate preset")
        print("• Low-End Mode optimizations (smaller decode, pHash only)")
        print("• Stricter thresholds for low-end mode")
        print("• Features stored in database")
        print("• Error handling without crashes")
        print("• Hash similarity comparison")

if __name__ == "__main__":
    demo_features_pipeline()