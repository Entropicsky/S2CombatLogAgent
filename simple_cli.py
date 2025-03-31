#!/usr/bin/env python3
"""
Simple CLI for the SMITE 2 Combat Log Agent.

This script provides a command-line interface that uses the current
agent architecture with the pipeline of:
1. QueryAnalystAgent
2. DataEngineerAgent
3. DataAnalystAgent
4. ResponseComposerAgent
5. FollowUpPredictorAgent

Output formats supported:
- text: Plain text response (default)
- json: Simple JSON with just the answer and followups
- debug_json: Detailed JSON with query debug information (SQL, results, etc.)
"""

import os
import asyncio
import logging
import json
from pathlib import Path
import argparse
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import agents
from smite2_agent.pipeline.base.data_package import DataPackage
from smite2_agent.agents.query_analyst import QueryAnalystAgent
from smite2_agent.agents.data_engineer import DataEngineerAgent
from smite2_agent.agents.data_analyst import DataAnalystAgent
from smite2_agent.agents.response_composer import ResponseComposerAgent
from smite2_agent.agents.followup_predictor import FollowUpPredictorAgent

async def process_query(db_path: Path, query: str, model: str = "gpt-4o", include_followups: bool = True) -> DataPackage:
    """
    Process a query using the full agent pipeline.
    
    Args:
        db_path: Path to the database
        query: Query to process
        model: Model to use
        include_followups: Whether to include follow-up predictions
        
    Returns:
        Complete DataPackage with results
    """
    logger.info(f"Processing query: {query}")
    
    # Create the agents
    query_analyst = QueryAnalystAgent(
        db_path=str(db_path),
        model=model,
        temperature=0.2
    )
    
    data_engineer = DataEngineerAgent(
        db_path=db_path,
        model=model,
        temperature=0.2
    )
    
    data_analyst = DataAnalystAgent(
        model=model,
        temperature=0.2
    )
    
    response_composer = ResponseComposerAgent(
        model=model,
        temperature=0.2
    )
    
    followup_predictor = None
    if include_followups:
        followup_predictor = FollowUpPredictorAgent(
            model=model,
            temperature=0.3,
            db_path=db_path
        )
    
    # Create a new data package
    data_package = DataPackage(query=query)
    if db_path:
        data_package.set_db_path(str(db_path))
    
    # Process query analysis
    logger.info("Query Analysis...")
    data_package = await query_analyst._process(data_package)
    
    # Process data engineering
    logger.info("Data Engineering...")
    data_package = await data_engineer.process_question(data_package)
    
    # Process data analysis
    logger.info("Data Analysis...")
    data_package = await data_analyst.process_data(data_package)
    
    # Process response composition
    logger.info("Response Composition...")
    data_package = await response_composer.generate_response(data_package)
    
    # Process follow-up prediction if enabled
    if include_followups and followup_predictor:
        logger.info("Follow-up Prediction...")
        data_package = await followup_predictor._process(data_package)
    
    return data_package

def format_output(data_package: DataPackage, output_format: str = "text") -> str:
    """
    Format the data package output according to the specified format.
    
    Args:
        data_package: The data package to format
        output_format: Output format ('text', 'json', or 'debug_json')
        
    Returns:
        Formatted output string
    """
    # Extract the response
    response = data_package.get_response()
    if not response:
        response = "I was unable to process your query. Please try again."
    
    # Return formatted output based on format
    if output_format == "text":
        return response
    
    elif output_format == "json":
        # Simple JSON with just the answer and followups
        package_dict = data_package.to_dict()
        simple_json = {
            "answer": response,
            "suggested_followups": package_dict.get("enhancement", {}).get("suggested_questions", [])
        }
        return json.dumps(simple_json, indent=2)
    
    elif output_format == "debug_json":
        # Detailed JSON with query debug information
        return data_package.to_debug_json()
    
    else:
        # Default to text if invalid format
        return response

async def interactive_mode(db_path: Path, model: str = "gpt-4o", include_followups: bool = True, output_format: str = "text"):
    """
    Run the CLI in interactive mode.
    
    Args:
        db_path: Path to the database
        model: Model to use
        include_followups: Whether to include follow-up predictions
        output_format: Output format ('text', 'json', or 'debug_json')
    """
    print("\n" + "="*50)
    print("SMITE 2 Combat Log Agent - Interactive Mode")
    print(f"Output Format: {output_format}")
    print("Enter 'exit' or 'quit' to exit")
    print("="*50 + "\n")
    
    while True:
        # Get user input
        query = input("\nEnter your query: ")
        
        # Check for exit command
        if query.lower() in ["exit", "quit"]:
            print("Exiting interactive mode...")
            break
        
        # Process the query
        try:
            print("\nProcessing your query...")
            data_package = await process_query(db_path, query, model, include_followups)
            
            # Format and print the response
            formatted_output = format_output(data_package, output_format)
            
            print("\n" + "="*50)
            print("RESPONSE:")
            print("="*50)
            print(formatted_output)
            print("="*50)
            
        except Exception as e:
            print(f"\nError processing query: {str(e)}")

async def main():
    """Run the CLI."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="SMITE 2 Combat Log Agent CLI")
    parser.add_argument("query", nargs="?", help="Query to process (if not specified, run in interactive mode)")
    parser.add_argument("--db", dest="db_path", default="data/CombatLogExample.db", help="Path to the database file")
    parser.add_argument("--model", dest="model", default="gpt-4o", help="Model to use")
    parser.add_argument("--no-followups", dest="no_followups", action="store_true", help="Disable follow-up predictions")
    parser.add_argument("--output", dest="output_format", choices=["text", "json", "debug_json"], default="text", 
                       help="Output format (text, json, or debug_json)")
    args = parser.parse_args()
    
    # Convert db_path to Path
    db_path = Path(args.db_path)
    
    # Check if the database file exists
    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        return
    
    # Run in interactive mode if no query is specified
    if not args.query:
        await interactive_mode(db_path, args.model, not args.no_followups, args.output_format)
    else:
        # Process the query
        data_package = await process_query(db_path, args.query, args.model, not args.no_followups)
        
        # Format and print the response
        formatted_output = format_output(data_package, args.output_format)
        print(formatted_output)

if __name__ == "__main__":
    asyncio.run(main()) 