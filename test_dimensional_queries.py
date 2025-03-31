#!/usr/bin/env python3
"""
Test script for evaluating the enhanced DataEngineerAgent with challenging queries.

This script tests the agent's ability to handle difficult entity mapping, temporal
concepts, and complex relationships in queries.
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
logger = logging.getLogger("test_dimensional_queries")

# Load environment variables from .env file
load_dotenv()

# Check if API key is set
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment. Please set it in a .env file.")

# Import the orchestrator
from smite2_agent.agents.orchestrator import Orchestrator

# Define challenging test questions
CHALLENGING_QUESTIONS = [
    # Entity name variations
    "What damage did Fire Giant do in the match?",  # Tests entity name mapping (FireGiant)
    
    # Temporal concept queries
    "What was the final objective captured in the match?",  # Tests detecting "final" → MAX(timestamp)
    "Which player scored first blood?",  # Tests detecting "first" → MIN(timestamp)
    
    # Entity-specific queries
    "How much damage did Mateo do with Sacred Bell?",  # Tests player name and ability mapping
    "Which abilities did psychotic8ball use the most?",  # Tests player name variation and aggregation
    
    # Complex aggregations
    "What's the kill-to-death ratio for each player?",  # Tests multiple aggregation functions
    
    # Complex joins
    "Which god dealt the most healing and how much?",  # Tests joining player, god, and combat_events
    
    # Unusual entity references
    "Show me stats for the player with the most assists",  # Tests subquery for entity identification
    
    # Mixed concepts
    "Did Taco kill more enemies with abilities or basic attacks?",  # Tests understanding attack types
    
    # Comparative queries
    "Which player had the highest damage per minute?"  # Tests complex calculation
]

async def test_query(orchestrator, query: str):
    """Test the orchestrator with a specific query."""
    print(f"\n{'='*80}")
    print(f"TESTING QUERY: '{query}'")
    print(f"{'='*80}\n")
    
    # Process the query
    result = await orchestrator.process_query(query)
    
    # Check if successful
    if result["success"]:
        print("QUERY PROCESSED SUCCESSFULLY")
        print("\nGENERATED SQL:")
        print(f"```sql\n{result['data_package']['data']['query_results']['query1']['sql']}\n```")
        print("\nRESPONSE:")
        print("-" * 80)
        print(result["response"])
        print("-" * 80)
        
        # Print domain analysis for debugging
        if "domain_analysis" in result["data_package"]:
            print("\nDOMAIN ANALYSIS:")
            print("-" * 80)
            domain_analysis = result["data_package"]["domain_analysis"]
            for concept, mapping in domain_analysis.get("database_mappings", {}).items():
                if isinstance(mapping, dict) and "exact_value" in mapping:
                    print(f"✓ Mapped '{concept}' → '{mapping['exact_value']}'")
            print("-" * 80)
    else:
        print("QUERY PROCESSING FAILED")
        print("\nERROR:")
        print("-" * 80)
        print(result["response"])
        print("-" * 80)
        print("\nALL ERRORS:")
        for error in result.get("all_errors", []):
            print(f"- {error}")
    
    return result["success"]

async def run_tests():
    """Run all test queries."""
    # Initialize the orchestrator
    db_path = Path("data/CombatLogExample.db")
    orchestrator = Orchestrator(
        db_path=db_path,
        model="gpt-4o",
        strict_mode=False  # Set to True for stricter validation
    )
    
    # Test each query
    successes = 0
    for i, query in enumerate(CHALLENGING_QUESTIONS, 1):
        print(f"\nTest {i}/{len(CHALLENGING_QUESTIONS)}")
        success = await test_query(orchestrator, query)
        if success:
            successes += 1
    
    # Print summary
    print("\n" + "="*40)
    print(f"RESULTS: {successes}/{len(CHALLENGING_QUESTIONS)} queries successful")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_tests()) 