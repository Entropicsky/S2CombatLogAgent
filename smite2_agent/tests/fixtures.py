"""
Test fixtures for SMITE 2 Combat Log Agent.
Provides utilities for testing with the real CombatLogExample.db file.
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional

# Path to the real sample database
DEFAULT_DB_PATH = Path("data/CombatLogExample.db")

def get_test_db_path() -> Path:
    """Get the path to the test database.
    
    Returns:
        Path to the CombatLogExample.db file
    
    Raises:
        FileNotFoundError: If the database file does not exist
    """
    db_path = DEFAULT_DB_PATH
    
    if not db_path.exists():
        raise FileNotFoundError(f"Test database file not found: {db_path}")
    
    return db_path

def get_test_db_connection() -> sqlite3.Connection:
    """Get a connection to the test database.
    
    Returns:
        Open connection to the test database
    """
    db_path = get_test_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

# SQL queries for testing based on actual database schema
SAFE_SQL_QUERIES = [
    "SELECT * FROM matches LIMIT 1",
    "SELECT player_name, god_name FROM players WHERE team_id = 1 LIMIT 5",
    "SELECT COUNT(*) FROM combat_events WHERE damage_amount > 0",
    "SELECT p.player_name, COUNT(c.event_id) as damage_events FROM players p JOIN combat_events c ON p.player_id = c.source_entity GROUP BY p.player_id",
    """
    WITH damage_stats AS (
        SELECT source_entity, SUM(damage_amount) as total_damage 
        FROM combat_events 
        WHERE damage_amount > 0
        GROUP BY source_entity
    ) 
    SELECT p.player_name, ds.total_damage 
    FROM players p 
    JOIN damage_stats ds ON p.player_id = ds.source_entity 
    ORDER BY ds.total_damage DESC
    """
]

UNSAFE_SQL_QUERIES = [
    "DROP TABLE matches",
    "DELETE FROM players",
    "UPDATE combat_events SET damage_amount = 0",
    "INSERT INTO matches VALUES (999, 'hack', 'hack', 'now', 'later', 0, NULL, NULL)",
    "CREATE TABLE evil (id INTEGER PRIMARY KEY)",
    "PRAGMA journal_mode = WAL",
    "ATTACH DATABASE '/tmp/evil.db' AS evil"
] 