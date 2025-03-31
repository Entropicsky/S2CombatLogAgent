#!/usr/bin/env python3
"""
Test script for multi-query processing in the DataEngineerAgent.

This script tests the parallel query execution capabilities of the DataEngineerAgent
by simulating a multi-query request from QueryAnalystAgent.
"""

import os
import asyncio
import json
import logging
import time
from pathlib import Path
import argparse
from typing import List, Dict, Any
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_multi_query")

# Load environment variables from .env file
load_dotenv()

# Import the DataEngineerAgent directly
from smite2_agent.agents.data_engineer import DataEngineerAgent
from smite2_agent.pipeline.base.data_package import DataPackage

# Example multi-query tests
MULTI_QUERY_TESTS = [
    {
        "name": "Player Comparison Test",
        "query": "Compare the damage output of top two players",
        "query_analysis": {
            "query_type": "combat_analysis",
            "requires_comparison": True,
            "needs_multiple_queries": True,
            "sql_suggestion": [
                {
                    "purpose": "Get damage data for first player",
                    "query": """
                    SELECT 
                        c.source_entity as PlayerName,
                        p.god_name as GodName,
                        c.ability_name as AbilityName,
                        SUM(c.damage_amount) as TotalDamage
                    FROM combat_events c
                    JOIN players p ON c.source_entity = p.player_name
                    WHERE c.damage_amount > 0
                    AND c.source_entity = (
                        SELECT source_entity
                        FROM combat_events
                        WHERE damage_amount > 0
                        GROUP BY source_entity
                        ORDER BY SUM(damage_amount) DESC
                        LIMIT 1
                    )
                    GROUP BY c.ability_name
                    ORDER BY TotalDamage DESC
                    LIMIT 10
                    """
                },
                {
                    "purpose": "Get damage data for second player",
                    "query": """
                    SELECT 
                        c.source_entity as PlayerName,
                        p.god_name as GodName,
                        c.ability_name as AbilityName,
                        SUM(c.damage_amount) as TotalDamage
                    FROM combat_events c
                    JOIN players p ON c.source_entity = p.player_name
                    WHERE c.damage_amount > 0
                    AND c.source_entity = (
                        SELECT source_entity
                        FROM combat_events
                        WHERE damage_amount > 0
                        GROUP BY source_entity
                        ORDER BY SUM(damage_amount) DESC
                        LIMIT 1 OFFSET 1
                    )
                    GROUP BY c.ability_name
                    ORDER BY TotalDamage DESC
                    LIMIT 10
                    """
                }
            ]
        }
    },
    {
        "name": "Time Comparison Test",
        "query": "Compare damage in first 10 minutes vs last 10 minutes",
        "query_analysis": {
            "query_type": "timeline_analysis",
            "requires_comparison": True,
            "needs_multiple_queries": True,
            "sql_suggestion": [
                {
                    "purpose": "Damage analysis for first 10 minutes",
                    "query": """
                    WITH TimeInfo AS (
                        SELECT MIN(event_time) as min_time FROM combat_events
                    )
                    SELECT 
                        c.source_entity as PlayerName,
                        p.god_name as GodName,
                        SUM(c.damage_amount) as TotalDamage
                    FROM combat_events c
                    JOIN players p ON c.source_entity = p.player_name
                    CROSS JOIN TimeInfo t
                    WHERE c.damage_amount > 0
                    AND julianday(c.event_time) BETWEEN 
                        julianday(t.min_time) 
                        AND julianday(t.min_time) + 600/86400.0
                    GROUP BY c.source_entity
                    ORDER BY TotalDamage DESC
                    """
                },
                {
                    "purpose": "Damage analysis for last 10 minutes",
                    "query": """
                    WITH TimeInfo AS (
                        SELECT MAX(event_time) as max_time FROM combat_events
                    )
                    SELECT 
                        c.source_entity as PlayerName,
                        p.god_name as GodName,
                        SUM(c.damage_amount) as TotalDamage
                    FROM combat_events c
                    JOIN players p ON c.source_entity = p.player_name
                    CROSS JOIN TimeInfo t
                    WHERE c.damage_amount > 0
                    AND julianday(c.event_time) BETWEEN 
                        julianday(t.max_time) - 600/86400.0
                        AND julianday(t.max_time)
                    GROUP BY c.source_entity
                    ORDER BY TotalDamage DESC
                    """
                }
            ]
        }
    },
    {
        "name": "Multi-metric Test",
        "query": "Show damage and healing for all players",
        "query_analysis": {
            "query_type": "player_analysis",
            "requires_comparison": False,
            "needs_multiple_queries": True,
            "sql_suggestion": [
                {
                    "purpose": "Get damage data for all players",
                    "query": """
                    SELECT 
                        c.source_entity as PlayerName,
                        p.god_name as GodName,
                        SUM(c.damage_amount) as TotalDamage
                    FROM combat_events c
                    JOIN players p ON c.source_entity = p.player_name
                    WHERE c.damage_amount > 0
                    GROUP BY c.source_entity
                    ORDER BY TotalDamage DESC
                    """
                },
                {
                    "purpose": "Get healing data for all players",
                    "query": """
                    SELECT 
                        c.source_entity as PlayerName,
                        p.god_name as GodName,
                        SUM(CASE WHEN c.damage_amount < 0 THEN ABS(c.damage_amount) ELSE 0 END) as TotalHealing
                    FROM combat_events c
                    JOIN players p ON c.source_entity = p.player_name
                    WHERE c.event_type = 'Healing' OR c.damage_amount < 0
                    GROUP BY c.source_entity
                    ORDER BY TotalHealing DESC
                    """
                }
            ]
        }
    },
    {
        "name": "Three-query Test",
        "query": "Analyze player performance in early, mid, and late game",
        "query_analysis": {
            "query_type": "timeline_analysis",
            "requires_comparison": True,
            "needs_multiple_queries": True,
            "sql_suggestion": [
                {
                    "purpose": "Early game analysis (0-10 min)",
                    "query": """
                    WITH TimeInfo AS (
                        SELECT MIN(event_time) as min_time FROM combat_events
                    )
                    SELECT 
                        c.source_entity as PlayerName,
                        p.god_name as GodName,
                        SUM(c.damage_amount) as TotalDamage,
                        COUNT(CASE WHEN c.event_type = 'Kill' THEN 1 END) as Kills
                    FROM combat_events c
                    JOIN players p ON c.source_entity = p.player_name
                    CROSS JOIN TimeInfo t
                    WHERE julianday(c.event_time) BETWEEN 
                        julianday(t.min_time) 
                        AND julianday(t.min_time) + 600/86400.0
                    GROUP BY c.source_entity
                    ORDER BY TotalDamage DESC
                    """
                },
                {
                    "purpose": "Mid game analysis (10-20 min)",
                    "query": """
                    WITH TimeInfo AS (
                        SELECT MIN(event_time) as min_time FROM combat_events
                    )
                    SELECT 
                        c.source_entity as PlayerName,
                        p.god_name as GodName,
                        SUM(c.damage_amount) as TotalDamage,
                        COUNT(CASE WHEN c.event_type = 'Kill' THEN 1 END) as Kills
                    FROM combat_events c
                    JOIN players p ON c.source_entity = p.player_name
                    CROSS JOIN TimeInfo t
                    WHERE julianday(c.event_time) BETWEEN 
                        julianday(t.min_time) + 600/86400.0
                        AND julianday(t.min_time) + 1200/86400.0
                    GROUP BY c.source_entity
                    ORDER BY TotalDamage DESC
                    """
                },
                {
                    "purpose": "Late game analysis (20+ min)",
                    "query": """
                    WITH TimeInfo AS (
                        SELECT MIN(event_time) as min_time FROM combat_events
                    )
                    SELECT 
                        c.source_entity as PlayerName,
                        p.god_name as GodName,
                        SUM(c.damage_amount) as TotalDamage,
                        COUNT(CASE WHEN c.event_type = 'Kill' THEN 1 END) as Kills
                    FROM combat_events c
                    JOIN players p ON c.source_entity = p.player_name
                    CROSS JOIN TimeInfo t
                    WHERE julianday(c.event_time) > 
                        julianday(t.min_time) + 1200/86400.0
                    GROUP BY c.source_entity
                    ORDER BY TotalDamage DESC
                    """
                }
            ]
        }
    }
]

