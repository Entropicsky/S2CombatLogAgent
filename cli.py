#!/usr/bin/env python3
"""
Command-line interface for the SMITE 2 Combat Log Agent.

This script provides a simple CLI for interacting with the agent
and querying the combat log database.
"""

import os
import sys
import asyncio
import argparse
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("smite2_cli")

# Load environment variables from .env file
load_dotenv()

# Check if API key is set
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("OPENAI_API_KEY not found in environment. Please set it in a .env file.")
    sys.exit(1)

# Import the orchestrator
try:
    from smite2_agent.agents.orchestrator import Orchestrator
except ImportError:
    logger.error("Failed to import Orchestrator. Make sure the package is installed.")
    sys.exit(1)

async def interactive_mode(db_path: Path, model: str, strict_mode: bool):
    """
    Run the CLI in interactive mode.
    
    Args:
        db_path: Path to the database file
        model: Model to use for the agents
        strict_mode: Whether to use strict mode for guardrails
    """
    print(f"SMITE 2 Combat Log Agent - Interactive Mode")
    print(f"Using database: {db_path}")
    print(f"Using model: {model}")
    print(f"Strict mode: {'Enabled' if strict_mode else 'Disabled'}")
    print("\nInitializing orchestrator... (this may take a moment)")
    
    try:
        # Initialize the orchestrator
        orchestrator = Orchestrator(
            db_path=db_path,
            model=model,
            strict_mode=strict_mode,
            schema_cache_path=Path("data/schema_cache.json")
        )
        
        print("\nReady for queries! Type 'exit' to quit.\n")
        
        # Main loop
        while True:
            # Get user input
            user_input = input("\n> ")
            
            # Check for exit command
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break
            
            # Check for empty input
            if not user_input.strip():
                continue
                
            try:
                # Process the query
                print("Processing query... (this may take a moment)")
                result = await orchestrator.process_query(user_input)
                
                # Display the result
                if result["success"]:
                    print("\n" + "=" * 80)
                    print(result["response"])
                    print("=" * 80)
                else:
                    print("\n" + "=" * 80)
                    print("ERROR:")
                    print(result["response"])
                    print("=" * 80)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error in interactive mode: {str(e)}")
        print(f"Error: {str(e)}")

async def process_single_query(query: str, db_path: Path, model: str, strict_mode: bool, output_json: bool):
    """
    Process a single query and exit.
    
    Args:
        query: The query to process
        db_path: Path to the database file
        model: Model to use for the agents
        strict_mode: Whether to use strict mode for guardrails
        output_json: Whether to output the result as JSON
    """
    try:
        # Initialize the orchestrator
        orchestrator = Orchestrator(
            db_path=db_path,
            model=model,
            strict_mode=strict_mode,
            schema_cache_path=Path("data/schema_cache.json")
        )
        
        # Process the query
        result = await orchestrator.process_query(query)
        
        # Output the result
        if output_json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(result["response"])
            else:
                print("ERROR: " + result["response"])
                
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        if output_json:
            print(json.dumps({"success": False, "error": str(e)}))
        else:
            print(f"Error: {str(e)}")

def main():
    """Parse arguments and run the CLI."""
    parser = argparse.ArgumentParser(description="SMITE 2 Combat Log Agent CLI")
    
    parser.add_argument(
        "--db", 
        type=str, 
        default="data/CombatLogExample.db",
        help="Path to the SQLite database file (default: data/CombatLogExample.db)"
    )
    
    parser.add_argument(
        "--model", 
        type=str, 
        default="gpt-4o",
        help="OpenAI model to use (default: gpt-4o)"
    )
    
    parser.add_argument(
        "--strict", 
        action="store_true",
        help="Enable strict mode for guardrails and error messages"
    )
    
    parser.add_argument(
        "--json", 
        action="store_true",
        help="Output results as JSON"
    )
    
    parser.add_argument(
        "query", 
        nargs="?", 
        help="Query to process (omit for interactive mode)"
    )
    
    args = parser.parse_args()
    
    # Convert db path to Path object
    db_path = Path(args.db)
    
    # Check if database file exists
    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        sys.exit(1)
    
    # Run in appropriate mode
    if args.query:
        # Single query mode
        asyncio.run(process_single_query(
            query=args.query,
            db_path=db_path,
            model=args.model,
            strict_mode=args.strict,
            output_json=args.json
        ))
    else:
        # Interactive mode
        asyncio.run(interactive_mode(
            db_path=db_path,
            model=args.model,
            strict_mode=args.strict
        ))

if __name__ == "__main__":
    main() 