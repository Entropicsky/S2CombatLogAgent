"""
Tests for the database connection manager functionality.
Verifies read-only enforcement and connection management.
"""

import unittest
import sqlite3
from pathlib import Path

from smite2_agent.tests.fixtures import get_test_db_path
from smite2_agent.db.connection import get_connection, DatabaseConnection


class TestDatabaseConnection(unittest.TestCase):
    """Test case for database connection manager."""
    
    def setUp(self):
        """Set up database path."""
        self.db_path = get_test_db_path()
    
    def test_get_connection(self):
        """Test that get_connection returns a valid DatabaseConnection."""
        db_conn = get_connection(self.db_path)
        self.assertIsNotNone(db_conn)
        self.assertIsInstance(db_conn, DatabaseConnection)
        
        # Verify connection works for reading
        result = db_conn.execute_query("SELECT COUNT(*) FROM matches")
        self.assertGreater(result[0]['COUNT(*)'], 0, "Should have at least one match in the database")
    
    def test_readonly_mode(self):
        """Test that the connection is in read-only mode."""
        db_conn = get_connection(self.db_path)
        
        # Attempt to modify data (should fail)
        with self.assertRaises(ValueError):
            db_conn.execute_query("INSERT INTO matches VALUES (999, 'new-match', 'Arena', 'now', 'later', 300, NULL, NULL)")
        
        with self.assertRaises(ValueError):
            db_conn.execute_query("UPDATE matches SET map_name = 'Joust'")
        
        with self.assertRaises(ValueError):
            db_conn.execute_query("DELETE FROM matches")
    
    def test_query_only_pragma(self):
        """Test that PRAGMA query_only is set."""
        db_conn = get_connection(self.db_path)
        conn = db_conn.get_connection()
        
        # Check PRAGMA setting using the internal connection
        cursor = conn.cursor()
        cursor.execute("PRAGMA query_only")
        query_only = cursor.fetchone()[0]
        self.assertEqual(query_only, 1)
    
    def test_connection_is_isolated(self):
        """Test that each call to get_connection returns an isolated DatabaseConnection."""
        db_conn1 = get_connection(self.db_path)
        db_conn2 = get_connection(self.db_path)
        
        # Verify connections are different objects
        self.assertIsNot(db_conn1, db_conn2)
        
        # Test that both connections can execute queries independently
        result1 = db_conn1.execute_query("SELECT * FROM matches LIMIT 1")
        self.assertEqual(len(result1), 1)
        
        result2 = db_conn2.execute_query("SELECT COUNT(*) FROM players")
        self.assertGreater(result2[0]['COUNT(*)'], 0)
    
    def test_execute_query(self):
        """Test execute_query method with valid queries."""
        db_conn = get_connection(self.db_path)
        
        # Simple query
        result = db_conn.execute_query("SELECT * FROM matches LIMIT 2")
        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), 2)
        
        # Query with parameters
        result = db_conn.execute_query("SELECT * FROM players WHERE team_id = ?", (1,))
        for row in result:
            self.assertEqual(row['team_id'], 1)
    
    def test_get_table_schema(self):
        """Test get_table_schema method."""
        db_conn = get_connection(self.db_path)
        
        schema = db_conn.get_table_schema("players")
        self.assertGreater(len(schema), 0)
        
        # Check for expected columns
        column_names = [col['name'] for col in schema]
        for expected in ['player_id', 'player_name', 'team_id', 'god_name']:
            self.assertIn(expected, column_names)
    
    def test_get_all_tables(self):
        """Test get_all_tables method."""
        db_conn = get_connection(self.db_path)
        
        tables = db_conn.get_all_tables()
        self.assertGreater(len(tables), 0)
        
        # Check for expected tables
        for expected in ['matches', 'players', 'combat_events']:
            self.assertIn(expected, tables)


if __name__ == "__main__":
    unittest.main() 