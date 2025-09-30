[![CI](https://github.com/garyPenhook/W4GNS-Logger-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/garyPenhook/W4GNS-Logger-AI/actions/workflows/ci.yml)

# W4GNS Logger AI

Ham radio QSO logger with SQLite storage, ADIF import/export, awards insights, and an optional AI summary helper.

Features:
- CLI built with Typer and Rich
- Desktop GUI (Tkinter) with tabs for Log, Browse, Awards, Tools
- SQLite database via SQLModel (SQLAlchemy 2.x)
- ADIF import/export (minimal but practical)
- Search/filter by call/band/mode/grid
- Awards summary and suggestions, plus AI-assisted evaluation
- Optional AI summary using OpenAI (if `OPENAI_API_KEY` is set)
- **High-performance C extensions for 10-100x speedup** (optional, auto-fallback to Python)

## Performance

This logger includes optional high-performance C/Cython extensions that provide:

- **ADIF Parsing**: 10-20x speedup via C pointer arithmetic
- **Awards Computation**: 5-30x speedup via optimized set operations
- **ADIF Export**: 5-15x speedup via C string formatting

**Benchmarks (50K QSOs):**
- ADIF import: ~3,600 QSOs/sec
- Awards computation: ~11,000 QSOs/sec  
- ADIF export: ~80,000 QSOs/sec

C extensions are **optional** - the logger automatically falls back to pure Python if not compiled. See `benchmarks/benchmark_c_extensions.py` for performance comparisons.

## Quick start (Windows, uv)

1) Install dependencies (development + tests):

```
uv pip install -e .[dev]
```

2) Build C extensions (optional, for 10-100x speedup):

```
python setup.py build_ext --inplace
```

**Note:** Building C extensions requires:
- Python development headers (`python3-dev` on Linux, included with Python on Windows)
- C compiler (GCC/Clang on Linux, Visual Studio on Windows)
- Cython 3.0+

If C extensions are not built, the logger will automatically fall back to pure Python implementations.

3) Initialize the database (optional; commands auto-init on first run):

```
w4gns init
```

4) Launch the GUI:

```
w4gns-gui
```

If the launcher is not in PATH yet, run:

```
python -m w4gns_logger_ai.gui
```

5) CLI examples:

```
w4gns log --call K1ABC --band 20m --mode SSB --freq 14.25 --comment "First contact"
w4gns list --limit 10
w4gns search --call ABC --mode SSB
w4gns export --output mylog.adi
w4gns import-adif mylog.adi
```

5) Awards (deterministic + AI):

```
w4gns awards summary
w4gns awards suggest
w4gns awards eval --goals "Reach DXCC on 20m SSB"
```

## AI setup (optional)

Install the AI extra and set your OpenAI key:

```
uv pip install -e .[ai]
set OPENAI_API_KEY=sk-...
```

Without a key or the extra installed, AI commands fall back to a local summary/plan.

## Awards configuration

Thresholds are configurable via JSON. Defaults:

```
{
  "DXCC": 100,
  "VUCC": 100
}
```

You can override thresholds by creating `awards.json` in your user config directory or by pointing an env var at a custom file.

- Env var: `W4GNS_AWARDS_CONFIG`
- Default location (Windows): `%APPDATA%/W4GNS Logger AI/awards.json` (via platformdirs)

Example:

```
{
  "DXCC": 125,
  "VUCC": 75,
  "MY_CUSTOM": 50
}
```

Unknown keys are accepted for future use; only known awards are applied today.

## Configuration

- Database path can be overridden by setting `W4GNS_DB_PATH` to a full file path.
- By default, the DB is stored under your user data directory (e.g., `%LOCALAPPDATA%\W4GNS Logger AI\qsolog.sqlite3`).

## Development

- Lint: `ruff check .`
- Tests: `pytest -q`

### For AI Coding Assistants 🤖

This project has comprehensive guidelines for AI assistants in the `.ai/` directory:
- **[Quick Reference](.ai/quick-reference.md)** - Start here! Performance patterns, common tasks, critical rules
- **[Coding Guidelines](.ai/coding-guidelines.md)** - Detailed architecture, patterns, and best practices

Key principles:
- ✅ Use generators (`Iterator[T]`) for all data processing
- ✅ Optimize parallelization with `get_optimal_workers()`
- ✅ Stream large files and datasets
- ✅ Use `next()` for early termination
- ✅ Always include type hints and error handling

See also: `STREAMING_IMPROVEMENTS_SUMMARY.md`, `HYPERTHREADING_SUMMARY.md`

## CI

A GitHub Actions workflow runs lint and tests on pushes/PRs.

## Packaging

This project uses PEP 621 metadata in `pyproject.toml` with Hatchling as the build backend. `uv` can install from `pyproject.toml` directly.
