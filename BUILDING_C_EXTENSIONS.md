# Building C Extensions

This guide explains how to build the optional high-performance C/Cython extensions for W4GNS Logger AI.

## Why Build C Extensions?

The C extensions provide **10-100x speedup** for performance-critical operations:

- **ADIF Parsing**: 10-20x faster via C pointer arithmetic
- **Awards Computation**: 5-30x faster via optimized set operations  
- **ADIF Export**: 5-15x faster via C string formatting

C extensions are **completely optional** - the logger automatically falls back to pure Python implementations if they're not available.

## Prerequisites

### Linux (Ubuntu/Debian)

```bash
sudo apt-get install python3-dev build-essential
pip install Cython setuptools wheel
```

### macOS

```bash
xcode-select --install  # Install command line tools
pip install Cython setuptools wheel
```

### Windows

1. Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. Select "Desktop development with C++" workload
3. Install Cython:

```powershell
pip install Cython setuptools wheel
```

## Building

From the project root directory:

```bash
python setup.py build_ext --inplace
```

This compiles the Cython extensions in-place, creating `.so` (Linux/macOS) or `.pyd` (Windows) files in `w4gns_logger_ai/c_extensions/`.

## Verification

Run the benchmark suite to verify C extensions are working:

```bash
python benchmarks/benchmark_c_extensions.py
```

You should see:
```
✅ C extensions are ENABLED
```

If C extensions are not available, you'll see:
```
⚠️ C extensions are NOT available (using pure Python)
```

## Performance Comparison

**With C Extensions (50K QSOs):**
- ADIF import: ~3,600 QSOs/sec
- Awards computation: ~11,000 QSOs/sec
- ADIF export: ~80,000 QSOs/sec

**Pure Python (50K QSOs):**
- ADIF import: ~300-500 QSOs/sec (10-20x slower)
- Awards computation: ~1,000-2,000 QSOs/sec (5-10x slower)
- ADIF export: ~5,000-10,000 QSOs/sec (8-15x slower)

## Troubleshooting

### "Python.h: No such file or directory"

Install Python development headers:
- **Linux**: `sudo apt-get install python3-dev`
- **macOS**: Already included with Python
- **Windows**: Reinstall Python with "Include pip and IDLE" option

### "error: Microsoft Visual C++ 14.0 or greater is required"

Install Visual Studio Build Tools with C++ workload (Windows only).

### Segmentation fault

This usually indicates a version mismatch. Try:
```bash
pip install --upgrade --force-reinstall Cython
python setup.py clean --all
python setup.py build_ext --inplace
```

### C extensions not loading

Check import status:
```python
from w4gns_logger_ai import adif
print(f"C extensions: {adif.USE_C_EXTENSIONS}")
```

## Distribution

When distributing the package, consider:

1. **Pre-built wheels**: Build platform-specific wheels with C extensions
2. **Source distribution**: Users can build on their own system
3. **Pure Python fallback**: Always works without compilation

Build wheels for distribution:
```bash
pip install build
python -m build --wheel
```

## CI/CD

For GitHub Actions, see `.github/workflows/ci.yml` for build matrix examples with C extension compilation.
