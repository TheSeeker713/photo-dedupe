# Step 11 Implementation Summary: Grouping Engine & "Original" Selection

## ✅ Acceptance Criteria Achieved

### 1. Two-Tier Grouping System

#### **Tier 1 (Exact Duplicates)**
- **Criteria**: Same size + same fast hash + SHA256 confirmation
- **Implementation**: Groups files by `(size, fast_hash)` tuple, then confirms with SHA256 if enabled
- **Confidence Score**: 1.0 (with SHA256) or 0.95 (fast hash only)
- **Use Case**: Identical files with different names/locations

#### **Tier 2 (Near Duplicates)**  
- **Criteria**: pHash within threshold + dimension sanity check (±10%)
- **Optional**: EXIF DateTimeOriginal match for strict mode
- **Implementation**: Uses BK-tree search index for efficient perceptual hash matching
- **Confidence Score**: Dynamic based on pHash distance (1.0 - distance/threshold)
- **Use Case**: Same image with different compression, quality, or minor edits

### 2. Deterministic "Original" Selection Rules

**Priority Order (implemented as sort key):**
1. **Highest Resolution** → `dims_w × dims_h` (descending)
2. **Earliest EXIF Time** → `exif_dt` timestamp (ascending, None = latest)  
3. **Largest File Size** → `size` in bytes (descending)
4. **Preferred Format Order** → RAW > TIFF > PNG > JPEG > WEBP > OTHER
5. **Path Tie-breaker** → Alphabetical sort for consistency

### 3. Group Composition Validation
- **Each group**: Exactly one "original" + at least one "duplicate"
- **Database Storage**: Uses existing `groups` and `group_members` tables
- **Role Assignment**: 'original' and 'duplicate' roles with similarity scores

### 4. Score Summaries
- **Group-level**: Confidence scores, tier classification, file counts
- **Overall Summary**: Total groups, space savings estimate, confidence distribution
- **Metadata**: Processing statistics, algorithm parameters

## 🏗️ Implementation Architecture

### Core Classes

#### **`FileFormat` Enum**
```python
class FileFormat(Enum):
    RAW = ("raw", 1)      # Highest quality priority
    TIFF = ("tiff", 2)    # Lossless 
    PNG = ("png", 3)      # Lossless compressed
    JPEG = ("jpeg", 4)    # Lossy compressed  
    WEBP = ("webp", 5)    # Modern lossy
    OTHER = ("other", 6)  # Unknown formats
```

#### **`FileRecord` Dataclass**
- Comprehensive file metadata with computed properties
- Resolution calculation, format classification, EXIF parsing
- Used for grouping decisions and original selection

#### **`DuplicateGroup` Dataclass**
- Group metadata: ID, tier, original, duplicates, confidence
- Summary generation and validation methods
- Database storage format compatibility

#### **`GroupingEngine` Class**
- **Two-tier processing**: Exact → Near duplicate detection
- **Search integration**: Uses BK-tree index for performance
- **Database integration**: Stores results in existing schema
- **Configuration**: Performance presets, tolerance settings

### Key Algorithms

#### **Exact Duplicate Detection**
```python
def find_exact_duplicates(files):
    # Group by (size, fast_hash)
    groups = group_by(files, key=lambda f: (f.size, f.fast_hash))
    
    # SHA256 confirmation if enabled
    if sha256_enabled:
        groups = confirm_with_sha256(groups)
    
    # Select original for each group
    return [create_group(select_original(group)) for group in groups]
```

#### **Near Duplicate Detection**
```python
def find_near_duplicates(files, exact_files):
    candidates = exclude(files, exact_files)
    
    for file in candidates:
        # BK-tree search within threshold
        similar = search_index.find_near_duplicates(file.id, threshold)
        
        # Dimension compatibility check
        valid = filter(similar, dimension_compatible)
        
        # EXIF datetime match in strict mode
        if strict_mode:
            valid = filter(valid, exif_datetime_match)
        
        if valid:
            yield create_group(select_original([file] + valid))
```

