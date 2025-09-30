# AI Assistant Quick Reference - W4GNS Logger

> **For AI Coding Assistants**: This file provides quick context and patterns for the W4GNS Logger project. Read this first before making code changes.

## 🎯 Project Mission
Amateur radio contact logging with AI-powered insights, optimized for performance and memory efficiency.

## 🏗️ Architecture Summary

### Core Principles
1. **Memory Efficiency First**: Always use generators (`Iterator[T]`) for data processing
2. **Streaming Over Lists**: Stream large datasets, provide list wrappers for compatibility
3. **Parallel by Default**: Use hyperthreading-aware parallel processing for large datasets
4. **Graceful Degradation**: Always include fallbacks and error handling
5. **Type Safety**: Comprehensive type hints with TypedDict for structured data

### Tech Stack Quick View
```
Python 3.12+ → SQLModel/SQLAlchemy → SQLite
├── CLI: Typer + Rich
├── GUI: Tkinter (optional)
├── AI: OpenAI (optional, with fallbacks)
├── Parallel: ThreadPoolExecutor + ProcessPoolExecutor
└── Testing: pytest + ruff
```

## 🚀 Performance Patterns

### 1. Generator Pattern (ALWAYS USE)
```python
# ✅ Primary: Streaming generator
def list_qsos_stream(limit: int = 100) -> Iterator[QSO]:
    with session_scope() as session:
        stmt = select(QSO).limit(limit)
        for qso in session.scalars(stmt):
            yield qso

# ✅ Wrapper: Backward compatible
def list_qsos(limit: int = 100) -> List[QSO]:
    return list(list_qsos_stream(limit))
```

**Benefits**: 50-99% memory reduction, enables processing datasets larger than RAM

### 2. Early Termination Pattern (USE FOR "FIND FIRST")
```python
def get_first_match(criteria) -> Optional[QSO]:
    with session_scope() as session:
        stmt = select(QSO).where(...).limit(1)
        return next(session.scalars(stmt), None)  # Stops after first!
```

### 3. Parallel Processing Pattern (USE FOR LARGE DATASETS)
```python
from w4gns_logger_ai.parallel_utils import get_optimal_workers

def process_parallel(items: List[Item], workload: str = "cpu") -> List[Result]:
    # workload: "io" (files/network), "cpu" (computation), "mixed" (APIs)
    workers = get_optimal_workers(workload)
    
    # Choose executor: ThreadPoolExecutor for I/O, ProcessPoolExecutor for CPU
    Executor = ThreadPoolExecutor if workload == "io" else ProcessPoolExecutor
    
    # CI detection for fallback
    if any(e in os.environ for e in ['CI', 'GITHUB_ACTIONS']):
        Executor = ThreadPoolExecutor  # Always threads in CI
    
    try:
        with Executor(max_workers=workers) as executor:
            return list(executor.map(process_item, items))
    except Exception:
        return [process_item(i) for i in items]  # Sequential fallback
```

### 4. Database Pattern (ALWAYS USE session_scope)
```python
from w4gns_logger_ai.storage import session_scope

def add_qso(qso: QSO) -> QSO:
    with session_scope() as session:  # Auto commit/rollback/close
        session.add(qso)
        session.flush()
        session.refresh(qso)
        return qso
```

## 📊 When to Use What

| Scenario | Pattern | Example |
|----------|---------|---------|
| Query multiple records | `Iterator[T]` generator | `list_qsos_stream()` |
| Find first match | `next()` with default | `get_first_qso_by_call()` |
| Large file parsing | Parallel + streaming | `load_adif_parallel()` |
| CPU-heavy computation | ProcessPoolExecutor | `compute_summary_parallel()` |
| API calls | ThreadPoolExecutor | `summarize_qsos_parallel()` |
| File I/O | ThreadPoolExecutor | `dump_adif_stream()` |
| Batch DB operations | Bulk with batching | `bulk_add_qsos()` |

## 🔧 Common Tasks

### Adding a New Field to QSO
1. Update `models.py`: Add field to `QSO` class
2. Update `adif.py`: Add to `FIELD_MAP_IN` and `FIELD_MAP_OUT`
3. Update `dump_adif_stream()`: Add field export logic
4. Add test in `test_adif.py`: Test roundtrip

### Adding a New CLI Command
```python
@app.command()
def new_cmd(
    param: str = typer.Argument(..., help="..."),
    stream: bool = typer.Option(False, help="Use streaming"),
) -> None:
    """Command description."""
    try:
        _ensure_db()
        if stream:
            for item in process_stream(param):
                console.print(item)
        else:
            results = process_batch(param)
            console.print(f"Done: {len(results)}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
```

### Adding Parallel Processing
1. Create sequential version first
2. Add parallel version with `get_optimal_workers()`
3. Add auto-switching wrapper with threshold (e.g., >1000 items)
4. Include CI detection and fallbacks

## ⚠️ Critical Rules

