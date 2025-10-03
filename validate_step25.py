#!/usr/bin/env python3
"""
Step 25 Validation Command - Test dataset & validation routine.

This script creates a test dataset and runs comprehensive validation of the 
photo-dedupe system. It can be run as a standalone command or integrated 
into the main application as a menu item.

Usage:
    python validate_step25.py [--temp-dir DIR] [--keep-files] [--verbose]
"""

import argparse
import logging
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tests.validation_runner import ValidationRunner, print_validation_summary


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
        ]
    )


def main():
    """Main validation command entry point."""
    parser = argparse.ArgumentParser(
        description="Run Step 25 validation tests for photo-dedupe system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python validate_step25.py                    # Run with default settings
    python validate_step25.py --verbose          # Run with detailed logging
    python validate_step25.py --keep-files       # Keep test files after validation
    python validate_step25.py --temp-dir ./test  # Use specific directory
        """
    )
    
    parser.add_argument(
        '--temp-dir', 
        type=Path,
        help='Directory to use for test files (default: system temp)'
    )
    
    parser.add_argument(
        '--keep-files', 
        action='store_true',
        help='Keep test files after validation (default: cleanup)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run quick validation (fewer test files)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    print("Step 25 - Photo-Dedupe Validation Suite")
    print("=" * 50)
    
    try:
        # Create temp directory if needed
        if args.temp_dir:
            temp_dir = args.temp_dir
            temp_dir.mkdir(parents=True, exist_ok=True)
        else:
            temp_dir = Path(tempfile.mkdtemp())
        
        logger.info(f"Using temporary directory: {temp_dir}")
        
        # Run validation
        runner = ValidationRunner(temp_dir)
        
        print("\nRunning comprehensive validation tests...")
        print("This may take a few minutes...")
        print()
        
        summary = runner.run_full_validation()
        
        # Print results
        print_validation_summary(summary)
        
        # Cleanup or preserve files
        if args.keep_files:
            print(f"\n📁 Test files preserved in: {temp_dir}")
        else:
            try:
                import shutil
                shutil.rmtree(temp_dir)
                logger.info("Cleaned up temporary files")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp files: {e}")
        
        # Return appropriate exit code
        if summary.success_rate >= 80:
            print("\n✅ Validation completed successfully!")
            return 0
        elif summary.success_rate >= 60:
            print("\n⚠️  Validation completed with warnings.")
            return 1
        else:
            print("\n❌ Validation failed!")
            return 2
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Validation interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Validation failed with error: {e}", exc_info=args.verbose)
        print(f"\n💥 Validation error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())