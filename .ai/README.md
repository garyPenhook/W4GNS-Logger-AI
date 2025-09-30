# AI Assistant Documentation

This directory contains comprehensive guidelines and quick references for AI coding assistants working on the W4GNS Logger project.

## 📚 Documentation Files

### 1. **quick-reference.md** ⚡ START HERE
**Quick context for AI assistants** - Read this first!
- Performance patterns at a glance
- Common tasks and solutions
- Critical do's and don'ts
- Quick debug commands
- Code review checklist

**Use when**: You need to quickly understand the project before making changes

### 2. **coding-guidelines.md** 📖 COMPREHENSIVE GUIDE
**Detailed guidelines and patterns** - Deep dive reference
- Architecture and design patterns
- Performance optimization strategies
- Code quality standards
- Testing requirements
- Complete examples and anti-patterns

**Use when**: You need detailed guidance on implementing new features

## 🎯 How to Use (For AI Assistants)

### New to the Project?
1. Read `quick-reference.md` (5 min)
2. Skim `coding-guidelines.md` (10 min)
3. Review relevant examples in codebase
4. Start coding with patterns in mind

### Making Changes?
1. Check `quick-reference.md` for the pattern
2. Reference `coding-guidelines.md` for details
3. Follow the established conventions
4. Run tests and linting before committing

### Adding New Features?
1. Study similar existing features
2. Apply performance patterns from guidelines
3. Use generators for data processing
4. Optimize parallelization with `get_optimal_workers()`
5. Include comprehensive tests

## 🚀 Key Performance Patterns

### 1. Always Use Generators
```python
# ✅ Primary: Streaming
def list_items_stream() -> Iterator[Item]:
    for item in query():
        yield item

# ✅ Wrapper: Compatibility
def list_items() -> List[Item]:
    return list(list_items_stream())
```

### 2. Optimize Parallelization
```python
from w4gns_logger_ai.parallel_utils import get_optimal_workers

workers = get_optimal_workers("io")    # I/O bound
workers = get_optimal_workers("cpu")   # CPU bound
workers = get_optimal_workers("mixed") # Mixed workload
```

### 3. Use Early Termination
```python
def find_first(criteria) -> Optional[Item]:
    return next(iter(items_matching(criteria)), None)
```

### 4. Always Use session_scope()
```python
from w4gns_logger_ai.storage import session_scope

with session_scope() as session:
    # Auto commit/rollback/close
    session.add(item)
```

## ⚠️ Critical Rules

### ✅ ALWAYS
- Use `Iterator[T]` for data processing
- Use `get_optimal_workers()` for parallelization
- Use `session_scope()` for database
- Add type hints to public functions
- Include error handling and fallbacks
- Test with CI-aware configurations

### ❌ NEVER
- Load entire datasets into memory
- Use fixed worker counts
- Create sessions manually
- Skip type hints
- Ignore CI environment
- Commit failing linting

## 📊 Performance Targets

| Dataset Size | Strategy | Workers | Memory |
|--------------|----------|---------|--------|
| < 1K items | Sequential | N/A | List OK |
| 1K - 10K | Parallel optional | 2-4 | Prefer generators |
| > 10K | Parallel required | Optimal | Must use generators |

**Results**:
- **Memory**: 50-99% reduction with streaming
- **Speed**: 2-10x improvement with parallelization
- **Scalability**: Process datasets larger than RAM

## 🧪 Testing Checklist

- [ ] Uses `tmp_path` for database
- [ ] Resets `storage._engine = None` in teardown
- [ ] Includes CI-aware fallbacks
- [ ] Tests edge cases (None, empty, large)
- [ ] Passes `pytest -v`
- [ ] Passes `ruff check`

## 🔗 Related Documentation

In this directory:
- `quick-reference.md` - Quick patterns and rules
- `coding-guidelines.md` - Comprehensive guidelines

In project root:
- `STREAMING_IMPROVEMENTS_SUMMARY.md` - Streaming implementation
- `HYPERTHREADING_SUMMARY.md` - Parallel processing
- `GENERATOR_FUNCTIONS_ANALYSIS.md` - Generator patterns
- `NEXT_FUNCTION_OPPORTUNITIES.md` - Early termination patterns

## 🎓 Learning Path

1. **Beginner**: Read `quick-reference.md`
2. **Intermediate**: Study `coding-guidelines.md`
3. **Advanced**: Review performance analysis docs
4. **Expert**: Study `w4gns_logger_ai/parallel_utils.py`

## 📝 Contributing Guidelines for AI

When making changes:

1. **Understand Context**
   - Read quick-reference.md first
   - Check coding-guidelines.md for patterns
   - Review similar existing code

2. **Follow Patterns**
   - Use established conventions
   - Apply performance optimizations
   - Include comprehensive types

3. **Ensure Quality**
   - Write tests for new features
   - Run `pytest -v` and `ruff check`
   - Document public APIs

4. **Optimize Performance**
   - Default to generators (`Iterator[T]`)
   - Use `get_optimal_workers()` for parallel
   - Stream large files and datasets
   - Batch database operations

## 🚨 Common Pitfalls

1. **Memory Issues**: Loading full dataset → Use generators
2. **Wrong Workers**: Fixed count → Use `get_optimal_workers()`
3. **DB Problems**: Manual sessions → Use `session_scope()`
4. **CI Failures**: No fallbacks → Add CI detection
5. **Type Issues**: Missing hints → Add comprehensive types

## 💡 Pro Tips

1. When in doubt, look for existing patterns
2. Default to streaming, wrap with `list()` if needed
3. Always optimize for the CI environment
4. Use `next()` for early exits
5. Batch database operations (1000+ items)

## 📞 Quick Commands

```bash
# Testing
pytest -v

# Linting
ruff check .
ruff check --fix

# CPU info
python -m w4gns_logger_ai.parallel_utils

# Examples
python examples/hyperthreading_optimization.py
```

---

**Last Updated**: 2025-09-30  
**Purpose**: AI assistant onboarding and reference  
**Status**: Active - Primary documentation for AI coding

---

*These guidelines represent established patterns and optimizations. Follow them to maintain code quality and performance.*
