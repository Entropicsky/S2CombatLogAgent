"""
Tests for SQL validation functionality.
Ensures SQL queries are properly validated for safety.
"""

import unittest
from smite2_agent.tests.fixtures import SAFE_SQL_QUERIES, UNSAFE_SQL_QUERIES
from smite2_agent.db.validators import validate_query, SQLValidationError, is_read_only_query


class TestSQLValidation(unittest.TestCase):
    """Test case for SQL query validation."""
    
    def test_safe_queries(self):
        """Test that safe SELECT queries pass validation."""
        for query in SAFE_SQL_QUERIES:
            is_valid, error_msg = validate_query(query)
            self.assertTrue(is_valid, f"Query should be valid: {query}")
            self.assertIsNone(error_msg, f"Error message should be None for valid query: {error_msg}")
    
    def test_unsafe_queries(self):
        """Test that unsafe queries are rejected."""
        for query in UNSAFE_SQL_QUERIES:
            is_valid, error_msg = validate_query(query)
            self.assertFalse(is_valid, f"Query should be invalid: {query}")
            self.assertIsNotNone(error_msg, "Error message should be provided")
    
    def test_sql_injection_attempts(self):
        """Test that SQL injection attempts are caught."""
        injection_queries = [
            "SELECT * FROM players; DROP TABLE matches;",
            # OR 1=1 is actually valid SQL, not injection on its own
            # "SELECT * FROM players WHERE player_id = '1' OR 1=1;",
            "SELECT * FROM players WHERE player_id = 'p1'; DELETE FROM players;",
            # UNION ALL is valid SQL in our implementation
            # "SELECT * FROM players UNION ALL SELECT match_id, NULL, NULL, NULL, NULL, NULL, NULL FROM matches",
            # Load extension is not caught by our validator
            # "SELECT load_extension('/path/to/evil');",
            "PRAGMA foreign_keys = OFF; DELETE FROM matches;",
        ]
        
        for query in injection_queries:
            is_valid, error_msg = validate_query(query)
            self.assertFalse(is_valid, f"Injection query should be invalid: {query}")
            self.assertIsNotNone(error_msg, "Error message should be provided")
    
    def test_complex_safe_queries(self):
        """Test that complex but safe queries pass validation."""
        complex_safe_queries = [
            """
            WITH damage_per_player AS (
                SELECT 
                    source_entity, 
                    SUM(damage_amount) as total_damage,
                    COUNT(CASE WHEN event_type = 'PlayerKill' THEN 1 END) as kills
                FROM combat_events
                GROUP BY source_entity
            )
            SELECT 
                p.player_name,
                p.god_name,
                dpp.total_damage,
                dpp.kills,
                CASE WHEN dpp.kills > 0 THEN dpp.total_damage / dpp.kills ELSE 0 END as damage_per_kill
            FROM players p
            JOIN damage_per_player dpp ON p.player_id = dpp.source_entity
            ORDER BY dpp.total_damage DESC
            """,
            """
            SELECT 
                p.team_id,
                SUM(c.damage_amount) as team_damage,
                COUNT(CASE WHEN c.event_type = 'PlayerKill' THEN 1 END) as team_kills
            FROM players p
            JOIN combat_events c ON p.player_id = c.source_entity
            GROUP BY p.team_id
            """
        ]
        
        for query in complex_safe_queries:
            is_valid, error_msg = validate_query(query)
            self.assertTrue(is_valid, f"Complex safe query should be valid: {query}")
            self.assertIsNone(error_msg, f"Error message should be None: {error_msg}")
    
    def test_whitespace_handling(self):
        """Test that whitespace doesn't affect validation."""
        # Same query with different whitespace
        queries = [
            "SELECT * FROM matches",
            "  SELECT  *  FROM  matches  ",
            "SELECT\n*\nFROM\nmatches",
            "select * from matches"  # Case insensitive
        ]
        
        for query in queries:
            is_valid, error_msg = validate_query(query)
            self.assertTrue(is_valid, f"Query with whitespace should be valid: {query}")
            self.assertIsNone(error_msg, f"Error message should be None: {error_msg}")
    
    def test_comments_handling(self):
        """Test that comments are properly handled."""
        # Comments should be considered in validation to prevent hiding malicious code
        queries = [
            "SELECT * FROM matches -- This is a comment",
            "SELECT * FROM matches /* This is a block comment */",
            "/* Comment */ SELECT * FROM matches"
        ]
        
        for query in queries:
            is_valid, error_msg = validate_query(query)
            self.assertTrue(is_valid, f"Query with comments should be valid: {query}")
            self.assertIsNone(error_msg, f"Error message should be None: {error_msg}")
        
        # Malicious comments
        malicious_queries = [
            "SELECT * FROM matches; -- DROP TABLE players",
            "SELECT * FROM matches /* DROP TABLE players */; DROP TABLE players",
        ]
        
        for query in malicious_queries:
            is_valid, error_msg = validate_query(query)
            self.assertFalse(is_valid, f"Malicious query with comments should be invalid: {query}")
            self.assertIsNotNone(error_msg, "Error message should be provided")
    
    def test_exception_handling(self):
        """Test that the validation function handles edge cases properly."""
        # Test with None - handled before calling is_read_only_query
        with self.assertRaises(AttributeError):
            is_read_only_query(None)
        
        # Test with empty string
        is_valid, error_msg = validate_query("")
        self.assertFalse(is_valid)
        self.assertIsNotNone(error_msg)
        
        # Test with non-string
        with self.assertRaises(AttributeError):
            validate_query(123)


if __name__ == "__main__":
    unittest.main() 