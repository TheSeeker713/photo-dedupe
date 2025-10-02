# photo-dedupe

A Python utility for finding and removing duplicate photos from large collections. Features both command-line and GUI interfaces with intelligent duplicate detection using multiple hashing algorithms and perceptual analysis.

## 🚧 Development Status

**Currently in active development** - Core components implemented:
- ✅ File system scanning with change detection
- ✅ EXIF metadata extraction and orientation handling  
- ✅ Thumbnail generation with caching
- ✅ SQLite database with performance optimization
- ✅ Settings management and cache system

**Not yet implemented:**
- Hash computation and perceptual analysis
- Duplicate detection algorithms
- User interface (CLI/GUI)
- Batch operations and safety features

Expected beta release: Q1 2025

## Features (Planned)

- **Smart Scanning**: Recursive directory scanning with configurable include/exclude patterns
- **Multiple Detection Methods**: File hash, perceptual hash (pHash, dHash, wHash), and optional ORB features
- **Performance Tuned**: Three presets (Ultra-Lite, Balanced, Accurate) for different hardware capabilities
- **Safe Operations**: Send to Recycle Bin or quarantine folder with undo support
- **Privacy Focused**: Hashed filenames in cache, no cloud dependencies
- **Format Support**: JPEG, PNG, HEIC/HEIF, RAW formats, and more

## Getting Started

### Prerequisites
- Python 3.10 or higher
- Windows (primary target), macOS/Linux (community support)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd photo-dedupe
```

2. Create and activate virtual environment:
```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Windows Command Prompt  
.\.venv\Scripts\activate.bat

# macOS/Linux
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Development Testing

Run component tests to verify installation:
```bash
# Test settings system
python -m src.app.demo_settings

# Test database initialization  
python -m src.store.demo_db

# Test file scanning
python -m src.ops.demo_scan

# Test thumbnail generation
python -m src.core.demo_thumbs_simple
```

## Project Structure

```
src/
├── app/          # Application settings and configuration
├── core/         # Core algorithms (EXIF, thumbnails, hashing)
├── ops/          # Operations (scanning, duplicate detection)  
├── store/        # Data storage (database, cache management)
├── ui/           # User interface components (future)
└── tests/        # Test utilities and validation
```

## Contributing

This project is in early development. Core architecture is stabilizing but APIs may change. 

## License

[License TBD]
