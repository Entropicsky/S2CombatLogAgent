#!/usr/bin/env python3
"""
Test script for the full multi-query pipeline.

This script tests the complete pipeline from QueryAnalystAgent to DataEngineerAgent
with multi-query capabilities on real-world scenarios.
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
logger = logging.getLogger("test_pipeline_multi_query")

# Load environment variables from .env file
load_dotenv()

# Import the agents and data package
from smite2_agent.agents.query_analyst import QueryAnalystAgent
from smite2_agent.agents.data_engineer import DataEngineerAgent
from smite2_agent.pipeline.base.data_package import DataPackage

# Test queries that should trigger multi-query analysis
PIPELINE_TEST_QUERIES = [
    "Compare the damage output of MateoUwU and psychotic8BALL",
    "Show me damage dealt in the first 10 minutes versus the last 10 minutes",
    "Analyze both damage and healing for each player",
    "Compare player performance in early, mid, and late game phases"
]

async def test_pipeline_multi_query(db_path: Path, test_index: int, verbose: bool = False):
    """
    Test the full pipeline with multi-query capabilities.
    
    Args:
        db_path: Path to the database
        test_index: Index of the test to run (or -1 for all tests)
        verbose: Whether to show verbose output
    """
    queries_to_run = [PIPELINE_TEST_QUERIES[test_index]] if test_index >= 0 else PIPELINE_TEST_QUERIES
    
    for query in queries_to_run:
        print(f"\n{'='*80}")
        print(f"TESTING PIPELINE WITH QUERY: '{query}'")
        print(f"{'='*80}\n")
        
        # Initialize the QueryAnalystAgent
        print("Initializing QueryAnalystAgent...")
        query_analyst = QueryAnalystAgent(
            db_path=str(db_path),
            model="gpt-4o",
            temperature=0.2
        )
        
        # Initialize the DataEngineerAgent
        print("Initializing DataEngineerAgent...")
        data_engineer = DataEngineerAgent(
            db_path=db_path,
            model="gpt-4o",
            temperature=0.2,
            strict_mode=False
        )
        
        # Create a data package
        data_package = DataPackage(query=query, db_path=str(db_path))
        
        # Time the processing
        start_time = time.time()
        
        # First, print what the DataPackage contains
        print(f"\nCreated DataPackage with query: '{data_package.get_user_query()}'")
        
        # Step 1: Process with QueryAnalystAgent
        print("\nStep 1: Processing with QueryAnalystAgent...")
        
        # Access query_analyst's internal _analyze_query method directly
        # since _process apparently requires different access
        analysis = query_analyst._analyze_query(query)
        
        # Convert the data package to dict, modify it, and convert back
        package_dict = data_package.to_dict()
        package_dict["query_analysis"] = analysis
        data_package = DataPackage.from_dict(package_dict)
        
        # Get the query analysis
        query_analysis = package_dict.get("query_analysis", {})
        
        # Print query analysis summary
        print("\nQUERY ANALYSIS SUMMARY:")
        print(f"Query Type: {query_analysis.get('query_type', 'Not specified')}")
        print(f"Requires Comparison: {query_analysis.get('requires_comparison', False)}")
        print(f"Needs Multiple Queries: {query_analysis.get('needs_multiple_queries', False)}")
        
        sql_suggestions = query_analysis.get("sql_suggestion", [])
        print(f"SQL Queries Generated: {len(sql_suggestions)}")
        
        if verbose:
            print("\nSQL SUGGESTIONS:")
            for i, suggestion in enumerate(sql_suggestions, 1):
                print(f"\n{'-'*40}")
                print(f"Query {i}: {suggestion.get('purpose', 'No purpose specified')}")
                print(f"SQL: ```\n{suggestion.get('query', 'No query available')}\n```")
        
        # Step 2: Process with DataEngineerAgent
        print("\nStep 2: Processing with DataEngineerAgent...")
        result_package = await data_engineer.process_question(data_package)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Check for errors
        if result_package.has_errors():
            print("\nPIPELINE ENCOUNTERED ERRORS:")
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
        print(f"Full pipeline test completed in {processing_time:.2f} seconds")
        print(f"{'='*40}")

def main():
    parser = argparse.ArgumentParser(description='Test the full pipeline with multi-query capabilities')
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
    asyncio.run(test_pipeline_multi_query(db_path, args.test, args.verbose))

if __name__ == "__main__":
    main() 