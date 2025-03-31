#!/usr/bin/env python3
"""
Example demonstrating the complete SMITE 2 Combat Log Agent pipeline.

This example shows how the full agent pipeline works:
1. Query Analyst analyzes the user's question
2. Data Engineer creates and executes SQL queries
3. Data Analyst analyzes the query results
4. Response Composer creates the final response
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from pprint import pprint
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment")

# Set OpenAI API key for the Agents SDK
os.environ["OPENAI_API_KEY"] = api_key

# Add parent directory to path for importing smite2_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smite2_agent.agents.orchestrator import Orchestrator

# Database path
DB_PATH = Path("data/CombatLogExample.db")

# Set up schema cache path
SCHEMA_CACHE_PATH = Path("data/schema_cache.json")

# Colors for console output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

async def process_query(orchestrator, query):
    """Process a query and display the results with detailed tracing."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}Processing Query: '{query}'{Colors.ENDC}\n")
    
    # Process the query
    result = await orchestrator.process_query(query)
    
    # Display the results
    if result["success"]:
        print(f"\n{Colors.GREEN}{Colors.BOLD}Final Response:{Colors.ENDC}")
        print(f"{Colors.GREEN}{result['response']}{Colors.ENDC}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}Error:{Colors.ENDC}")
        print(f"{Colors.RED}{result['response']}{Colors.ENDC}")
        if "all_errors" in result:
            print(f"\n{Colors.RED}All Errors:{Colors.ENDC}")
            for error in result["all_errors"]:
                print(f"{Colors.RED}- {error}{Colors.ENDC}")
        return
    
    # If data package is available, show processing details
    if "data_package" in result:
        data_package = result["data_package"]
        
        # Show processing history
        if "metadata" in data_package and "processing_history" in data_package["metadata"]:
            history = data_package["metadata"]["processing_history"]
            print(f"\n{Colors.BLUE}{Colors.BOLD}Processing Pipeline:{Colors.ENDC}")
            
            for i, stage in enumerate(history):
                status_color = Colors.GREEN if stage["status"] == "success" else Colors.RED
                print(f"{Colors.BLUE}{i+1}. {stage['stage']} ({stage['agent_id']}): {status_color}{stage['status']}{Colors.ENDC}")
                if "start_time" in stage and "end_time" in stage and stage["end_time"]:
                    print(f"   Time: {stage['start_time']} to {stage['end_time']}")
        
        # Show Query Analysis
        if "query_analysis" in data_package:
            analysis = data_package["query_analysis"]
            print(f"\n{Colors.CYAN}{Colors.BOLD}Query Analysis:{Colors.ENDC}")
            print(f"{Colors.CYAN}Query Type: {analysis.get('query_type', 'Unknown')}{Colors.ENDC}")
            print(f"{Colors.CYAN}Intent: {analysis.get('intent', 'Unknown')}{Colors.ENDC}")
            
            if "required_data_points" in analysis:
                print(f"{Colors.CYAN}Required Data Points: {', '.join(analysis['required_data_points'])}{Colors.ENDC}")
            
            if "required_tables" in analysis:
                print(f"{Colors.CYAN}Required Tables: {', '.join(analysis['required_tables'])}{Colors.ENDC}")
        
        # Show SQL Queries Used
        if "data" in data_package and "query_results" in data_package["data"]:
            queries = data_package["data"]["query_results"]
            print(f"\n{Colors.YELLOW}{Colors.BOLD}SQL Queries Used:{Colors.ENDC}")
            
            for query_id, query_data in queries.items():
                print(f"{Colors.YELLOW}Query {query_id}:{Colors.ENDC}")
                print(f"{Colors.YELLOW}{query_data.get('sql', 'No SQL available')}{Colors.ENDC}")
                print(f"{Colors.YELLOW}Rows: {query_data.get('result_summary', {}).get('row_count', 'Unknown')}{Colors.ENDC}")
        
        # Show Analysis Results
        if "analysis" in data_package and "key_findings" in data_package["analysis"]:
            findings = data_package["analysis"]["key_findings"]
            if findings:
                print(f"\n{Colors.GREEN}{Colors.BOLD}Key Findings:{Colors.ENDC}")
                for finding in findings:
                    print(f"{Colors.GREEN}- {finding.get('description', 'No description')}{Colors.ENDC}")

async def main():
    """Run the example."""
    print(f"Using database: {DB_PATH.absolute()}")
    if not DB_PATH.exists():
        print(f"Error: Database file {DB_PATH} does not exist!")
        return
    
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== Initializing Combat Log Agent Pipeline ==={Colors.ENDC}")
    
    # Create the orchestrator
    orchestrator = Orchestrator(
        db_path=DB_PATH,
        model="gpt-4o",
        strict_mode=False,
        schema_cache_path=SCHEMA_CACHE_PATH
    )
    
    # Test different types of queries covering various aspects of the match
    test_queries = [
        # Combat analysis queries
        "Who dealt the most damage in the match?",
        "Which ability did the most healing?",
        
        # Player analysis queries
        "How did MateoUwU perform in the match?",
        "What items did the support player build?",
        
        # Timeline analysis queries
        "What objectives were taken in the first 10 minutes?",
        
        # Comparison analysis queries
        "Compare the damage output between the mid and jungle players",
    ]
    
    # Process each query
    for i, query in enumerate(test_queries):
        print(f"\n{Colors.HEADER}{Colors.BOLD}Query {i+1}/{len(test_queries)}{Colors.ENDC}")
        await process_query(orchestrator, query)
        
        # Add a delay between queries to avoid rate limiting
        if i < len(test_queries) - 1:
            print(f"\n{Colors.YELLOW}Waiting 2 seconds before next query...{Colors.ENDC}")
            await asyncio.sleep(2)
    
    # Test database switching (simulated with the same database)
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== Testing Database Switching ==={Colors.ENDC}")
    print(f"Updating to the same database to demonstrate the functionality")
    orchestrator.update_database(DB_PATH)
    
    # Run one more query to verify everything still works
    await process_query(orchestrator, "Who took the most damage in the match?")

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    asyncio.run(main())
    print(f"\n{Colors.GREEN}Done{Colors.ENDC}") 