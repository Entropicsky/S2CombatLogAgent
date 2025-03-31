#!/usr/bin/env python3
"""
Test script for the SMITE 2 Combat Log Agent.

This script tests the core functionality of the agent pipeline
by running a simple query through the orchestrator.
"""

import os
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_agents")

# Load environment variables from .env file
load_dotenv()

# Check if API key is set
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment. Please set it in a .env file.")

# Import the orchestrator
from smite2_agent.agents.orchestrator import Orchestrator

async def test_query(query: str):
    """Test the orchestrator with a specific query."""
    print(f"\n=== Testing query: '{query}' ===\n")
    
    # Initialize the orchestrator
    db_path = Path("data/CombatLogExample.db")
    orchestrator = Orchestrator(
        db_path=db_path,
        model="gpt-4o",
        strict_mode=True
    )
    
    # Process the query
    result = await orchestrator.process_query(query)
    
    # Check if successful
    if result["success"]:
        print("Query processed successfully!")
        print("\nResponse:")
        print("-" * 80)
        print(result["response"])
        print("-" * 80)
    else:
        print("Query processing failed.")
        print("\nError:")
        print("-" * 80)
        print(result["response"])
        print("-" * 80)
        print("\nAll errors:")
        for error in result.get("all_errors", []):
            print(f"- {error}")
    
    return result["success"]

async def run_tests():
    """Run a series of test queries."""
    # Test simple query
    simple_query = "Who are the top 3 players by damage?"
    success_simple = await test_query(simple_query)
    
    # Only run additional tests if the simple one worked
    if success_simple:
        # Test a more complex query
        complex_query = "What are the most effective abilities used by MateoUwU and how much damage did each do?"
        await test_query(complex_query)
    
    print("\n=== Test Summary ===")
    if success_simple:
        print("✅ Basic functionality is working!")
        print("You can now use the CLI or Streamlit app to interact with the agent.")
    else:
        print("❌ Tests failed. Please check the error messages above.")

if __name__ == "__main__":
    asyncio.run(run_tests()) 