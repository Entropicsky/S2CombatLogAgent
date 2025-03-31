#!/usr/bin/env python3
"""
Test the Streamlit app implementation.
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from smite2_agent.ui.streamlit_app import (
    extract_match_id_from_file,
    process_log_file,
    parse_debug_json,
    format_output
)


class TestStreamlitApp(unittest.TestCase):
    """Test the Streamlit app functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_log_path = Path(self.temp_dir.name) / "test.log"
        
        # Create a sample log file
        with open(self.test_log_path, "w") as f:
            f.write('{"eventType": "start", "matchID": "test-match-123"}\n')
            f.write('{"eventType": "other", "data": "test"}\n')
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_extract_match_id_from_file(self):
        """Test extracting match ID from a log file."""
        # Test with a file containing a valid match ID
        match_id = extract_match_id_from_file(self.test_log_path)
        self.assertEqual(match_id, "test-match-123")
        
        # Test with a file that doesn't contain a match ID
        empty_file = Path(self.temp_dir.name) / "empty.log"
        with open(empty_file, "w") as f:
            f.write('{"eventType": "other", "data": "test"}\n')
        
        match_id = extract_match_id_from_file(empty_file)
        self.assertEqual(match_id, "match-empty")
    
    def test_parse_debug_json(self):
        """Test parsing debug JSON."""
        # Test with valid JSON
        valid_json = '{"user_response": {"formatted_answer": "Test answer"}}'
        result = parse_debug_json(valid_json)
        self.assertEqual(result["user_response"]["formatted_answer"], "Test answer")
        
        # Test with invalid JSON
        invalid_json = '{"user_response": '
        result = parse_debug_json(invalid_json)
        self.assertTrue("error" in result)
    
    @patch("smite2_agent.ui.streamlit_app.DataPackage")
    def test_format_output(self, mock_data_package):
        """Test formatting output in different formats."""
        # Mock DataPackage
        mock_package = MagicMock()
        mock_package.get_response.return_value = "Test response"
        mock_package.to_dict.return_value = {
            "enhancement": {"suggested_questions": ["Q1", "Q2"]}
        }
        mock_package.to_debug_json.return_value = '{"debug": true}'
        
        # Test text format
        text_output = format_output(mock_package, "text")
        self.assertEqual(text_output, "Test response")
        
        # Test JSON format
        json_output = format_output(mock_package, "json")
        self.assertIn("Test response", json_output)
        self.assertIn("Q1", json_output)
        
        # Test debug JSON format
        debug_output = format_output(mock_package, "debug_json")
        self.assertEqual(debug_output, '{"debug": true}')
    
    @patch("smite2_agent.ui.streamlit_app.CombatLogParser")
    def test_process_log_file(self, mock_parser_class):
        """Test processing a log file."""
        # Mock the parser
        mock_parser = MagicMock()
        mock_parser.parse_file.return_value = True
        mock_parser_class.return_value = mock_parser
        
        # Call the function
        with patch("smite2_agent.ui.streamlit_app.extract_match_id_from_file") as mock_extract:
            mock_extract.return_value = "test-match-123"
            result = process_log_file(self.test_log_path)
        
        # Check that the parser was called correctly
        mock_parser.parse_file.assert_called_once_with(str(self.test_log_path))
        
        # Check that the function returned a Path
        self.assertIsInstance(result, Path)
        
        # Test with parser failure
        mock_parser.parse_file.return_value = False
        result = process_log_file(self.test_log_path)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main() 