"""
Tests for SQL query tools.
Verifies the SQL query execution with validation.
"""

import unittest
from typing import Dict, Any
from pathlib import Path
import sqlite3

from smite2_agent.tests.fixtures import get_test_db_path, SAFE_SQL_QUERIES, UNSAFE_SQL_QUERIES
from smite2_agent.tools.sql_tools import run_sql_query
from smite2_agent.db.validators import SQLValidationError


class TestSQLTools(unittest.TestCase):
    """Test case for SQL query tools."""
    
    def setUp(self):
        """Set up database path."""
        self.db_path = get_test_db_path()
    
    def test_run_sql_query_basic(self):
        """Test basic SQL query execution."""
        query = "SELECT * FROM matches LIMIT 1"
        result = run_sql_query(query, self.db_path)
        
        # Verify query success
        self.assertTrue(result["success"], "Query should succeed")
        self.assertIsNotNone(result["data"], "Data should be returned")
        self.assertIn("match_id", result["data"][0], "Result should include match_id")
    
    def test_run_sql_query_format_options(self):
        """Test SQL query with different format options."""
        query = "SELECT player_name, god_name FROM players LIMIT 3"
        
        # Test with default format (dict)
        result_dict = run_sql_query(query, self.db_path)
        self.assertTrue(result_dict["success"])
        self.assertIsInstance(result_dict["data"], list)
        self.assertGreater(len(result_dict["data"]), 0)
        
        # Test with markdown format
        result_md = run_sql_query(query, self.db_path, format_as="markdown")
        self.assertTrue(result_md["success"])
        self.assertIsInstance(result_md["data"], str)
        self.assertIn("|", result_md["data"], "Markdown should contain pipe characters")
        self.assertIn("player_name", result_md["data"], "Markdown should include headers")
        
        # Test with CSV format
        result_csv = run_sql_query(query, self.db_path, format_as="csv")
        self.assertTrue(result_csv["success"])
        self.assertIsInstance(result_csv["data"], str)
        self.assertIn(",", result_csv["data"], "CSV should contain commas")
        self.assertIn("player_name", result_csv["data"], "CSV should include headers")
    
    def test_run_sql_query_with_parameters(self):
        """Test SQL query with parameters to prevent injection."""
        # Query with parameters
        query = "SELECT * FROM players WHERE team_id = ? LIMIT 2"
        params = [1]  # Team ID 1
        
        result = run_sql_query(query, self.db_path, params=params)
        self.assertTrue(result["success"])
        self.assertGreater(len(result["data"]), 0)
        
        # Verify all returned players are from team 1
        for player in result["data"]:
            self.assertEqual(player["team_id"], 1)
    
    def test_run_sql_query_invalid_query(self):
        """Test handling of invalid SQL queries."""
        # Test that unsafe queries return an error result rather than raising an exception
        for query in UNSAFE_SQL_QUERIES:
            result = run_sql_query(query, self.db_path)
            self.assertFalse(result["success"], f"Unsafe query should fail: {query}")
            self.assertIn("error", result, "Error message should be present")
            self.assertIn("Invalid SQL query", result["error"], f"Should indicate invalid SQL: {result['error']}")
        
        # Test with syntactically invalid query
        result = run_sql_query("SELECT * FROMM players", self.db_path)
        self.assertFalse(result["success"])
        self.assertIn("error", result)
    
    def test_run_sql_query_complex(self):
        """Test execution of complex but valid SQL queries."""
        # Complex query with joins, aggregations
        complex_query = """
        WITH damage_stats AS (
            SELECT source_entity, SUM(damage_amount) as total_damage 
            FROM combat_events 
            WHERE damage_amount > 0
            GROUP BY source_entity
        )
        SELECT 
            p.player_name,
            ds.total_damage
        FROM players p
        JOIN damage_stats ds ON p.player_id = ds.source_entity
        ORDER BY ds.total_damage DESC
        LIMIT 5
        """
        
        result = run_sql_query(complex_query, self.db_path)
        self.assertTrue(result["success"])
        self.assertIsInstance(result["data"], list)
        # Results might be empty if damage_amount is NULL in all records
        # or if player_id doesn't match source_entity
        
    def test_run_sql_query_nonexistent_table(self):
        """Test query with non-existent table."""
        query = "SELECT * FROM non_existent_table"
        
        # Our implementation returns an error result rather than raising an exception
        result = run_sql_query(query, self.db_path)
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertIn("no such table", result["error"].lower())
    
    def test_run_sql_query_empty_result(self):
        """Test query that returns empty result."""
        # Query that should return no rows
        query = "SELECT * FROM players WHERE player_name = 'NonExistentPlayer'"
        
        result = run_sql_query(query, self.db_path)
        self.assertTrue(result["success"])
        self.assertEqual(len(result["data"]), 0, "Result should be empty")
    
    def test_run_sql_query_aggregate(self):
        """Test aggregate SQL query."""
        query = "SELECT COUNT(*) as total_players FROM players"
        
        result = run_sql_query(query, self.db_path)
        self.assertTrue(result["success"])
        self.assertGreater(result["data"][0]["total_players"], 0, "Should have at least one player")


if __name__ == "__main__":
    unittest.main() 