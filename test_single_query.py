#!/usr/bin/env python3
"""
Test script for running a single query to test the DataEngineerAgent.

This allows for testing a specific question to see how the enhanced
domain concept analysis and entity mapping works.
"""

import os
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
import argparse
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_single_query")

# Load environment variables from .env file
load_dotenv()

# Import the DataEngineerAgent directly to see detailed domain analysis
from smite2_agent.agents.data_engineer import DataEngineerAgent
from smite2_agent.pipeline.base.data_package import DataPackage

async def test_data_engineer(db_path: Path, query: str, verbose: bool = False):
    """
    Test the DataEngineerAgent with a single query.
    
    Args:
        db_path: Path to the database
        query: Query to test
        verbose: Whether to show verbose output
    """
    print(f"\n{'='*80}")
    print(f"TESTING QUERY: '{query}'")
    print(f"{'='*80}\n")
    
    # Initialize the DataEngineerAgent
    agent = DataEngineerAgent(
        db_path=db_path,
        model="gpt-4o",
        temperature=0.2,
        strict_mode=False
    )
    
    # Create a data package
    data_package = DataPackage(query=query, db_path=str(db_path))
    
    # Process the query
    print("\nProcessing query with DataEngineerAgent...\n")
    result_package = await agent.process_question(data_package)
    
    # Check for errors
    if result_package.has_errors():
        print("QUERY PROCESSING FAILED")
        print("\nERRORS:")
        for error in result_package.get_all_errors():
            print(f"- {error}")
        return
    
    # Get the query results
    query_results = result_package.get_query_results()
    if not query_results:
        print("No query results returned")
        return
    
    # Get the first query result
    query_result = list(query_results.values())[0]
    sql_query = query_result.get('sql', 'No SQL query available')
    
    print("\nGENERATED SQL:")
    print(f"```sql\n{sql_query}\n```")
    
    print("\nRESULTS:")
    data = query_result.get('data', [])
    if not data:
        print("No data returned")
    else:
        print(f"Returned {len(data)} rows")
        # Print first 5 rows
        for i, row in enumerate(data[:5]):
            print(f"Row {i+1}: {json.dumps(row, default=str)}")
        if len(data) > 5:
            print(f"... and {len(data) - 5} more rows")
    
    # Print domain analysis
    domain_analysis = result_package.get_domain_analysis()
    if domain_analysis and verbose:
        print("\nDOMAIN ANALYSIS (FULL):")
        print("-" * 80)
        print(json.dumps(domain_analysis, indent=2, default=str))
        print("-" * 80)
    elif domain_analysis:
        print("\nDOMAIN ANALYSIS (MAPPINGS):")
        print("-" * 80)
        for concept, mapping in domain_analysis.get("database_mappings", {}).items():
            if isinstance(mapping, dict):
                if "exact_value" in mapping:
                    print(f"✓ Mapped '{concept}' → exact value: '{mapping['exact_value']}'")
                elif "table" in mapping and "columns" in mapping:
                    print(f"✓ Mapped '{concept}' → table: {mapping['table']}, columns: {mapping['columns']}")
        
        print("\nSPECIAL LOGIC:")
        for concept, logic in domain_analysis.get("special_logic", {}).items():
            if isinstance(logic, dict) and "description" in logic:
                print(f"✓ Detected '{concept}': {logic['description']}")
        print("-" * 80)
        
        # Show dimensional data fetched
        print("\nDIMENSIONAL DATA FETCHED:")
        for dim, count in domain_analysis.get("dimensional_data", {}).items():
            print(f"- {dim}: {count}")
        print("-" * 80)

def main():
    parser = argparse.ArgumentParser(description='Test a single query with the DataEngineerAgent')
    parser.add_argument('--db', type=str, default='data/CombatLogExample.db', 
                        help='Path to SQLite database')
    parser.add_argument('--query', type=str, required=True,
                        help='Query to test')
    parser.add_argument('--verbose', action='store_true',
                        help='Show verbose output including full domain analysis')
    
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
    asyncio.run(test_data_engineer(db_path, args.query, args.verbose))

if __name__ == "__main__":
    main() 