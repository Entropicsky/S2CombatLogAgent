# Utility Scripts

This directory contains utility scripts for enhancing and working with SMITE 2 Combat Log databases.

## Timeline Enhancement Scripts

- `migrate_timeline_schema.py` - Migrates existing databases to include the enhanced timeline event schema
- `reprocess_timeline.py` - Reprocesses timeline events using the enhanced generator
- `enhance_timeline.py` - Combined script that performs both migration and reprocessing

Usage:
```bash
python scripts/enhance_timeline.py path/to/database.db [--match-id MATCH_ID] [--force]
```

## Excel Export Scripts

- `export_to_excel.py` - Exports all tables from a SQLite database to an Excel file
- For detailed documentation on the export process and data model, see [EXPORT_README.md](EXPORT_README.md)

Usage:
```bash
python scripts/export_to_excel.py path/to/database.db [-o output.xlsx]
```

The Excel export is also automatically run after processing log files with the main `load.py` script. To disable this behavior, use the `--no-excel` flag:

```bash
python load.py path/to/log_file.log [--no-excel]
```

## Integration Testing

- `integration_test.py` - Performs a clean test of the parser by removing the database, parsing a log file, and validating the results

Usage:
```bash
python scripts/integration_test.py path/to/log_file.log [--keep-db] [--skip-excel]
```

## Dependencies

Some scripts require additional dependencies:
- Excel export requires `pandas`, `openpyxl`, and `xlsxwriter`

Install all dependencies with:
```bash
pip install -r requirements.txt
``` 