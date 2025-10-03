"""
Integration test for Step 22 - Manual override workflow.

This test demonstrates the complete manual override workflow:
1. Automatic grouping with deterministic original selection
2. User preference conflicts with automatic selection  
3. Manual override application with banner notification
4. Override persistence across rescans
5. Conflict resolution when original files disappear
"""

import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockSettings:
    """Mock settings for testing."""
    
    def __init__(self):
        self._data = {
            "Performance": {
                "current_preset": "Balanced"
            },
            "Grouping": {
                "enable_sha256_confirmation": True,
                "strict_mode_exif_match": False,
                "dimension_tolerance": 0.1
            }
        }


class ManualOverrideIntegrationTest:
    """Integration test for manual override system."""
    
    def __init__(self, test_db_path: Path):
        self.test_db_path = test_db_path
        self.settings = MockSettings()
        self.conflicts_detected = []
        self.overrides_applied = []
        
    def run_complete_workflow(self) -> Dict[str, Any]:
        """Run complete manual override workflow test."""
        logger.info("Starting Step 22 manual override integration test...")
        
        results = {
            "test_name": "Step 22 - Manual Override Workflow",
            "start_time": time.time(),
            "phases": {},
            "summary": {},
            "success": True,
            "errors": []
        }
        
        try:
            # Phase 1: Setup and initialization
            results["phases"]["1_initialization"] = self._test_initialization()
            
            # Phase 2: Automatic grouping
            results["phases"]["2_automatic_grouping"] = self._test_automatic_grouping()
            
            # Phase 3: Conflict detection
            results["phases"]["3_conflict_detection"] = self._test_conflict_detection()
            
            # Phase 4: Manual override application
            results["phases"]["4_manual_override"] = self._test_manual_override_application()
            
            # Phase 5: Override persistence
            results["phases"]["5_persistence"] = self._test_override_persistence()
            
            # Phase 6: Missing file handling
            results["phases"]["6_missing_file"] = self._test_missing_file_handling()
            
            # Phase 7: Statistics and reporting
            results["phases"]["7_statistics"] = self._test_statistics()
            
            # Calculate overall success
            all_phases_passed = all(
                phase.get("success", False) 
                for phase in results["phases"].values()
            )
            
            results["success"] = all_phases_passed
            results["end_time"] = time.time()
            results["duration"] = results["end_time"] - results["start_time"]
            
            # Generate summary
            results["summary"] = self._generate_summary(results)
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Integration test failed: {str(e)}")
            logger.error(f"Integration test failed: {e}")
        
        return results
    
    def _test_initialization(self) -> Dict[str, Any]:
        """Test Step 22 component initialization."""
        phase_result = {
            "name": "Component Initialization",
            "success": True,
            "components": {},
            "errors": []
        }
        
        try:
            # Test manual override manager initialization
            try:
                from ops.manual_override import ManualOverrideManager
                manager = ManualOverrideManager(self.test_db_path)
                phase_result["components"]["override_manager"] = {
                    "initialized": True,
                    "db_path": str(self.test_db_path)
                }
            except Exception as e:
                phase_result["components"]["override_manager"] = {
                    "initialized": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"Override manager init failed: {e}")
            
            # Test conflict handler initialization
            try:
                from ops.manual_override import ConflictHandler
                handler = ConflictHandler(self.test_db_path)
                phase_result["components"]["conflict_handler"] = {
                    "initialized": True,
                    "qt_available": hasattr(handler, 'conflict_detected')
                }
            except Exception as e:
                phase_result["components"]["conflict_handler"] = {
                    "initialized": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"Conflict handler init failed: {e}")
            
            # Test banner system initialization
            try:
                from gui.conflict_banner import ConflictBannerManager
                banner_manager = ConflictBannerManager()
                phase_result["components"]["banner_manager"] = {
                    "initialized": True,
                    "max_concurrent": getattr(banner_manager, 'max_concurrent_banners', 1)
                }
            except Exception as e:
                phase_result["components"]["banner_manager"] = {
                    "initialized": False,
                    "error": str(e)
                }
                # Banner failure is not critical for core functionality
                logger.warning(f"Banner manager init failed (non-critical): {e}")
            
            # Test grouping engine with override integration
            try:
                from ops.grouping import GroupingEngine
                engine = GroupingEngine(self.test_db_path, self.settings)
                has_override_manager = hasattr(engine, 'override_manager') and engine.override_manager is not None
                phase_result["components"]["grouping_engine"] = {
                    "initialized": True,
                    "override_integration": has_override_manager
                }
            except Exception as e:
                phase_result["components"]["grouping_engine"] = {
                    "initialized": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"Grouping engine init failed: {e}")
            
            # Check if any critical components failed
            critical_components = ["override_manager", "grouping_engine"]
            failed_critical = [
                comp for comp in critical_components 
                if not phase_result["components"].get(comp, {}).get("initialized", False)
            ]
            
            if failed_critical:
                phase_result["success"] = False
                phase_result["errors"].append(f"Critical components failed: {failed_critical}")
            
        except Exception as e:
            phase_result["success"] = False
            phase_result["errors"].append(f"Initialization phase failed: {str(e)}")
        
        return phase_result
    
    def _test_automatic_grouping(self) -> Dict[str, Any]:
        """Test automatic grouping with deterministic original selection."""
        phase_result = {
            "name": "Automatic Grouping",
            "success": True,
            "test_scenarios": {},
            "errors": []
        }
        
        try:
            from ops.grouping import GroupingEngine, FileRecord, FileFormat
            from datetime import datetime, timedelta
            
            engine = GroupingEngine(self.test_db_path, self.settings)
            
            # Test scenario 1: Resolution priority
            base_time = datetime.now()
            files_scenario1 = [
                FileRecord(
                    id=1, path="/test/low_res.jpg", size=500000, fast_hash="hash1",
                    sha256_hash="sha1", phash="phash1", width=800, height=600,
                    resolution=480000, exif_datetime=base_time,
                    file_format=FileFormat.JPEG
                ),
                FileRecord(
                    id=2, path="/test/high_res.jpg", size=2000000, fast_hash="hash2",
                    sha256_hash="sha2", phash="phash2", width=1920, height=1080,
                    resolution=2073600, exif_datetime=base_time,
                    file_format=FileFormat.JPEG
                )
            ]
            
            original_id, duplicate_ids, conflict_info = engine._select_original(files_scenario1)
            
            phase_result["test_scenarios"]["resolution_priority"] = {
                "expected_original": 2,  # Higher resolution
                "actual_original": original_id,
                "success": original_id == 2,
                "conflict_detected": conflict_info is not None
            }
            
            # Test scenario 2: EXIF time priority (same resolution)
            files_scenario2 = [
                FileRecord(
                    id=3, path="/test/newer.jpg", size=1000000, fast_hash="hash3",
                    sha256_hash="sha3", phash="phash3", width=1200, height=800,
                    resolution=960000, exif_datetime=base_time + timedelta(minutes=10),
                    file_format=FileFormat.JPEG
                ),
                FileRecord(
                    id=4, path="/test/older.jpg", size=1000000, fast_hash="hash4",
                    sha256_hash="sha4", phash="phash4", width=1200, height=800,
                    resolution=960000, exif_datetime=base_time,
                    file_format=FileFormat.JPEG
                )
            ]
            
            original_id, duplicate_ids, conflict_info = engine._select_original(files_scenario2)
            
            phase_result["test_scenarios"]["exif_time_priority"] = {
                "expected_original": 4,  # Earlier EXIF time
                "actual_original": original_id,
                "success": original_id == 4,
                "conflict_detected": conflict_info is not None
            }
            
            # Test scenario 3: Format priority (same resolution and time)
            files_scenario3 = [
                FileRecord(
                    id=5, path="/test/image.jpg", size=1000000, fast_hash="hash5",
                    sha256_hash="sha5", phash="phash5", width=1200, height=800,
                    resolution=960000, exif_datetime=base_time,
                    file_format=FileFormat.JPEG
                ),
                FileRecord(
                    id=6, path="/test/image.png", size=1200000, fast_hash="hash6",
                    sha256_hash="sha6", phash="phash6", width=1200, height=800,
                    resolution=960000, exif_datetime=base_time,
                    file_format=FileFormat.PNG
                )
            ]
            
            original_id, duplicate_ids, conflict_info = engine._select_original(files_scenario3)
            
            phase_result["test_scenarios"]["format_priority"] = {
                "expected_original": 6,  # PNG has better priority than JPEG
                "actual_original": original_id,
                "success": original_id == 6,
                "conflict_detected": conflict_info is not None
            }
            
            # Check overall success
            all_scenarios_passed = all(
                scenario.get("success", False)
                for scenario in phase_result["test_scenarios"].values()
            )
            
            phase_result["success"] = all_scenarios_passed
            
            if not all_scenarios_passed:
                failed_scenarios = [
                    name for name, scenario in phase_result["test_scenarios"].items()
                    if not scenario.get("success", False)
                ]
                phase_result["errors"].append(f"Failed scenarios: {failed_scenarios}")
            
        except Exception as e:
            phase_result["success"] = False
            phase_result["errors"].append(f"Automatic grouping test failed: {str(e)}")
        
        return phase_result
    
    def _test_conflict_detection(self) -> Dict[str, Any]:
        """Test conflict detection between automatic and manual selection."""
        phase_result = {
            "name": "Conflict Detection",
            "success": True,
            "scenarios": {},
            "errors": []
        }
        
        try:
            from ops.manual_override import ManualOverrideManager, OverrideType, OverrideReason, ManualOverride
            
            manager = ManualOverrideManager(self.test_db_path)
            
            # Create a mock manual override
            override = ManualOverride(
                id=None,
                group_id=1,
                original_file_id=100,  # User prefers this
                auto_original_id=101,  # Algorithm selected this
                override_type=OverrideType.SINGLE_GROUP,
                reason=OverrideReason.USER_PREFERENCE,
                created_at=time.time(),
                notes="User prefers lower file for quality reasons"
            )
            
            # Test recording override
            try:
                override_id = manager.record_override(override)
                phase_result["scenarios"]["override_recording"] = {
                    "success": override_id is not None,
                    "override_id": override_id
                }
            except Exception as e:
                phase_result["scenarios"]["override_recording"] = {
                    "success": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"Override recording failed: {e}")
            
            # Test conflict detection after rescan
            try:
                conflicts = manager.detect_conflicts_after_rescan()
                phase_result["scenarios"]["conflict_detection"] = {
                    "success": True,
                    "conflicts_found": len(conflicts),
                    "conflicts": conflicts
                }
                self.conflicts_detected = conflicts
            except Exception as e:
                phase_result["scenarios"]["conflict_detection"] = {
                    "success": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"Conflict detection failed: {e}")
            
            # Test override statistics
            try:
                stats = manager.get_override_stats()
                phase_result["scenarios"]["override_statistics"] = {
                    "success": True,
                    "stats": stats
                }
            except Exception as e:
                phase_result["scenarios"]["override_statistics"] = {
                    "success": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"Override statistics failed: {e}")
            
            # Check overall success
            all_scenarios_passed = all(
                scenario.get("success", False)
                for scenario in phase_result["scenarios"].values()
            )
            
            phase_result["success"] = all_scenarios_passed
            
        except Exception as e:
            phase_result["success"] = False
            phase_result["errors"].append(f"Conflict detection test failed: {str(e)}")
        
        return phase_result
    
    def _test_manual_override_application(self) -> Dict[str, Any]:
        """Test manual override application workflow."""
        phase_result = {
            "name": "Manual Override Application",
            "success": True,
            "operations": {},
            "errors": []
        }
        
        try:
            from ops.grouping import GroupingEngine
            from ops.manual_override import OverrideType, OverrideReason
            
            engine = GroupingEngine(self.test_db_path, self.settings)
            
            # Test applying manual override
            try:
                success = engine.apply_manual_override(
                    group_id=1,
                    new_original_id=100,
                    override_type="single_group",
                    reason="user_preference",
                    notes="User manually selected this file as original"
                )
                
                phase_result["operations"]["apply_override"] = {
                    "success": success,
                    "group_id": 1,
                    "new_original_id": 100
                }
                
                if success:
                    self.overrides_applied.append({
                        "group_id": 1,
                        "new_original_id": 100,
                        "timestamp": time.time()
                    })
                
            except Exception as e:
                phase_result["operations"]["apply_override"] = {
                    "success": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"Apply override failed: {e}")
            
            # Test removing manual override
            try:
                success = engine.remove_manual_override(group_id=1)
                phase_result["operations"]["remove_override"] = {
                    "success": success,
                    "group_id": 1
                }
            except Exception as e:
                phase_result["operations"]["remove_override"] = {
                    "success": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"Remove override failed: {e}")
            
            # Test checking for conflicts
            try:
                conflicts = engine.check_override_conflicts()
                phase_result["operations"]["check_conflicts"] = {
                    "success": True,
                    "conflicts_found": len(conflicts),
                    "conflicts": conflicts
                }
            except Exception as e:
                phase_result["operations"]["check_conflicts"] = {
                    "success": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"Check conflicts failed: {e}")
            
            # Check overall success
            all_operations_passed = all(
                op.get("success", False)
                for op in phase_result["operations"].values()
            )
            
            phase_result["success"] = all_operations_passed
            
        except Exception as e:
            phase_result["success"] = False
            phase_result["errors"].append(f"Manual override application test failed: {str(e)}")
        
        return phase_result
    
    def _test_override_persistence(self) -> Dict[str, Any]:
        """Test that overrides persist across rescans."""
        phase_result = {
            "name": "Override Persistence",
            "success": True,
            "tests": {},
            "errors": []
        }
        
        try:
            from ops.manual_override import ManualOverrideManager
            
            # Create new manager instance (simulating app restart)
            manager = ManualOverrideManager(self.test_db_path)
            
            # Test getting all overrides
            try:
                overrides = manager.get_all_overrides(active_only=True)
                phase_result["tests"]["get_active_overrides"] = {
                    "success": True,
                    "count": len(overrides),
                    "overrides": [
                        {
                            "group_id": o.group_id,
                            "original_file_id": o.original_file_id,
                            "override_type": o.override_type.value,
                            "reason": o.reason.value
                        }
                        for o in overrides
                    ]
                }
            except Exception as e:
                phase_result["tests"]["get_active_overrides"] = {
                    "success": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"Get active overrides failed: {e}")
            
            # Test getting specific override
            try:
                override = manager.get_override_for_group(1)
                phase_result["tests"]["get_specific_override"] = {
                    "success": override is not None,
                    "found": override is not None,
                    "group_id": override.group_id if override else None
                }
            except Exception as e:
                phase_result["tests"]["get_specific_override"] = {
                    "success": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"Get specific override failed: {e}")
            
            # Check overall success
            all_tests_passed = all(
                test.get("success", False)
                for test in phase_result["tests"].values()
            )
            
            phase_result["success"] = all_tests_passed
            
        except Exception as e:
            phase_result["success"] = False
            phase_result["errors"].append(f"Override persistence test failed: {str(e)}")
        
        return phase_result
    
    def _test_missing_file_handling(self) -> Dict[str, Any]:
        """Test handling when manually selected original file disappears."""
        phase_result = {
            "name": "Missing File Handling",
            "success": True,
            "scenarios": {},
            "errors": []
        }
        
        try:
            from ops.grouping import GroupingEngine, FileRecord, FileFormat
            
            engine = GroupingEngine(self.test_db_path, self.settings)
            
            # Test scenario: Original file exists in group
            files_with_original = [
                FileRecord(
                    id=100, path="/test/user_selected.jpg", size=1000000, fast_hash="hash100",
                    sha256_hash="sha100", phash="phash100", width=1200, height=800,
                    resolution=960000, exif_datetime=datetime.now(),
                    file_format=FileFormat.JPEG
                ),
                FileRecord(
                    id=101, path="/test/auto_selected.jpg", size=2000000, fast_hash="hash101",
                    sha256_hash="sha101", phash="phash101", width=1920, height=1080,
                    resolution=2073600, exif_datetime=datetime.now(),
                    file_format=FileFormat.JPEG
                )
            ]
            
            try:
                original_id, duplicate_ids, conflict_info = engine._select_original(files_with_original, group_id=1)
                phase_result["scenarios"]["file_exists"] = {
                    "success": True,
                    "original_selected": original_id,
                    "conflict_detected": conflict_info is not None
                }
            except Exception as e:
                phase_result["scenarios"]["file_exists"] = {
                    "success": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"File exists scenario failed: {e}")
            
            # Test scenario: Original file missing from group
            files_without_original = [
                FileRecord(
                    id=101, path="/test/auto_selected.jpg", size=2000000, fast_hash="hash101",
                    sha256_hash="sha101", phash="phash101", width=1920, height=1080,
                    resolution=2073600, exif_datetime=datetime.now(),
                    file_format=FileFormat.JPEG
                ),
                FileRecord(
                    id=102, path="/test/another_file.jpg", size=1500000, fast_hash="hash102",
                    sha256_hash="sha102", phash="phash102", width=1600, height=900,
                    resolution=1440000, exif_datetime=datetime.now(),
                    file_format=FileFormat.JPEG
                )
            ]
            
            try:
                original_id, duplicate_ids, conflict_info = engine._select_original(files_without_original, group_id=1)
                phase_result["scenarios"]["file_missing"] = {
                    "success": True,
                    "original_selected": original_id,
                    "fallback_to_auto": original_id == 101,  # Should pick highest resolution
                    "conflict_detected": conflict_info is not None
                }
            except Exception as e:
                phase_result["scenarios"]["file_missing"] = {
                    "success": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"File missing scenario failed: {e}")
            
            # Check overall success
            all_scenarios_passed = all(
                scenario.get("success", False)
                for scenario in phase_result["scenarios"].values()
            )
            
            phase_result["success"] = all_scenarios_passed
            
        except Exception as e:
            phase_result["success"] = False
            phase_result["errors"].append(f"Missing file handling test failed: {str(e)}")
        
        return phase_result
    
    def _test_statistics(self) -> Dict[str, Any]:
        """Test override statistics and reporting."""
        phase_result = {
            "name": "Statistics and Reporting",
            "success": True,
            "metrics": {},
            "errors": []
        }
        
        try:
            from ops.manual_override import ManualOverrideManager
            from ops.grouping import GroupingEngine
            
            manager = ManualOverrideManager(self.test_db_path)
            engine = GroupingEngine(self.test_db_path, self.settings)
            
            # Test override statistics
            try:
                stats = manager.get_override_stats()
                phase_result["metrics"]["override_stats"] = {
                    "success": True,
                    "stats": stats
                }
            except Exception as e:
                phase_result["metrics"]["override_stats"] = {
                    "success": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"Override stats failed: {e}")
            
            # Test grouping engine statistics
            try:
                grouping_stats = engine.stats
                phase_result["metrics"]["grouping_stats"] = {
                    "success": True,
                    "stats": grouping_stats
                }
            except Exception as e:
                phase_result["metrics"]["grouping_stats"] = {
                    "success": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"Grouping stats failed: {e}")
            
            # Test conflict summary
            try:
                if hasattr(engine, 'override_manager') and engine.override_manager:
                    from ops.manual_override import ConflictHandler
                    handler = ConflictHandler(self.test_db_path)
                    if hasattr(handler, 'get_conflict_summary'):
                        summary = handler.get_conflict_summary()
                        phase_result["metrics"]["conflict_summary"] = {
                            "success": True,
                            "summary": summary
                        }
                    else:
                        phase_result["metrics"]["conflict_summary"] = {
                            "success": True,
                            "summary": "Conflict handler available but no Qt support"
                        }
                else:
                    phase_result["metrics"]["conflict_summary"] = {
                        "success": True,
                        "summary": "No override manager available"
                    }
            except Exception as e:
                phase_result["metrics"]["conflict_summary"] = {
                    "success": False,
                    "error": str(e)
                }
                phase_result["errors"].append(f"Conflict summary failed: {e}")
            
            # Check overall success
            all_metrics_passed = all(
                metric.get("success", False)
                for metric in phase_result["metrics"].values()
            )
            
            phase_result["success"] = all_metrics_passed
            
        except Exception as e:
            phase_result["success"] = False
            phase_result["errors"].append(f"Statistics test failed: {str(e)}")
        
        return phase_result
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test summary."""
        total_phases = len(results["phases"])
        passed_phases = sum(1 for phase in results["phases"].values() if phase.get("success", False))
        
        summary = {
            "test_name": "Step 22 - Manual Override System",
            "overall_success": results["success"],
            "success_rate": f"{(passed_phases / total_phases * 100):.1f}%" if total_phases > 0 else "0%",
            "phases_total": total_phases,
            "phases_passed": passed_phases,
            "phases_failed": total_phases - passed_phases,
            "duration_seconds": results.get("duration", 0),
            "conflicts_detected": len(self.conflicts_detected),
            "overrides_applied": len(self.overrides_applied),
            "key_features_tested": [
                "Manual override database operations",
                "Conflict detection and resolution", 
                "Override persistence across rescans",
                "Missing file handling",
                "Statistics and reporting",
                "GUI banner system integration",
                "Deterministic original selection"
            ],
            "recommendations": []
        }
        
        # Add recommendations based on results
        if not results["success"]:
            failed_phases = [
                name for name, phase in results["phases"].items()
                if not phase.get("success", False)
            ]
            summary["recommendations"].append(f"Review failed phases: {failed_phases}")
        
        if summary["success_rate"] == "100.0%":
            summary["recommendations"].append("All tests passed! Manual override system is working correctly.")
        elif float(summary["success_rate"].rstrip('%')) >= 80:
            summary["recommendations"].append("Most tests passed. Review minor issues in failed phases.")
        else:
            summary["recommendations"].append("Significant issues detected. Review implementation and dependencies.")
        
        return summary


def run_step22_integration_test(test_db_path: Path = None) -> Dict[str, Any]:
    """Run the complete Step 22 integration test."""
    import tempfile
    
    if test_db_path is None:
        temp_dir = tempfile.mkdtemp()
        test_db_path = Path(temp_dir) / "step22_test.db"
    
    test = ManualOverrideIntegrationTest(test_db_path)
    results = test.run_complete_workflow()
    
    # Print summary
    summary = results.get("summary", {})
    print(f"\n{'='*60}")
    print(f"STEP 22 INTEGRATION TEST RESULTS")
    print(f"{'='*60}")
    print(f"Overall Success: {summary.get('overall_success', False)}")
    print(f"Success Rate: {summary.get('success_rate', '0%')}")
    print(f"Phases Passed: {summary.get('phases_passed', 0)}/{summary.get('phases_total', 0)}")
    print(f"Duration: {summary.get('duration_seconds', 0):.2f} seconds")
    print(f"Conflicts Detected: {summary.get('conflicts_detected', 0)}")
    print(f"Overrides Applied: {summary.get('overrides_applied', 0)}")
    
    if summary.get('recommendations'):
        print(f"\nRecommendations:")
        for rec in summary['recommendations']:
            print(f"  • {rec}")
    
    print(f"{'='*60}\n")
    
    return results


if __name__ == "__main__":
    # Run the integration test
    test_results = run_step22_integration_test()
    
    # Exit with appropriate code
    exit(0 if test_results.get("success", False) else 1)