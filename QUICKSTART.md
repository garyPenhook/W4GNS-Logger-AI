# Quick Start Guide - W4GNS Logger AI

## Setup (First Time)

```bash
# 1. Navigate to project directory
cd /home/w4gns/Documents/software/W4GNS-Logger-AI

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Verify installation
pytest -v
```

## Running the Application

### GUI Mode
```bash
# Start the graphical interface
w4gns-gui
# or
python -m w4gns_logger_ai.gui
```

### CLI Mode

#### Log a QSO
```bash
w4gns log --call K1ABC --band 20m --mode SSB --freq 14.250
```

#### List Recent QSOs
```bash
w4gns list --limit 20
```

#### Search QSOs
```bash
w4gns search --call K1ABC
w4gns search --band 20m --mode FT8
```

#### Import ADIF File
```bash
w4gns import-adif mylog.adi
```

#### Export ADIF File
```bash
w4gns export --output mylog.adi --limit 1000
```

#### Awards Summary
```bash
w4gns awards summary
w4gns awards suggest
w4gns awards eval --goals "Work 100 countries on 20m"
```

## Common Tasks

### Import Contest Log
```bash
w4gns import-adif contest.adi --parallel --batch-size 1000
```

### Check Awards Progress
```bash
w4gns awards summary --band 20m --mode SSB
```

### Generate AI Summary (requires OPENAI_API_KEY)
```bash
export OPENAI_API_KEY="your-key-here"
w4gns summarize --limit 50
```

## Troubleshooting

### Missing tkinter
```bash
sudo apt-get install python3-tk
```

### Database Issues
```bash
# Check database location
w4gns init

# Set custom database path
export W4GNS_DB_PATH="/path/to/custom.db"
```

### Run Tests
```bash
pytest -v
```

### Check Code Quality
```bash
ruff check .
```

## File Locations

- **Database**: `~/.local/share/W4GNS Logger AI/qsolog.sqlite3`
- **Config**: `~/.config/W4GNS Logger AI/awards.json`
- **Virtual Env**: `.venv/`

## Quick Tips

1. **Parallel Processing**: Automatically enabled for large files (>500 records)
2. **Batch Size**: Default 1000, adjust with `--batch-size` for imports
3. **Awards Config**: Edit `~/.config/W4GNS Logger AI/awards.json` to customize thresholds
4. **AI Features**: Optional, requires `OPENAI_API_KEY` environment variable

## Performance Tips

- Use `--parallel` flag for large ADIF imports
- Increase `--batch-size` for very large files (try 5000)
- Filter searches by band/mode for faster queries
- Use `--limit` to restrict result size

## Help

```bash
# General help
w4gns --help

# Command-specific help
w4gns log --help
w4gns awards --help
```

## Next Steps

1. ✅ Review IMPROVEMENTS.md for technical details
2. ✅ Check REVIEW_SUMMARY.md for full analysis
3. ✅ Run `pytest -v` to verify everything works
4. 📻 Start logging QSOs!

73!
