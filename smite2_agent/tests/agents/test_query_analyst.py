"""
Tests for the Query Analyst Agent.

This module contains tests for the Query Analyst Agent, verifying its ability to:
1. Extract match context from the database
2. Analyze user queries
3. Identify query intent and required data
4. Enhance queries with domain-specific knowledge
"""

import os
import asyncio
import unittest
import sqlite3
from pathlib import Path
from typing import Dict, Any

from smite2_agent.agents.query_analyst import QueryAnalystAgent

# Test database path
TEST_DB_PATH = os.environ.get("TEST_DB_PATH", "data/CombatLogExample.db")

# Simple DataPackage for testing
class SimpleDataPackage:
    """Simplified DataPackage for testing."""
    
    def __init__(self, query=""):
        self.query = query
        self.data = {}

class TestQueryAnalystAgent(unittest.TestCase):
    """Test suite for Query Analyst Agent."""

    def setUp(self):
        """Set up the test environment."""
        # Ensure the test database exists
        if not os.path.exists(TEST_DB_PATH):
            raise FileNotFoundError(f"Test database not found at {TEST_DB_PATH}")
        
        # Create a connection to verify database access
        try:
            conn = sqlite3.connect(TEST_DB_PATH)
            conn.close()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to test database: {e}")
        
        # Initialize the agent with test configuration
        self.agent = QueryAnalystAgent(
            name="test_query_analyst",
            db_path=TEST_DB_PATH,
            model="gpt-3.5-turbo",  # Use a smaller model for tests
            temperature=0.0,  # Deterministic for testing
        )
        
        # Create a clean data package for testing
        self.data_package = SimpleDataPackage()
        self.data_package.data = {}

    def test_extract_match_context(self):
        """Test the agent's ability to extract match context from the database."""
        # Run the extract match context method
        match_context = self.agent._extract_match_context()
        
        # Verify match_context has the expected structure
        self.assertIsInstance(match_context, dict)
        
        # Check for player information
        self.assertIn('players', match_context)
        self.assertIsInstance(match_context['players'], list)
        
        # Check for match information
        self.assertIn('match_info', match_context)
        self.assertIsInstance(match_context['match_info'], dict)
        
        # Check for combat statistics
        self.assertIn('combat_stats', match_context)
        self.assertIsInstance(match_context['combat_stats'], dict)

    def test_analyze_query_basic(self):
        """Test the agent's ability to analyze a basic query."""
        # Set up the data package with a basic query
        self.data_package.query = "Who dealt the most damage in the match?"
        
        # Run the analyze method directly
        analysis_result = self.agent._analyze_query(self.data_package.query)
        
        # Verify the analysis result
        self.assertIsInstance(analysis_result, dict)
        self.assertIn('query_type', analysis_result)
        self.assertIn('entities', analysis_result)
        self.assertIn('metrics', analysis_result)
        
        # Check for query understanding
        self.assertIn('most damage', analysis_result['metrics'])

    def test_analyze_query_complex(self):
        """Test the agent's ability to analyze a complex, multi-part query."""
        # Set up the data package with a complex query requiring multiple SQL queries
        self.data_package.query = "Compare the damage output of PlayerOne in the first 10 minutes versus the last 10 minutes, and show how it compares to PlayerTwo."
        
        # Run the analyze method directly
        analysis_result = self.agent._analyze_query(self.data_package.query)
        
        # Verify the analysis result handles multi-part queries
        self.assertIsInstance(analysis_result, dict)
        self.assertIn('query_type', analysis_result)
        self.assertIn('entities', analysis_result)
        self.assertIn('metrics', analysis_result)
        self.assertIn('time_ranges', analysis_result)
        
        # Check for player entities
        self.assertIn('PlayerOne', analysis_result['entities'])
        self.assertIn('PlayerTwo', analysis_result['entities'])
        
        # Check for time ranges
        time_ranges = analysis_result['time_ranges']
        self.assertEqual(len(time_ranges), 2)  # Should identify two time ranges

    def test_process_with_data_package(self):
        """Test the agent's full process method with a data package."""
        # Set up the data package
        self.data_package.query = "What abilities did PlayerOne use most effectively?"
        
        # Execute the process
        asyncio.run(self.agent._process(self.data_package))
        
        # Verify the data package was updated correctly
        self.assertIn('query_analysis', self.data_package.data)
        self.assertIn('match_context', self.data_package.data)
        
        # Verify the query analysis data
        query_analysis = self.data_package.data['query_analysis']
        self.assertIn('query_type', query_analysis)
        self.assertIn('entities', query_analysis)
        self.assertIn('sql_suggestion', query_analysis)
        
        # Check that it generated SQL suggestions
        self.assertIsInstance(query_analysis['sql_suggestion'], list)
        self.assertGreater(len(query_analysis['sql_suggestion']), 0)

def run_tests():
    """Run the tests."""
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == "__main__":
    unittest.main() 