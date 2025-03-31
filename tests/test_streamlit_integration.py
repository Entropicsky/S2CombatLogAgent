#!/usr/bin/env python3
"""
Integration test for the Streamlit app.

This test uses the actual CombatLogExample.log file to test the full workflow.
"""

import os
import sys
import json
import unittest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from smite2_agent.ui.streamlit_app import (
    extract_match_id_from_file,
    process_log_file,
    process_query,
    parse_debug_json
)


class TestStreamlitIntegration(unittest.TestCase):
    """Integration test for the Streamlit app."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that are used for all tests."""
        # Path to the example log file
        cls.example_log_path = parent_dir / "CombatLogExample.log"
        
        # Check if the example log file exists
        if not cls.example_log_path.exists():
            raise unittest.SkipTest(f"Example log file not found: {cls.example_log_path}")
        
        # Path to the example database
        cls.example_db_path = parent_dir / "data" / "CombatLogExample.db"
        
        # Check if the example database exists
        if not cls.example_db_path.exists():
            raise unittest.SkipTest(f"Example database not found: {cls.example_db_path}")
        
        # Create a temporary directory for test files
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.temp_path = Path(cls.temp_dir.name)
        
        # Set up environment for tests
        os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "dummy-key")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures."""
        cls.temp_dir.cleanup()
    
    def test_extract_match_id_from_real_file(self):
        """Test extracting match ID from the real log file."""
        match_id = extract_match_id_from_file(self.example_log_path)
        # This should be a valid match ID from the log file or a fallback based on filename
        self.assertTrue(match_id.startswith("match-"))
    
    @unittest.skip("Skipping because this is a long-running test that actually processes the log file")
    def test_process_real_log_file(self):
        """Test processing the real log file."""
        # This test actually processes the log file, which can take a while
        db_path = process_log_file(self.example_log_path)
        
        # Verify that the database was created
        self.assertIsNotNone(db_path)
        self.assertTrue(db_path.exists())
    
    @patch("smite2_agent.agents.query_analyst.QueryAnalystAgent._process")
    @patch("smite2_agent.agents.data_engineer.DataEngineerAgent.process_question")
    @patch("smite2_agent.agents.data_analyst.DataAnalystAgent.process_data")
    @patch("smite2_agent.agents.response_composer.ResponseComposerAgent.generate_response")
    @patch("smite2_agent.agents.followup_predictor.FollowUpPredictorAgent._process")
    def test_process_query_with_mocks(self, mock_followup, mock_composer, mock_analyst, mock_engineer, mock_query_analyst):
        """Test processing a query with mocked agents."""
        # Set up the mock data package
        mock_package = MagicMock()
        mock_package.to_debug_json.return_value = json.dumps({
            "user_response": {
                "formatted_answer": "Test answer",
                "suggested_followups": ["What about X?", "Tell me about Y?"]
            }
        })
        
        # Set up the mock agent responses
        mock_query_analyst.return_value = mock_package
        mock_engineer.return_value = mock_package
        mock_analyst.return_value = mock_package
        mock_composer.return_value = mock_package
        mock_followup.return_value = mock_package
        
        # Process a test query - use asyncio.run to handle the coroutine
        result = asyncio.run(process_query(
            db_path=self.example_db_path,
            query="Who dealt the most damage?",
            model="gpt-4o",
            include_followups=True
        ))
        
        # Check that all the agents were called
        mock_query_analyst.assert_called_once()
        mock_engineer.assert_called_once()
        mock_analyst.assert_called_once()
        mock_composer.assert_called_once()
        mock_followup.assert_called_once()
        
        # Check the result
        self.assertEqual(result, mock_package)
    
    @unittest.skipIf(not os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") == "dummy-key",
                    "Skipping because this test requires a valid OpenAI API key")
    def test_real_query_processing(self):
        """Test processing a real query using the actual agents."""
        # This test requires a valid OpenAI API key and will make API calls
        
        # Process a simple query using the event loop
        query = "Who dealt the most damage in the match?"
        result = asyncio.run(process_query(
            db_path=self.example_db_path, 
            query=query,
            include_followups=False  # Disable follow-ups to make the test faster
        ))
        
        # Parse the debug JSON
        debug_json = result.to_debug_json()
        debug_data = parse_debug_json(debug_json)
        
        # Verify that we got a response
        self.assertIn("user_response", debug_data)
        self.assertIn("formatted_answer", debug_data["user_response"])
        
        # Verify that SQL queries were executed
        self.assertIn("pipeline_details", debug_data)
        self.assertIn("queries", debug_data["pipeline_details"])
        
        # Verify that the response mentions the top damage dealer
        # This is a real test against actual data, so we should see real results
        formatted_answer = debug_data["user_response"]["formatted_answer"]
        self.assertTrue("damage" in formatted_answer.lower())


if __name__ == "__main__":
    unittest.main() 