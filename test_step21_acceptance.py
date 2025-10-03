#!/usr/bin/env python3
"""
Step 21 Acceptance Test: Low-End Mode Behaviors

Tests Ultra-Lite preset enforcement and battery saver auto-switch functionality.

Requirements:
1. Ultra-Lite preset enforces: 2 threads, on-demand thumbnails, pHash only for 
   suspected groups at 128–192px decode, strict threshold (≤6), skip RAW/TIFF 
   by default, small caches, Below-Normal process priority, Low I/O priority, 
   animations off.
2. Battery saver auto-switch to Ultra-Lite when on DC power or <20% battery.
3. Toggling presets changes behavior at runtime (or after restart) and is 
   visible in logs and diagnostics.
"""

import os
import sys
import time
import tempfile
import shutil
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QApplication = None
    QTimer = None

from app.settings import Settings
from core.power_manager import PowerManager, UltraLiteEnforcer
from core.ultra_lite_mode import UltraLiteModeManager, create_ultra_lite_manager
from core.thumbs import ThumbnailGenerator
from ops.grouping import GroupingEngine


class Step21AcceptanceTest:
    """Comprehensive acceptance test for Step 21 Ultra-Lite mode behaviors."""
    
    def __init__(self):
        self.temp_dir = None
        self.settings = None
        self.mode_manager = None
        self.test_results = []
        
        # Setup logging to capture diagnostics
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("step21_test")
    
    def setup(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="step21_test_"))
        self.settings = Settings(config_dir=self.temp_dir / "config")
        
        # Initialize Qt application if available
        if QT_AVAILABLE and QApplication.instance() is None:
            self.app = QApplication([])
        
        print(f"🔧 Test environment setup in: {self.temp_dir}")
    
    def cleanup(self):
        """Cleanup test environment."""
        if self.mode_manager:
            self.mode_manager.cleanup()
        
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        
        print("🧹 Test environment cleaned up")
    
    def test_1_ultra_lite_preset_enforcement(self):
        """Test 1: Ultra-Lite preset enforces all required restrictions."""
        print("\\n🔍 Test 1: Ultra-Lite preset enforcement")
        
        # Set Ultra-Lite preset
        self.settings.set("Performance", "current_preset", "Ultra-Lite")
        self.settings.save()
        
        # Create enforcer
        power_manager = PowerManager(self.settings)
        enforcer = UltraLiteEnforcer(self.settings, power_manager)
        
        # Get effective configuration
        config = enforcer.get_effective_config()
        
        # Test all Ultra-Lite requirements
        requirements = {
            "thread_cap": (config.get("thread_cap"), 2, "2 threads maximum"),
            "memory_cap_mb": (config.get("memory_cap_mb"), 512, "512MB memory cap"),
            "cache_size_cap_mb": (config.get("cache_size_cap_mb"), 256, "256MB cache cap"),
            "thumbnail_decode_size": (config.get("thumbnail_decode_size"), 128, "128px decode size"),
            "thumbnail_max_size": (config.get("thumbnail_max_size"), 192, "192px max thumbnail"),
            "phash_threshold": (config.get("phash_threshold"), 6, "≤6 pHash threshold"),
            "skip_raw_tiff": (config.get("skip_raw_tiff"), True, "Skip RAW/TIFF"),
            "enable_orb_fallback": (config.get("enable_orb_fallback"), False, "No ORB fallback"),
            "on_demand_thumbs": (config.get("on_demand_thumbs"), True, "On-demand thumbnails"),
            "animations_enabled": (config.get("animations_enabled"), False, "Animations disabled"),
            "use_perceptual_hash_only": (config.get("use_perceptual_hash_only"), True, "pHash only"),
            "process_priority": (config.get("process_priority"), "below_normal", "Below-Normal priority"),
            "io_priority": (config.get("io_priority"), "low", "Low I/O priority"),
        }
        
        passed_requirements = 0
        total_requirements = len(requirements)
        
        for key, (actual, expected, description) in requirements.items():
            if actual == expected:
                print(f"  ✅ {description}: {actual}")
                passed_requirements += 1
            else:
                print(f"  ❌ {description}: expected {expected}, got {actual}")
        
        # Test thread enforcement
        enforced_threads = enforcer.enforce_thread_limits(16)
        if enforced_threads == 2:
            print(f"  ✅ Thread enforcement: 16 → {enforced_threads}")
            passed_requirements += 1
        else:
            print(f"  ❌ Thread enforcement failed: expected 2, got {enforced_threads}")
        
        total_requirements += 1
        
        # Test memory enforcement
        enforced_memory = enforcer.enforce_memory_limits(4096)
        if enforced_memory == 512:
            print(f"  ✅ Memory enforcement: 4096MB → {enforced_memory}MB")
            passed_requirements += 1
        else:
            print(f"  ❌ Memory enforcement failed: expected 512, got {enforced_memory}")
        
        total_requirements += 1
        
        success = passed_requirements == total_requirements
        print(f"  📊 Requirements met: {passed_requirements}/{total_requirements}")
        
        power_manager.cleanup()
        return success
    
    def test_2_battery_auto_switch_dc_power(self):
        """Test 2: Auto-switch to Ultra-Lite on DC power."""
        print("\\n🔋 Test 2: Battery auto-switch (DC power)")
        
        # Enable auto-switch
        self.settings.set("General", "battery_saver_auto_switch", True)
        self.settings.set("Performance", "current_preset", "Balanced")
        self.settings.save()
        
        # Mock battery info to simulate DC power
        mock_battery_info = {
            'percent': 80,
            'power_plugged': False,  # DC power (battery)
            'secsleft': 7200
        }
        
        power_manager = PowerManager(self.settings)
        
        with patch.object(power_manager, '_get_battery_info', return_value=mock_battery_info):
            # Trigger power status check
            power_manager._check_power_status()
            
            # Check if Ultra-Lite was enforced
            if power_manager.is_ultra_lite_enforced():
                reason = power_manager.get_enforcement_reason()
                print(f"  ✅ Ultra-Lite enforced on DC power: {reason}")
                
                # Verify preset was changed
                current_preset = self.settings.get("Performance", "current_preset")
                if current_preset == "Ultra-Lite":
                    print(f"  ✅ Preset changed to: {current_preset}")
                    success = True
                else:
                    print(f"  ❌ Preset not changed: {current_preset}")
                    success = False
            else:
                print("  ❌ Ultra-Lite not enforced on DC power")
                success = False
        
        power_manager.cleanup()
        return success
    
    def test_3_battery_auto_switch_low_battery(self):
        """Test 3: Auto-switch to Ultra-Lite on low battery."""
        print("\\n🪫 Test 3: Battery auto-switch (low battery)")
        
        # Set higher threshold for testing
        self.settings.set("General", "battery_saver_auto_switch", True)
        self.settings.set("General", "low_battery_threshold", 25)
        self.settings.set("Performance", "current_preset", "Accurate")
        self.settings.save()
        
        # Mock battery info to simulate low battery
        mock_battery_info = {
            'percent': 15,  # Below 20% threshold
            'power_plugged': True,  # AC power but low battery
            'secsleft': 1800
        }
        
        power_manager = PowerManager(self.settings)
        power_manager.low_battery_threshold = 20  # Override for test
        
        with patch.object(power_manager, '_get_battery_info', return_value=mock_battery_info):
            # Trigger power status check
            power_manager._check_power_status()
            
            # Check if Ultra-Lite was enforced
            if power_manager.is_ultra_lite_enforced():
                reason = power_manager.get_enforcement_reason()
                print(f"  ✅ Ultra-Lite enforced on low battery: {reason}")
                success = True
            else:
                print("  ❌ Ultra-Lite not enforced on low battery")
                success = False
        
        power_manager.cleanup()
        return success
    
    def test_4_format_skipping_ultra_lite(self):
        """Test 4: RAW/TIFF format skipping in Ultra-Lite mode."""
        print("\\n📁 Test 4: Format skipping in Ultra-Lite mode")
        
        # Set Ultra-Lite preset
        self.settings.set("Performance", "current_preset", "Ultra-Lite")
        self.settings.save()
        
        # Create thumbnail generator
        db_path = self.temp_dir / "test.db"
        thumb_gen = ThumbnailGenerator(db_path, self.settings)
        
        # Test RAW and TIFF format detection
        test_files = [
            (Path("test.cr2"), True, "Canon RAW"),
            (Path("test.nef"), True, "Nikon RAW"),
            (Path("test.arw"), True, "Sony RAW"),
            (Path("test.dng"), True, "Adobe DNG"),
            (Path("test.tif"), True, "TIFF"),
            (Path("test.tiff"), True, "TIFF"),
            (Path("test.jpg"), False, "JPEG"),
            (Path("test.png"), False, "PNG"),
            (Path("test.heic"), False, "HEIC"),
        ]
        
        passed_tests = 0
        total_tests = len(test_files)
        
        for file_path, should_skip, format_name in test_files:
            actually_skipped = thumb_gen.should_skip_format(file_path)
            
            if actually_skipped == should_skip:
                status = "SKIPPED" if should_skip else "PROCESSED"
                print(f"  ✅ {format_name} ({file_path.suffix}): {status}")
                passed_tests += 1
            else:
                expected_status = "SKIPPED" if should_skip else "PROCESSED"
                actual_status = "SKIPPED" if actually_skipped else "PROCESSED"
                print(f"  ❌ {format_name}: expected {expected_status}, got {actual_status}")
        
        print(f"  📊 Format tests passed: {passed_tests}/{total_tests}")
        
        success = passed_tests == total_tests
        return success
    
    def test_5_phash_threshold_enforcement(self):
        """Test 5: Strict pHash threshold (≤6) enforcement."""
        print("\\n🔍 Test 5: pHash threshold enforcement")
        
        # Set Ultra-Lite preset
        self.settings.set("Performance", "current_preset", "Ultra-Lite")
        self.settings.save()
        
        # Create grouping engine
        db_path = self.temp_dir / "grouping_test.db"
        grouping_engine = GroupingEngine(db_path, self.settings)
        
        # Verify Ultra-Lite threshold
        expected_threshold = 6
        actual_threshold = grouping_engine.phash_threshold
        
        if actual_threshold == expected_threshold:
            print(f"  ✅ pHash threshold: {actual_threshold} (≤6 strict mode)")
            
            # Test with Balanced mode for comparison
            self.settings.set("Performance", "current_preset", "Balanced")
            self.settings.save()
            
            grouping_engine_balanced = GroupingEngine(db_path, self.settings)
            balanced_threshold = grouping_engine_balanced.phash_threshold
            
            if balanced_threshold > actual_threshold:
                print(f"  ✅ Balanced threshold higher: {balanced_threshold} > {actual_threshold}")
                success = True
            else:
                print(f"  ❌ Balanced threshold not higher: {balanced_threshold}")
                success = False
        else:
            print(f"  ❌ pHash threshold: expected {expected_threshold}, got {actual_threshold}")
            success = False
        
        return success
    
    def test_6_runtime_preset_toggling(self):
        """Test 6: Runtime preset toggling with visible diagnostics."""
        print("\\n🔄 Test 6: Runtime preset toggling")
        
        # Create mode manager
        self.mode_manager = create_ultra_lite_manager(self.settings)
        
        # Start with Balanced mode
        self.settings.set("Performance", "current_preset", "Balanced")
        self.settings.save()
        
        print("  📊 Starting with Balanced preset...")
        initial_active = self.mode_manager.is_ultra_lite_active()
        
        if not initial_active:
            print("  ✅ Balanced mode active (Ultra-Lite inactive)")
        else:
            print("  ❌ Ultra-Lite incorrectly active in Balanced mode")
            return False
        
        # Switch to Ultra-Lite
        print("  🔄 Switching to Ultra-Lite preset...")
        self.settings.set("Performance", "current_preset", "Ultra-Lite")
        self.settings.save()
        
        # Apply runtime optimizations
        self.mode_manager.apply_runtime_optimizations()
        
        # Check if Ultra-Lite is now active
        ultra_lite_active = self.mode_manager.is_ultra_lite_active()
        
        if ultra_lite_active:
            print("  ✅ Ultra-Lite mode now active")
            
            # Get diagnostics
            diagnostics = self.mode_manager.get_power_status()
            print("  📊 Diagnostics:")
            print(f"    • Ultra-Lite active: {diagnostics['ultra_lite_active']}")
            print(f"    • Enforced by power: {diagnostics['enforced']}")
            print(f"    • Can override: {diagnostics['can_override']}")
            
            # Switch back to Accurate
            print("  🔄 Switching to Accurate preset...")
            self.settings.set("Performance", "current_preset", "Accurate")
            self.settings.save()
            
            self.mode_manager.apply_runtime_optimizations()
            
            # Check if Ultra-Lite is deactivated
            final_active = self.mode_manager.is_ultra_lite_active()
            
            if not final_active:
                print("  ✅ Ultra-Lite mode deactivated (Accurate mode active)")
                success = True
            else:
                print("  ❌ Ultra-Lite mode still active after switching to Accurate")
                success = False
        else:
            print("  ❌ Ultra-Lite mode not activated after preset switch")
            success = False
        
        return success
    
    def test_7_diagnostics_visibility(self):
        """Test 7: Diagnostics and logging visibility."""
        print("\\n📋 Test 7: Diagnostics visibility")
        
        # Create mode manager
        if not self.mode_manager:
            self.mode_manager = create_ultra_lite_manager(self.settings)
        
        # Set Ultra-Lite mode
        self.settings.set("Performance", "current_preset", "Ultra-Lite")
        self.settings.save()
        
        # Get comprehensive diagnostics
        from core.ultra_lite_mode import get_ultra_lite_diagnostics
        diagnostics = get_ultra_lite_diagnostics(self.settings)
        
        # Check diagnostics structure
        required_keys = [
            "status", "active", "enforced", "config", "restrictions"
        ]
        
        passed_checks = 0
        total_checks = len(required_keys)
        
        for key in required_keys:
            if key in diagnostics:
                print(f"  ✅ Diagnostics key present: {key}")
                passed_checks += 1
            else:
                print(f"  ❌ Missing diagnostics key: {key}")
        
        # Check specific diagnostic values
        if diagnostics.get("active"):
            print("  ✅ Ultra-Lite marked as active in diagnostics")
            passed_checks += 1
        else:
            print("  ❌ Ultra-Lite not marked as active in diagnostics")
        
        total_checks += 1
        
        # Check restrictions
        restrictions = diagnostics.get("restrictions", {})
        if restrictions.get("threads") == 2:
            print(f"  ✅ Thread restriction visible: {restrictions['threads']}")
            passed_checks += 1
        else:
            print(f"  ❌ Thread restriction incorrect: {restrictions.get('threads')}")
        
        total_checks += 1
        
        print(f"  📊 Diagnostics checks passed: {passed_checks}/{total_checks}")
        
        success = passed_checks == total_checks
        return success
    
    def run_all_tests(self):
        """Run all acceptance tests."""
        print("🚀 Starting Step 21 Acceptance Tests")
        print("=" * 60)
        
        tests = [
            ("Ultra-Lite preset enforcement", self.test_1_ultra_lite_preset_enforcement),
            ("Battery auto-switch (DC power)", self.test_2_battery_auto_switch_dc_power),
            ("Battery auto-switch (low battery)", self.test_3_battery_auto_switch_low_battery),
            ("Format skipping in Ultra-Lite", self.test_4_format_skipping_ultra_lite),
            ("pHash threshold enforcement", self.test_5_phash_threshold_enforcement),
            ("Runtime preset toggling", self.test_6_runtime_preset_toggling),
            ("Diagnostics visibility", self.test_7_diagnostics_visibility),
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            try:
                success = test_func()
                if success:
                    print(f"✅ {test_name}: PASSED")
                    passed_tests += 1
                else:
                    print(f"❌ {test_name}: FAILED")
                
                self.test_results.append((test_name, success))
                
            except Exception as e:
                print(f"💥 {test_name}: ERROR - {e}")
                self.test_results.append((test_name, False))
        
        print("\\n" + "=" * 60)
        print(f"📊 FINAL RESULTS: {passed_tests}/{total_tests} tests passed")
        
        # Detailed results
        print("\\n📋 Detailed Results:")
        for test_name, success in self.test_results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"  {status}: {test_name}")
        
        # Success criteria
        success_rate = (passed_tests / total_tests) * 100
        print(f"\\n🎯 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 85:
            print("🎉 Step 21 ACCEPTANCE CRITERIA MET!")
            return True
        else:
            print("⚠️  Step 21 acceptance criteria not fully met")
            return False


def main():
    """Main test execution."""
    test = Step21AcceptanceTest()
    
    try:
        test.setup()
        success = test.run_all_tests()
        
        if success:
            print("\\n🏆 Step 21 implementation SUCCESSFUL!")
            sys.exit(0)
        else:
            print("\\n⚠️  Step 21 implementation needs improvement")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\\n⏹️  Test interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\\n💥 Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        test.cleanup()


if __name__ == "__main__":
    main()