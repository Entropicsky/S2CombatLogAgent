#!/usr/bin/env python3
"""
SMITE 2 Combat Log Parser Integration Test Script
This script performs a clean test of the parser by:
1. Removing existing database file (if any)
2. Running the parser on a log file
3. Validating the database content
4. Testing Excel export
"""

import os
import sys
import argparse
import shutil
from pathlib import Path

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from smite_parser.config.config import ParserConfig
from smite_parser.parser import CombatLogParser
from scripts.export_to_excel import export_to_excel

def clean_test(log_file, keep_db=False, skip_excel=False):
    """Perform a clean integration test of the parser.
    
    Args:
        log_file: Path to the log file to process
        keep_db: If True, don't delete existing database file
        skip_excel: If True, skip Excel export test
    
    Returns:
        True if successful, False otherwise
    """
    print(f"=== Running Integration Test on {log_file} ===")
    
    # Check if log file exists
    log_path = Path(log_file)
    if not log_path.exists():
        print(f"Error: Log file {log_file} does not exist")
        return False
    
    # Determine database path
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / f"{log_path.stem}.db"
    
    # Remove existing database file if it exists and keep_db is False
    if db_path.exists() and not keep_db:
        print(f"Removing existing database file: {db_path}")
        os.remove(db_path)
    
    # Configure parser
    print(f"Configuring parser with database path: {db_path}")
    config = ParserConfig(
        db_path=str(db_path),
        batch_size=1000,
        show_progress=True,
        skip_malformed=True,
    )
    
    # Create parser
    parser = CombatLogParser(config)
    
    # Parse the file
    print(f"Parsing log file: {log_path}")
    success = parser.parse_file(str(log_path))
    
    if not success:
        print(f"❌ Failed to parse log file: {log_path}")
        return False
    
    print(f"✅ Successfully parsed log file: {log_path}")
    
    # Validate database content
    print("Validating database content...")
    try:
        # Basic validation - database file exists and has content
        if not db_path.exists():
            print(f"❌ Database file not found: {db_path}")
            return False
        
        if db_path.stat().st_size == 0:
            print(f"❌ Database file is empty: {db_path}")
            return False
        
        # Check tables using SQLite
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get table counts
        tables = ["matches", "players", "combat_events", "reward_events", "item_events", "player_events", "timeline_events", "player_stats"]
        table_counts = {}
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            table_counts[table] = count
            print(f"  {table}: {count} records")
        
        # Check if we have at least one match
        if table_counts["matches"] < 1:
            print("❌ No match records found in database")
            return False
        
        # Check if we have players
        if table_counts["players"] < 1:
            print("❌ No player records found in database")
            return False
        
        # Check if we have timeline events
        if table_counts["timeline_events"] < 1:
            print("❌ No timeline events found in database")
            return False
        
        conn.close()
        print("✅ Database validation successful")
    except Exception as e:
        print(f"❌ Database validation failed: {e}")
        return False
    
    # Test Excel export
    if not skip_excel:
        print("Testing Excel export...")
        try:
            excel_path = export_to_excel(str(db_path))
            if not os.path.exists(excel_path):
                print(f"❌ Excel file not found: {excel_path}")
                return False
            
            print(f"✅ Excel export successful: {excel_path}")
        except Exception as e:
            print(f"❌ Excel export failed: {e}")
            return False
    
    print("=== Integration Test Completed Successfully ===")
    return True

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Run integration test on SMITE 2 Combat Log Parser")
    parser.add_argument("log_file", help="Path to the combat log file to test")
    parser.add_argument("--keep-db", action="store_true", help="Don't delete existing database file")
    parser.add_argument("--skip-excel", action="store_true", help="Skip Excel export test")
    
    args = parser.parse_args()
    
    success = clean_test(args.log_file, args.keep_db, args.skip_excel)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 