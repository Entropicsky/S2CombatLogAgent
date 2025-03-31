#!/usr/bin/env python3
"""
Test runner for Query Analyst Agent tests.

This script runs the Query Analyst Agent tests to verify its functionality.
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment")

# Set OpenAI API key for the Agents SDK
os.environ["OPENAI_API_KEY"] = api_key

# Import the test module
from smite2_agent.tests.agents.test_query_analyst import run_tests

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    print("Running Query Analyst Agent tests...")
    
    # Run the tests
    run_tests()
    
    print("\nDone") 