#### **Original Selection Logic**
```python
def _original_sort_key(file):
    return (
        -file.resolution,           # Highest resolution first
        file.exif_datetime or max,  # Earliest time first  
        -file.size,                 # Largest size first
        file.format.priority,       # Better format first
        file.path                   # Consistent tie-breaker
    )
```

## 📊 Performance Characteristics

### Processing Speed
- **Exact Duplicates**: O(n) grouping + O(k) SHA256 confirmation
- **Near Duplicates**: O(n log n) with BK-tree search optimization
- **Original Selection**: O(k log k) per group where k = group size

### Memory Usage
- **File Records**: ~1KB per file for complete metadata
- **Search Index**: Uses existing BK-tree infrastructure
- **Group Storage**: Minimal overhead for group associations

### Scalability
- **Linear scaling** with file count for exact duplicates
- **Sub-linear scaling** for near duplicates due to BK-tree efficiency
- **Configurable thresholds** for performance vs accuracy trade-offs

## 🧪 Testing Coverage

### Unit Tests
- **File Format Classification**: All supported formats and priorities
- **Original Selection Rules**: Each priority level with edge cases
- **Group Composition**: Validation of exactly one original per group

### Integration Tests
- **Database Integration**: Storage and retrieval from existing schema
- **Search Index Integration**: BK-tree compatibility and performance  
- **Settings Integration**: Performance preset application

### Acceptance Tests
- **Two-tier Grouping**: Both exact and near duplicate detection
- **Deterministic Selection**: Comprehensive rule validation with test scenarios
- **Score Summaries**: Complete metadata and confidence calculations

## 🔧 Configuration Options

### Performance Presets
```python
PHASH_THRESHOLDS = {
    "Ultra-Lite": 6,   # Stricter matching
    "Balanced": 8,     # Default threshold  
    "Accurate": 12,    # More permissive
}
```

### Grouping Settings
- **`enable_sha256_confirmation`**: Tier 1 SHA256 verification (default: True)
- **`strict_mode_exif_match`**: Require EXIF datetime match for near duplicates
- **`dimension_tolerance`**: Percentage tolerance for dimension compatibility (±10%)

### Format Priority Customization
- **Extensible enum**: Easy to add new formats or modify priorities
- **Extension mapping**: Automatic format detection from file extensions
- **RAW format support**: Comprehensive list of camera RAW formats

## 🎯 Usage Examples

### Basic Grouping Workflow
```python
# Initialize engine
grouping_engine = GroupingEngine(db_path, settings)

# Process all files  
groups, stats = grouping_engine.process_all_files()

# Store results
grouping_engine.store_groups(groups)

# Get summary
summary = grouping_engine.get_group_summary(groups)
```

### Custom Configuration
```python
# Enable strict EXIF matching
settings.update("Grouping", "strict_mode_exif_match", True)

# Adjust dimension tolerance
settings.update("Grouping", "dimension_tolerance", 0.05)  # ±5%

# Disable SHA256 confirmation for speed
settings.update("Grouping", "enable_sha256_confirmation", False)
```

### Results Analysis
```python
for group in groups:
    print(f"Group {group.id} ({group.tier.value}):")
    print(f"  Original: {group.original_id}")
    print(f"  Duplicates: {len(group.duplicate_ids)}")
    print(f"  Confidence: {group.confidence_score:.3f}")
```

## 🎯 Next Steps Ready

With Step 11 complete, the photo deduplication tool now has:

1. **✅ Complete Detection Pipeline**: File scanning → Features → Search → Grouping
2. **✅ Two-Tier Duplicate Detection**: Exact and near duplicate identification
3. **✅ Deterministic Original Selection**: Consistent, rule-based prioritization
4. **✅ Database Integration**: Proper storage in existing schema
5. **✅ Performance Optimization**: Configurable presets and efficient algorithms

**Ready for Step 12+**: User interface for group management, bulk operations, and duplicate resolution workflows.

---

*Step 11 successfully implements a production-ready two-tier grouping engine with deterministic original selection, meeting all acceptance criteria for comprehensive duplicate photo management.*