#!/usr/bin/env python3
"""
Test runner script for running all tests.

Run with: python -m smite2_agent.tests.run_tests
"""

import os
import sys
import unittest
import argparse

# Add the parent directory to the path so we can import smite2_agent
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


def run_tests(test_type=None):
    """
    Run the tests.
    
    Args:
        test_type: Type of tests to run ('db', 'sql', 'chart', 'agent', or None for all)
    """
    loader = unittest.TestLoader()
    
    if test_type == 'db':
        # Database tests
        print("Running database tests...")
        test_files = [
            'test_db_connection.py',
            'test_schema_extraction.py'
        ]
    elif test_type == 'sql':
        # SQL tests
        print("Running SQL tests...")
        test_files = [
            'test_sql_validators.py',
            'test_sql_tools.py'
        ]
    elif test_type == 'chart':
        # Chart tests
        print("Running chart tests...")
        test_files = [
            'test_chart_tools.py'
        ]
    elif test_type == 'agent':
        # Agent and LLM tests
        print("Running agent and LLM integration tests...")
        test_files = [
            'test_openai_agent.py',
            'test_function_tools.py',
            'test_pandasai_integration.py',
            'test_agent_handoff.py'
        ]
    else:
        # All tests
        print("Running all tests...")
        test_files = [
            # Database tests
            'test_db_connection.py',
            'test_schema_extraction.py',
            # SQL tests
            'test_sql_validators.py',
            'test_sql_tools.py',
            # Chart tests
            'test_chart_tools.py',
            # Agent and LLM tests
            'test_openai_agent.py',
            'test_function_tools.py',
            'test_pandasai_integration.py',
            'test_agent_handoff.py'
        ]
    
    tests = unittest.TestSuite()
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    for test_file in test_files:
        test_file_path = os.path.join(test_dir, test_file)
        if os.path.exists(test_file_path):
            # If the file exists, load the tests
            file_tests = loader.discover(test_dir, pattern=test_file)
            tests.addTest(file_tests)
        else:
            print(f"Warning: Test file {test_file} not found")
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(tests)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run SMITE 2 Combat Log Agent tests')
    parser.add_argument('--type', choices=['db', 'sql', 'chart', 'agent', 'all'], 
                        default='all', help='Type of tests to run')
    
    args = parser.parse_args()
    test_type = None if args.type == 'all' else args.type
    run_tests(test_type) 