### ✅ ALWAYS
- Use `Iterator[T]` for data processing
- Use `next()` for early termination
- Use `get_optimal_workers()` for parallelization
- Use `session_scope()` for database access
- Add type hints to all public functions
- Include error handling with fallbacks
- Test with temporary database (`tmp_path`)
- Reset `storage._engine = None` when changing DB path in tests
- Batch database operations (1000+ items)
- Include CI-aware fallbacks

### ❌ NEVER
- Load entire dataset into memory (use generators!)
- Create database sessions manually (use `session_scope()`)
- Use fixed worker counts (use `get_optimal_workers()`)
- Ignore CI environment (check `os.environ`)
- Skip type hints on public functions
- Individual DB inserts in loops (use `bulk_add_qsos()`)
- Hard-code paths (use environment variables)
- Commit failing linting (`ruff check`)

## 📈 Performance Targets

| Operation | Small (<1K) | Medium (1K-10K) | Large (>10K) |
|-----------|-------------|-----------------|--------------|
| **Strategy** | Sequential | Parallel optional | Parallel required |
| **Memory** | List OK | Prefer generators | Must use generators |
| **Workers** | N/A | 2-4 | Optimal (4-8) |
| **Batch Size** | N/A | 1000 | 5000-10000 |

## 🧪 Testing Checklist

- [ ] Unit tests for core functionality
- [ ] Edge cases (None, empty, large datasets)
- [ ] Temporary database with `tmp_path` fixture
- [ ] Reset `storage._engine = None` in teardown
- [ ] CI compatibility (use conservative settings)
- [ ] Error handling and fallbacks
- [ ] Type hints verified
- [ ] Linting passes (`ruff check`)

## 🔍 Quick Debug Commands

```bash
# Check tests
pytest -v

# Check linting  
ruff check .

# Auto-fix linting
ruff check --fix

# Check CPU info
python -m w4gns_logger_ai.parallel_utils

# Run optimization example
python examples/hyperthreading_optimization.py
```

## 📚 Key Files to Review

Before making changes, review:
- `.ai/coding-guidelines.md` - **Comprehensive guidelines (read this!)**
- `STREAMING_IMPROVEMENTS_SUMMARY.md` - Streaming patterns
- `HYPERTHREADING_SUMMARY.md` - Parallel processing
- `w4gns_logger_ai/parallel_utils.py` - Optimization utilities
- `tests/conftest.py` - Test fixtures and patterns

## 🎓 Learning Path for New AI Assistants

1. **Start Here**: Read this file
2. **Deep Dive**: Read `.ai/coding-guidelines.md`
3. **See Examples**: Study `examples/hyperthreading_optimization.py`
4. **Review Tests**: Check `tests/test_storage.py` for patterns
5. **Check Utils**: Understand `w4gns_logger_ai/parallel_utils.py`

## 💡 Pro Tips

1. **Generators Everywhere**: Default to `Iterator[T]`, wrap with `list()` if needed
2. **Parallel Smart**: Use `get_optimal_workers()` - it knows CPU architecture
3. **CI Aware**: Always check `os.environ` for CI and use conservative settings
4. **Type Everything**: Use `TypedDict` for dictionaries, `Optional` for nullables
5. **Test Isolation**: Reset `_engine` when changing DB path in tests
6. **Stream Files**: Use generators for files >1000 records
7. **Batch DB Ops**: Never insert one-by-one, always batch (1000+ items)
8. **Early Exit**: Use `next()` when you only need first match

## 🚨 Common Pitfalls to Avoid

1. **Memory Bloat**: Loading full dataset when generator would work
2. **Worker Waste**: Using too many/few workers (use `get_optimal_workers()`)
3. **DB Thrashing**: Creating new session for each operation
4. **CI Failures**: Not testing with CI-aware fallbacks
5. **Type Confusion**: Forgetting `Optional` or using `Any`
6. **No Streaming**: Processing large files without generators
7. **Batch Skipping**: Individual inserts instead of `bulk_add_qsos()`

## 📝 Code Review Checklist

Before submitting:
- [ ] Uses generators for data processing (`Iterator[T]`)
- [ ] Uses `next()` for early termination where applicable
- [ ] Uses `get_optimal_workers()` for parallelization
- [ ] Uses `session_scope()` for all DB access
- [ ] Has comprehensive type hints
- [ ] Includes error handling with fallbacks
- [ ] Has CI-aware conditional logic
- [ ] Includes tests (unit + integration)
- [ ] Passes `pytest -v`
- [ ] Passes `ruff check`
- [ ] Documentation updated (if public API changed)

## 🔗 Related Resources

- **Main Guidelines**: `.ai/coding-guidelines.md`
- **Streaming Guide**: `STREAMING_IMPROVEMENTS_SUMMARY.md`
- **Parallel Guide**: `HYPERTHREADING_SUMMARY.md`
- **Generator Analysis**: `GENERATOR_FUNCTIONS_ANALYSIS.md`
- **Next() Patterns**: `NEXT_FUNCTION_OPPORTUNITIES.md`

---

**Last Updated**: 2025-09-30  
**Version**: 1.0  
**Status**: Active - Use as primary AI assistant reference

---

*Quick tip: When in doubt, look for existing patterns in the codebase. The project follows consistent conventions - find a similar function and follow its pattern.*