async def test_multi_query(db_path: Path, test_index: int, verbose: bool = False):
    """
    Test the DataEngineerAgent with a multi-query test.
    
    Args:
        db_path: Path to the database
        test_index: Index of the test to run (or -1 for all tests)
        verbose: Whether to show verbose output
    """
    tests_to_run = MULTI_QUERY_TESTS if test_index < 0 else [MULTI_QUERY_TESTS[test_index]]
    
    for test in tests_to_run:
        print(f"\n{'='*80}")
        print(f"RUNNING TEST: {test['name']}")
        print(f"QUERY: '{test['query']}'")
        print(f"{'='*80}\n")
        
        # Initialize the DataEngineerAgent
        agent = DataEngineerAgent(
            db_path=db_path,
            model="gpt-4o",
            temperature=0.2,
            strict_mode=False
        )
        
        # Create a data package with query analysis
        data_package = DataPackage(query=test['query'], db_path=str(db_path))
        
        # Convert the data package to dict, modify it, and convert back
        # This is a workaround for directly accessing internal data
        package_dict = data_package.to_dict()
        package_dict["query_analysis"] = test["query_analysis"]
        data_package = DataPackage.from_dict(package_dict)
        
        # Time the processing
        start_time = time.time()
        
        # Process the query
        print("\nProcessing multi-query with DataEngineerAgent...\n")
        result_package = await agent.process_question(data_package)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Check for errors
        if result_package.has_errors():
            print("QUERY PROCESSING HAD ERRORS:")
            for error in result_package.get_all_errors():
                print(f"- {error}")
        
        # Get the query results
        query_results = result_package.get_query_results()
        if not query_results:
            print("No query results returned")
            continue
        
        print(f"\nQUERY RESULTS ({len(query_results)} queries processed in {processing_time:.2f} seconds):")
        for query_id, query_result in query_results.items():
            purpose = query_result.get('purpose', 'No purpose available')
            sql_query = query_result.get('sql', 'No SQL query available')
            
            print(f"\n{'-'*40}")
            print(f"Query {query_id}: {purpose}")
            if verbose:
                print(f"SQL: ```\n{sql_query}\n```")
            
            data = query_result.get('data', [])
            if not data:
                print(f"No data returned for {query_id}")
            else:
                print(f"Returned {len(data)} rows")
                # Print first 3 rows
                for i, row in enumerate(data[:3]):
                    print(f"Row {i+1}: {json.dumps(row, default=str)}")
                if len(data) > 3:
                    print(f"... and {len(data) - 3} more rows")
        
        print(f"\n{'='*40}")
        print(f"Test completed in {processing_time:.2f} seconds")
        print(f"{'='*40}")

def main():
    parser = argparse.ArgumentParser(description='Test parallel query execution in DataEngineerAgent')
    parser.add_argument('--db', type=str, default='data/CombatLogExample.db', 
                        help='Path to SQLite database')
    parser.add_argument('--test', type=int, default=-1,
                        help='Index of test to run (default: run all tests)')
    parser.add_argument('--verbose', action='store_true',
                        help='Show verbose output including SQL queries')
    
    args = parser.parse_args()
    
    # Check if API key is set
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment. Please set it in a .env file.")
        return
    
    # Check if database exists
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: Database file not found: {db_path}")
        return
    
    # Run the test
    asyncio.run(test_multi_query(db_path, args.test, args.verbose))

if __name__ == "__main__":
    main() 