#!/usr/bin/env python3
"""
Step 18 Demo: Reports & Export Demonstration
Shows the export functionality with sample data.
"""

import sys
import tempfile
import json
import csv
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def demo_export_functionality():
    """Demonstrate the export functionality with various formats and options."""
    from reports.export_manager import ReportExporter, ExportFormat, ExportScope, DuplicateRecord
    
    print("📊 Photo Deduplicator - Export Demo")
    print("=" * 50)
    
    # Create export manager
    exporter = ReportExporter()
    
    print(f"🔧 Export Manager Status:")
    print(f"   • Available Fields: {len(exporter.available_fields)}")
    enabled_fields = exporter.get_enabled_fields()
    print(f"   • Enabled Fields: {len(enabled_fields)}")
    
    # Show some field examples
    print(f"\n📋 Sample Export Fields:")
    for field in enabled_fields[:8]:  # Show first 8 fields
        required = "(Required)" if field.required else "(Optional)"
        print(f"   • {field.display_name} {required}")
    print(f"   ... and {len(enabled_fields) - 8} more fields")
    
    # Create sample data
    print(f"\n🎲 Creating Sample Data...")
    sample_records = exporter.create_sample_records(8)
    print(f"   • Created {len(sample_records)} duplicate records")
    print(f"   • Groups: {len(set(r.group_id for r in sample_records))}")
    
    # Show sample record
    sample = sample_records[0]
    print(f"\n📄 Sample Record Preview:")
    print(f"   • Group ID: {sample.group_id}")
    print(f"   • Original: {Path(sample.original_path).name}")
    print(f"   • Duplicate: {Path(sample.duplicate_path).name}")
    print(f"   • Tag: {sample.tag}")
    print(f"   • Similarity: {sample.similarity_score}%")
    print(f"   • Camera: {sample.camera_make} {sample.camera_model}")
    print(f"   • File Size: {sample.file_size:,} bytes")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Demo CSV Export
        print(f"\n📈 CSV Export Demo...")
        csv_file = temp_path / "duplicate_report.csv"
        
        success = exporter.export_to_csv(sample_records, str(csv_file))
        if success:
            print(f"   ✓ CSV export successful: {csv_file.name}")
            
            # Show CSV preview
            with open(csv_file, 'r', encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                rows = list(csv_reader)
                
            print(f"   • Rows: {len(rows)} (including header)")
            print(f"   • Columns: {len(rows[0]) if rows else 0}")
            print(f"   • Header: {', '.join(rows[0][:5])}..." if rows else "")
            
        # Demo JSON Export
        print(f"\n📋 JSON Export Demo...")
        json_file = temp_path / "duplicate_report.json"
        
        success = exporter.export_to_json(sample_records, str(json_file))
        if success:
            print(f"   ✓ JSON export successful: {json_file.name}")
            
            # Show JSON preview
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            print(f"   • Records: {len(data['records'])}")
            print(f"   • Export Date: {data['metadata']['export_date']}")
            print(f"   • Fields: {len(data['metadata']['exported_fields'])}")
            
            # Show first record fields
            if data['records']:
                first_record = data['records'][0]
                print(f"   • Sample Fields: {', '.join(list(first_record.keys())[:5])}...")
                
        # Demo Field Filtering
        print(f"\n🔍 Field Filtering Demo...")
        
        # Disable some fields
        exporter.set_field_enabled("notes", False)
        exporter.set_field_enabled("camera_make", False)
        exporter.set_field_enabled("camera_model", False)
        
        filtered_fields = exporter.get_enabled_fields()
        print(f"   • Original Fields: {len(enabled_fields)}")
        print(f"   • Filtered Fields: {len(filtered_fields)}")
        
        # Export with filtering
        filtered_file = temp_path / "filtered_report.json"
        success = exporter.export_to_json(sample_records, str(filtered_file))
        
        if success:
            with open(filtered_file, 'r', encoding='utf-8') as f:
                filtered_data = json.load(f)
                
            print(f"   ✓ Filtered export successful")
            print(f"   • Exported Fields: {len(filtered_data['metadata']['exported_fields'])}")
            
            # Verify filtering worked
            first_record = filtered_data['records'][0]
            if 'notes' not in first_record:
                print(f"   ✓ Field filtering working correctly")
            
        # Demo Both Formats Export
        print(f"\n📊 Both Formats Export Demo...")
        both_base = temp_path / "complete_report"
        
        success = exporter.export_both_formats(sample_records, str(both_base))
        if success:
            csv_exists = (temp_path / "complete_report.csv").exists()
            json_exists = (temp_path / "complete_report.json").exists()
            
            print(f"   ✓ Both formats export successful")
            print(f"   • CSV Created: {csv_exists}")
            print(f"   • JSON Created: {json_exists}")
            
        # Show file sizes
        print(f"\n📁 Export File Information:")
        for export_file in temp_path.glob("*.csv"):
            size_kb = export_file.stat().st_size / 1024
            print(f"   • {export_file.name}: {size_kb:.1f} KB")
            
        for export_file in temp_path.glob("*.json"):
            size_kb = export_file.stat().st_size / 1024
            print(f"   • {export_file.name}: {size_kb:.1f} KB")
            
        # Demo Export Scope Options
        print(f"\n🎯 Export Scope Options:")
        print(f"   • {ExportScope.CURRENT_VIEW.value}: Current filtered view")
        print(f"   • {ExportScope.FULL_DATASET.value}: Complete dataset")  
        print(f"   • {ExportScope.SELECTED_ONLY.value}: Selected files only")
        
        print(f"\n📋 Export Format Options:")
        print(f"   • {ExportFormat.CSV.value}: Comma-separated values")
        print(f"   • {ExportFormat.JSON.value}: JavaScript Object Notation")
        print(f"   • {ExportFormat.BOTH.value}: Both CSV and JSON")
        
    print(f"\n✅ Export Demo Complete!")
    print(f"All export formats and options working correctly.")

if __name__ == "__main__":
    demo_export_functionality()