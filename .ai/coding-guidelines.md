# W4GNS Logger AI - Coding Guidelines for AI Assistants

This document provides comprehensive guidelines for AI coding assistants working on the W4GNS Logger project. It captures architectural decisions, optimization patterns, and best practices established during development.

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & Design Patterns](#architecture--design-patterns)
3. [Performance Optimizations](#performance-optimizations)
4. [Code Quality Standards](#code-quality-standards)
5. [Testing Requirements](#testing-requirements)
6. [Common Patterns & Examples](#common-patterns--examples)

---

## Project Overview

### Tech Stack
- **Language**: Python 3.12+
- **ORM**: SQLModel (SQLAlchemy 2.x)
- **Database**: SQLite with connection pooling
- **CLI**: Typer with Rich for formatting
- **GUI**: Tkinter (optional)
- **AI**: OpenAI API (optional, with local fallbacks)
- **Testing**: pytest
- **Linting**: ruff
- **Type Checking**: Pyright/Pylance

### Project Structure
```
w4gns_logger_ai/
├── __init__.py
├── models.py          # SQLModel data models
├── storage.py         # Database persistence layer
├── adif.py           # ADIF file format handling
├── awards.py         # Awards calculation and filtering
├── ai_helper.py      # OpenAI integration (optional)
├── cli.py            # Command-line interface
├── gui.py            # Tkinter GUI (optional)
├── parallel_utils.py # Hyperthreading optimization utilities
└── c_extensions/     # Optional high-performance C/Cython extensions
    ├── __init__.py
    ├── c_adif_parser.pyx   # 10-20x faster ADIF parsing
    ├── c_awards.pyx        # 5-30x faster awards computation
    └── c_adif_export.pyx   # 5-15x faster ADIF export

tests/
├── conftest.py
├── test_*.py         # Test modules

benchmarks/
└── benchmark_c_extensions.py  # Performance benchmarking
```

### C/Cython Extensions (Optional)

The project includes optional high-performance C extensions that provide **10-100x speedup**:

- **c_adif_parser.pyx**: ADIF parsing with C pointer arithmetic (10-20x faster)
- **c_awards.pyx**: Awards computation with optimized set operations (5-30x faster)  
- **c_adif_export.pyx**: ADIF export with C string formatting (5-15x faster)

**Key Principles:**
- ✅ C extensions are **completely optional** - automatic fallback to pure Python
- ✅ Maintain 100% API compatibility between C and Python versions
- ✅ Use `USE_C_EXTENSIONS` flag for runtime detection
- ✅ Always provide pure Python implementation as fallback
- ✅ Build with `python setup.py build_ext --inplace`

**When to Use C Extensions:**
- Large dataset processing (50K+ QSOs)
- Performance-critical batch operations
- ADIF import/export of large files
- Awards computation on extensive logs

**When NOT to Use:**
- Small datasets (<1K QSOs) - overhead may negate benefits
- Development/testing without C compiler
- Distribution to users without build tools

## Performance Optimizations

### Performance Hierarchy

The project uses a multi-layer optimization strategy:

1. **Python-level optimizations** (always available):
   - Streaming generators for memory efficiency
   - `next()` for early termination
   - Parallel processing with optimal worker counts
   - Connection pooling and batch operations

2. **C/Cython extensions** (optional, 10-100x speedup):
   - ADIF parsing: C pointer arithmetic
   - Awards computation: Optimized set operations
   - ADIF export: C string formatting

3. **Database optimizations**:
   - Connection pooling with QueuePool
   - Batch operations
   - Proper indexing and query optimization

**Decision Flow:**
```
Is performance critical? 
├─ YES → Try C extensions first (if available)
│         └─ Fallback to optimized Python
└─ NO  → Use standard Python patterns
```

### 1. **Memory-Efficient Streaming with Generators**

#### ✅ ALWAYS prefer generator functions for data processing

**Pattern**: Return `Iterator[T]` for streaming, provide list-based wrapper for compatibility

```python
from typing import Iterator, List

# Primary streaming function
def list_qsos_stream(limit: int = 100) -> Iterator[QSO]:
    """Stream QSOs one at a time for memory efficiency."""
    with session_scope() as session:
        stmt = select(QSO).order_by(QSO.start_at.desc()).limit(limit)
        for qso in session.scalars(stmt):
            yield qso

# Backward-compatible wrapper
def list_qsos(limit: int = 100) -> List[QSO]:
    """Return QSOs as list (uses streaming internally)."""
    return list(list_qsos_stream(limit))
```

**Benefits**:
- 50-99% memory reduction on large datasets
- Enables processing datasets larger than RAM
- Lazy evaluation with early termination support
- Backward compatible with existing code

**When to use**:
- ✅ Database queries returning multiple records
- ✅ File parsing (ADIF, CSV, etc.)
- ✅ Data export/serialization
- ✅ Data transformations and filtering

### 2. **Early Termination with next()**

#### ✅ Use `next()` for "find first" operations

**Pattern**: Avoid loading full dataset when you only need first match

```python
def get_first_qso_by_call(call: str) -> Optional[QSO]:
    """Find first QSO by callsign using next() for efficiency."""
    with session_scope() as session:
        stmt = select(QSO).where(QSO.call == call.upper()).limit(1)
        # next() with default=None - Pythonic early termination
        return next(session.scalars(stmt), None)
```

**Benefits**:
- Stops iteration immediately after finding first match
- No need to load remaining records
- Clean, Pythonic code
- Type-safe with Optional return

**When to use**:
- ✅ "Find first matching" operations
- ✅ Existence checks (`if next(iter, None) is not None`)
- ✅ Default value scenarios
- ✅ Single-item extraction from iterators

### 3. **Parallel Processing with Hyperthreading Awareness**

#### ✅ Use workload-specific worker counts

**Pattern**: Different worker counts for I/O vs CPU bound operations

```python
from w4gns_logger_ai.parallel_utils import get_optimal_workers

# I/O bound operations (file parsing, network)
def load_adif_parallel(text: str) -> List[QSO]:
    workers = get_optimal_workers("io")  # Uses 2× physical cores
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Process chunks in parallel
        ...

# CPU bound operations (computation, calculations)
def compute_summary_parallel(qsos: List[QSO]) -> AwardsSummary:
    workers = get_optimal_workers("cpu")  # Uses physical cores only
    with ProcessPoolExecutor(max_workers=workers) as executor:
        # Process chunks in parallel
        ...

# Mixed operations (API calls with processing)
def summarize_qsos_parallel(batches: List[List[QSO]]) -> List[str]:
    workers = get_optimal_workers("mixed")  # Uses 1.5× physical cores
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Process batches concurrently
        ...
```

**Key Rules**:
- **ThreadPoolExecutor**: I/O bound (files, network, APIs) - benefits from hyperthreading
- **ProcessPoolExecutor**: CPU bound (math, algorithms) - use physical cores only
- **Always**: Include CI detection and conservative fallbacks
- **Always**: Add error handling with fallback to sequential processing

### 4. **Database Connection Management**

#### ✅ Use session_scope() context manager

**Pattern**: Thread-safe database access with automatic cleanup

```python
@contextmanager
def session_scope():
    """Context manager for database sessions."""
    session = Session(get_engine())
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# Usage
def add_qso(qso: QSO) -> QSO:
    with session_scope() as session:
        session.add(qso)
        session.flush()
        session.refresh(qso)
        return qso
```

**Key Rules**:
- ✅ Always use `session_scope()` - never create sessions directly
- ✅ Engine is a singleton with thread-safe double-check locking
- ✅ Connection pooling configured (pool_size=10, max_overflow=20)
- ✅ `check_same_thread=False` enables multi-threading
- ✅ Reset `_engine = None` when changing DB path in tests

### 5. **ADIF File Processing**

#### ✅ Stream ADIF processing for memory efficiency

**Pattern**: Parse and generate ADIF line-by-line

```python
# Streaming ADIF export
def dump_adif_stream(qsos: Iterable[QSO]) -> Iterator[str]:
    """Stream ADIF lines for memory-efficient export."""
    # Yield header
    yield "<ADIF_VER:3>3.1\n"
    yield "<PROGRAMID:13>W4GNS Logger\n"
    yield "<EOH>\n\n"
    
    # Yield records one at a time
    for qso in qsos:
        fields = []
        if qso.call:
            fields.append(f"<CALL:{len(qso.call)}>{qso.call}")
        # ... more fields
        yield "".join(fields) + "<EOR>\n"

# Backward-compatible wrapper
def dump_adif(qsos: Iterable[QSO]) -> str:
    """Return ADIF as string (uses streaming internally)."""
    return "".join(dump_adif_stream(qsos))
```

**Parallel ADIF Import**:
```python
def load_adif_parallel(text: str, max_workers: int = None) -> List[QSO]:
    """Parse ADIF using parallel processing."""
    chunks = text.split("<EOR>")
    
    # Use sequential for small files
    if len(chunks) < 100:
        return load_adif(text)
    
    # Optimize worker count for I/O workload
    if max_workers is None:
        max_workers = get_optimal_workers("io")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_chunk, c): c for c in chunks}
        results = []
        for future in as_completed(futures):
            if result := future.result():
                results.append(result)
    
    return results
```

### 6. **Awards Computation**

#### ✅ Automatic parallel processing for large datasets

**Pattern**: Threshold-based parallelization with automatic activation

```python
def compute_summary(qsos: Iterable[QSO]) -> AwardsSummary:
    """Compute awards summary with automatic parallelization."""
    qsos_list = list(qsos)
    
    # Auto-activate parallel for large datasets
    if len(qsos_list) > 10000:
        return compute_summary_parallel(qsos_list)
    
    # Sequential for small datasets
    total = len(qsos_list)
    countries = unique_values(qsos_list, "country")
    # ... compute stats
    
    return {
        "total_qsos": total,
        "unique_countries": len(countries),
        # ... more stats
    }

def compute_summary_parallel(qsos: Iterable[QSO], chunk_size: int = 5000):
    """Parallel awards computation for large datasets."""
    qsos_list = list(qsos)
    chunks = [qsos_list[i:i+chunk_size] for i in range(0, len(qsos_list), chunk_size)]
    
    workers = get_optimal_workers("cpu")
    
    # Use threads in CI, processes in production
    is_ci = any(env in os.environ for env in ['CI', 'GITHUB_ACTIONS'])
    Executor = ThreadPoolExecutor if is_ci else ProcessPoolExecutor
    
    with Executor(max_workers=workers) as executor:
        summaries = list(executor.map(_compute_summary_chunk, chunks))
        return _merge_summaries(summaries)
```

### 7. **Type Hints & Documentation**

#### ✅ Comprehensive type annotations

**Pattern**: Use modern type hints with clear documentation

```python
from typing import Dict, Iterable, Iterator, List, Optional, TypedDict

class AwardsSummary(TypedDict):
    """Type definition for awards summary dictionary."""
    total_qsos: int
    unique_countries: int
    unique_grids: int
    grids_by_band: Dict[str, int]

def search_qsos_stream(
    call: Optional[str] = None,
    band: Optional[str] = None,
    mode: Optional[str] = None,
    grid: Optional[str] = None,
    limit: int = 100,
) -> Iterator[QSO]:
    """Stream QSOs matching search criteria.
    
    Args:
        call: Optional callsign substring filter
        band: Optional band filter (exact match)
        mode: Optional mode filter (exact match)
        grid: Optional grid square filter
        limit: Maximum number of results
    
    Returns:
        Iterator yielding matching QSO objects
        
    Examples:
        >>> for qso in search_qsos_stream(band="20m", limit=10):
        ...     print(qso.call)
    """
    # Implementation...
```

**Key Rules**:
- ✅ All public functions must have type hints
- ✅ Use TypedDict for structured dictionaries
- ✅ Optional[] for nullable parameters
- ✅ Iterator[T] for generators, List[T] for lists
- ✅ Docstrings with Args, Returns, Examples

---

## Performance Optimizations

### 1. **Memory Efficiency Checklist**

When working with large datasets:

- ✅ **Use generators**: `Iterator[T]` instead of `List[T]`
- ✅ **Stream file I/O**: Read/write line-by-line
- ✅ **Use next()**: For early termination
- ✅ **Batch operations**: Process in chunks (1000-10000 items)
- ✅ **Connection pooling**: Reuse database connections
- ✅ **Lazy evaluation**: Only compute what's needed

### 2. **Parallelization Decision Tree**

```
Is the dataset large? (>1000 items)
  ├─ No → Use sequential processing
  └─ Yes → Is it I/O bound or CPU bound?
      ├─ I/O bound (files, network, API)
      │   └─ Use ThreadPoolExecutor with get_optimal_workers("io")
      ├─ CPU bound (computation, algorithms)
      │   └─ Use ProcessPoolExecutor with get_optimal_workers("cpu")
      └─ Mixed (API + processing)
          └─ Use ThreadPoolExecutor with get_optimal_workers("mixed")

Always include:
  ✅ CI detection (use conservative settings)
  ✅ Fallback to sequential on errors
  ✅ Timeout handling for async operations
```

### 3. **Database Optimization Patterns**

```python
# ✅ GOOD: Streaming query with limit
def list_qsos_stream(limit: int = 100) -> Iterator[QSO]:
    with session_scope() as session:
        stmt = select(QSO).limit(limit).order_by(QSO.start_at.desc())
        for qso in session.scalars(stmt):
            yield qso

# ✅ GOOD: Bulk operations in batches
def bulk_add_qsos(qsos: Iterable[QSO], batch_size: int = 1000) -> int:
    qsos_list = list(qsos)
    total = 0
    
    with session_scope() as session:
        for i in range(0, len(qsos_list), batch_size):
            batch = qsos_list[i:i+batch_size]
            session.bulk_save_objects(batch)
            session.flush()
            total += len(batch)
    
    return total

# ❌ BAD: Loading all records into memory
def get_all_qsos() -> List[QSO]:
    with session_scope() as session:
        return list(session.scalars(select(QSO)))  # Could be millions!

# ❌ BAD: Individual inserts in loop
def add_many_qsos(qsos: List[QSO]):
    for qso in qsos:
        add_qso(qso)  # New session for each! Very slow!
```

### 4. **CLI Performance Features**

```python
# Streaming export with --stream flag
@app.command()
def export(
    output: Path,
    limit: int = 100,
    stream: bool = typer.Option(False, help="Use streaming export"),
):
    """Export QSOs to ADIF file."""
    if stream:
        # Memory-efficient streaming
        count = 0
        with open(output, "w") as f:
            for line in dump_adif_stream(list_qsos_stream(limit=limit)):
                f.write(line)
                if "<EOR>" in line:
                    count += 1
        console.print(f"Exported {count} QSOs (streaming)")
    else:
        # Traditional list-based
        qsos = list_qsos(limit=limit)
        text = dump_adif(qsos)
        output.write_text(text)
        console.print(f"Exported {len(qsos)} QSOs")
```

---

## Code Quality Standards

### 1. **Linting & Formatting**

```bash
# All code must pass:
ruff check .           # Linting
ruff format .          # Auto-formatting (if needed)
pytest -v              # All tests must pass
```

**Common ruff rules**:
- Line length: 100 characters max
- Import sorting: isort compatible
- No unused imports or variables
- F-strings must have placeholders (or use regular strings)
- Type hints required for public functions

### 2. **Import Organization**

```python
# Standard library
from __future__ import annotations
import os
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

# Third-party
from sqlmodel import Session, SQLModel, create_engine, select
import typer
from rich.console import Console

# Local modules
from .models import QSO
from .parallel_utils import get_optimal_workers
```

### 3. **Error Handling**

```python
# ✅ GOOD: Specific exceptions with context
try:
    with session_scope() as session:
        session.add(qso)
except Exception as e:
    raise RuntimeError(f"Failed to add QSO: {e}") from e

# ✅ GOOD: Graceful degradation
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

def summarize_qsos(qsos: List[QSO]) -> str:
    if HAS_OPENAI and os.getenv("OPENAI_API_KEY"):
        return _openai_summary(qsos)
    return _fallback_summary(qsos)

# ✅ GOOD: CI-aware fallbacks
is_ci = any(env in os.environ for env in ['CI', 'GITHUB_ACTIONS'])
if is_ci:
    # Use simpler, more reliable approach
    return sequential_processing(data)
else:
    # Use advanced parallel processing
    return parallel_processing(data)
```

### 4. **Testing Patterns**

```python
# Test with temporary database
def test_feature(tmp_path):
    import os
    from w4gns_logger_ai import storage
    
    original_db = os.environ.get("W4GNS_DB_PATH")
    os.environ["W4GNS_DB_PATH"] = str(tmp_path / "test.sqlite3")
    
    try:
        # Reset engine to use new DB
        storage._engine = None
        create_db_and_tables()
        
        # Run test
        qso = QSO(call="TEST", start_at=datetime.now())
        result = add_qso(qso)
        assert result.id is not None
    
    finally:
        # Cleanup
        if original_db:
            os.environ["W4GNS_DB_PATH"] = original_db
        else:
            del os.environ["W4GNS_DB_PATH"]
        storage._engine = None

# Test parallel processing with CI safety
def test_parallel_processing():
    is_ci = 'CI' in os.environ
    
    if is_ci:
        # Simplified test for CI
        result = compute_summary(qsos)
    else:
        # Full parallel test
        result = compute_summary_parallel(qsos)
    
    assert result["total_qsos"] == len(qsos)
```

---

## Testing Requirements

### 1. **Test Coverage**

All new features must include:
- ✅ Unit tests for core functionality
- ✅ Integration tests for database operations
- ✅ Edge cases (empty input, None values, large datasets)
- ✅ CI compatibility tests

### 2. **Test Organization**

```python
# tests/test_feature.py
def test_basic_functionality():
    """Test core feature works as expected."""
    # Arrange
    qso = QSO(call="W1ABC", ...)
    
    # Act
    result = process_qso(qso)
    
    # Assert
    assert result is not None
    assert result.call == "W1ABC"

def test_edge_cases():
    """Test boundary conditions."""
    assert process_qso(None) is None
    assert process_empty([]) == []

def test_error_handling():
    """Test error conditions."""
    with pytest.raises(ValueError):
        process_invalid_input("bad")

def test_performance():
    """Test with realistic dataset sizes."""
    large_dataset = [QSO(...) for _ in range(10000)]
    result = process_many(large_dataset)
    assert len(result) == 10000
```

### 3. **Fixtures**

```python
# tests/conftest.py
@pytest.fixture
def sample_qso():
    """Create a sample QSO for testing."""
    return QSO(
        call="K1ABC",
        start_at=datetime(2024, 1, 1, 12, 0, 0),
        band="20m",
        mode="SSB",
    )

@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database for testing."""
    import os
    from w4gns_logger_ai import storage
    
    original = os.environ.get("W4GNS_DB_PATH")
    db_path = tmp_path / "test.sqlite3"
    os.environ["W4GNS_DB_PATH"] = str(db_path)
    storage._engine = None
    
    from w4gns_logger_ai.storage import create_db_and_tables
    create_db_and_tables()
    
    yield db_path
    
    if original:
        os.environ["W4GNS_DB_PATH"] = original
    else:
        del os.environ["W4GNS_DB_PATH"]
    storage._engine = None
```

---

## Common Patterns & Examples

### 1. **Adding a New Data Field**

When adding a new field to QSO model:

```python
# 1. Update models.py
class QSO(SQLModel, table=True):
    # Existing fields...
    new_field: Optional[str] = None

# 2. Update ADIF field mapping in adif.py
FIELD_MAP_IN = {
    # Existing mappings...
    "NEW_TAG": "new_field",
}

FIELD_MAP_OUT = {
    # Existing mappings...
    "new_field": "NEW_TAG",
}

# 3. Update ADIF export in dump_adif_stream()
if qso.new_field:
    fields.append(f"<NEW_TAG:{len(qso.new_field)}>{qso.new_field}")

# 4. Add test in tests/test_adif.py
def test_new_field_roundtrip():
    qso = QSO(call="W1ABC", new_field="test_value")
    adif = dump_adif([qso])
    parsed = load_adif(adif)
    assert parsed[0].new_field == "test_value"
```

### 2. **Adding a New CLI Command**

```python
# In cli.py
@app.command()
def new_command(
    param1: str = typer.Argument(..., help="Description"),
    param2: int = typer.Option(100, help="Optional param"),
    stream: bool = typer.Option(False, help="Use streaming"),
) -> None:
    """Command description for --help."""
    try:
        _ensure_db()
        
        # Use streaming when appropriate
        if stream:
            for item in process_stream(param1, limit=param2):
                console.print(item)
        else:
            results = process_batch(param1, limit=param2)
            console.print(f"Processed {len(results)} items")
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
```

### 3. **Adding Parallel Processing**

```python
# 1. Create sequential version first
def process_items(items: List[Item]) -> List[Result]:
    """Sequential processing for small datasets."""
    return [process_item(item) for item in items]

# 2. Add parallel version with optimization
def process_items_parallel(
    items: List[Item],
    workload_type: str = "cpu",
) -> List[Result]:
    """Parallel processing for large datasets."""
    from w4gns_logger_ai.parallel_utils import (
        get_optimal_workers,
        get_optimal_batch_size,
    )
    
    workers = get_optimal_workers(workload_type)
    batch_size = get_optimal_batch_size(len(items), workers)
    
    # Choose executor based on workload
    Executor = ThreadPoolExecutor if workload_type == "io" else ProcessPoolExecutor
    
    is_ci = 'CI' in os.environ
    if is_ci:
        # Always use threads in CI
        Executor = ThreadPoolExecutor
    
    try:
        with Executor(max_workers=workers) as executor:
            results = list(executor.map(process_item, items))
        return results
    except Exception:
        # Fallback to sequential
        return process_items(items)

# 3. Add smart wrapper with threshold
def process_items_auto(items: List[Item]) -> List[Result]:
    """Automatically choose sequential or parallel."""
    if len(items) > 1000:
        return process_items_parallel(items)
    return process_items(items)
```

### 4. **Adding Streaming Export**

```python
# 1. Create streaming generator
def export_format_stream(items: Iterable[Item]) -> Iterator[str]:
    """Stream export line-by-line."""
    # Header
    yield "# Header\n"
    
    # Items
    for item in items:
        yield format_item(item) + "\n"
    
    # Footer
    yield "# End\n"

# 2. Create backward-compatible wrapper
def export_format(items: Iterable[Item]) -> str:
    """Export as string (uses streaming)."""
    return "".join(export_format_stream(items))

# 3. Add CLI streaming option
@app.command()
def export_new_format(
    output: Path,
    limit: int = 100,
    stream: bool = typer.Option(False),
):
    if stream:
        with open(output, "w") as f:
            for line in export_format_stream(list_items_stream(limit)):
                f.write(line)
    else:
        items = list_items(limit)
        output.write_text(export_format(items))
```

---

## Key Takeaways

### ✅ Always Do
1. **Use generators** for data processing (Iterator[T])
2. **Use next()** for early termination
3. **Optimize worker counts** with parallel_utils
4. **Stream large files** line-by-line
5. **Type hint everything** with clear docs
6. **Handle errors gracefully** with fallbacks
7. **Test with CI awareness** and temporary DBs
8. **Batch database operations** (1000+ items)
9. **Use session_scope()** for DB access
10. **Document performance characteristics**

### ❌ Never Do
1. ❌ Load entire dataset into memory
2. ❌ Create database sessions manually
3. ❌ Use fixed worker counts (use get_optimal_workers)
4. ❌ Ignore CI environment differences
5. ❌ Skip type hints on public functions
6. ❌ Forget error handling and fallbacks
7. ❌ Use individual inserts in loops
8. ❌ Hard-code file paths or database locations
9. ❌ Skip tests for new features
10. ❌ Commit code that fails linting

### 🎯 Performance Targets
- **Memory**: 50-99% reduction with streaming
- **Parallelization**: 2-10x speedup on large datasets
- **Database**: <100ms for single queries, batch for bulk ops
- **ADIF**: Stream files >1000 records
- **Awards**: Parallel for >10,000 QSOs

---

## Quick Reference

### Import Checklist
```python
# For streaming
from typing import Iterator, Iterable, List, Optional

# For parallelization
from w4gns_logger_ai.parallel_utils import get_optimal_workers
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# For database
from w4gns_logger_ai.storage import session_scope
from sqlmodel import select

# For CLI
import typer
from rich.console import Console
```

### Common Commands
```bash
# Development
pytest -v                    # Run tests
ruff check .                # Lint
ruff format .               # Format
python -m w4gns_logger_ai.parallel_utils  # Check CPU

# Usage
w4gns export --stream       # Streaming export
w4gns import-adif --parallel  # Parallel import
```

### Performance Utils
```python
# Optimal workers
workers = get_optimal_workers("io")      # I/O bound
workers = get_optimal_workers("cpu")     # CPU bound
workers = get_optimal_workers("mixed")   # Mixed

# Batch sizing
batch_size = get_optimal_batch_size(total, workers)

# Parallelization check
if should_use_parallel(count, threshold=1000):
    use_parallel_processing()
```

---

## Version History

- **2025-09-30**: Initial guidelines created
  - Streaming generators implementation
  - Hyperthreading optimization utilities
  - Parallel processing patterns
  - Testing and CI best practices

---

## See Also

- `STREAMING_IMPROVEMENTS_SUMMARY.md` - Streaming generator implementation
- `HYPERTHREADING_ANALYSIS.md` - Detailed hyperthreading analysis
- `HYPERTHREADING_SUMMARY.md` - Hyperthreading implementation guide
- `GENERATOR_FUNCTIONS_ANALYSIS.md` - Generator performance analysis
- `NEXT_FUNCTION_OPPORTUNITIES.md` - Early termination patterns
- `IMPROVEMENTS.md` - Historical improvements log
- `REVIEW_SUMMARY.md` - Code review findings

---

*This document should be referenced by AI coding assistants when making changes to the W4GNS Logger codebase. It represents established patterns and optimizations that should be maintained and extended.*
