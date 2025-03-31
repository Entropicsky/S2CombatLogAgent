#!/usr/bin/env python3
"""
SMITE 2 Combat Log Analyzer
Command-line interface for testing and development.
"""

import os
import sys
import argparse
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from smite2_agent.config.settings import get_settings
from smite2_agent.config.prompts import get_prompt_for_agent, format_schema_info
from smite2_agent.db.connection import get_connection
from smite2_agent.db.schema import get_schema_info
from smite2_agent.agents.openai_agent import OpenAIAgent
from smite2_agent.tools.sql_tools import run_sql_query
from smite2_agent.utils.tools import function_tool


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("smite2_agent")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="SMITE 2 Combat Log Analyzer")
    parser.add_argument("db_path", help="Path to the SQLite database file")
    parser.add_argument("--prompt", "-p", help="Prompt to send to the agent")
    parser.add_argument("--agent", "-a", default="orchestrator", help="Agent type to use")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument("--model", "-m", help="Model name to use")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug logging")
    return parser.parse_args()


@function_tool
def query_database(query: str) -> Dict[str, Any]:
    """
    Execute a SQL query on the SMITE 2 combat log database.
    
    Args:
        query: SQL SELECT query to run
        
    Returns:
        Dictionary with query results
    """
    # The db_path will be set globally
    return run_sql_query(query, db_path, format_as="markdown")


async def run_agent_once(agent, prompt):
    """Run the agent with a single prompt."""
    logger.info(f"Running agent with prompt: {prompt}")
    
    # Run the agent
    response = await agent.run(prompt)
    
    # Display the response
    print("\nAGENT RESPONSE:")
    print("=" * 80)
    print(response.get("content", "No response"))
    print("=" * 80)
    
    # Display tool usage
    tools_used = response.get("tools_used", [])
    if tools_used:
        print("\nTools used:")
        for tool in tools_used:
            print(f"- {tool}")
    
    return response


async def run_interactive(agent):
    """Run the agent in interactive mode."""
    print("SMITE 2 Combat Log Analyzer (Interactive Mode)")
    print("Type 'exit' or 'quit' to end the session.")
    print("=" * 80)
    
    while True:
        # Get user input
        try:
            prompt = input("\nYour question: ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break
        
        # Check for exit command
        if prompt.lower() in ("exit", "quit"):
            print("Exiting...")
            break
        
        # Run the agent
        await run_agent_once(agent, prompt)


async def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Set global variables
    global db_path
    db_path = args.db_path
    
    # Set up logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Update settings if needed
    settings = get_settings()
    if args.model:
        settings.model_name = args.model
    
    # Validate database path
    db_file = Path(db_path)
    if not db_file.exists():
        logger.error(f"Database file not found: {db_path}")
        sys.exit(1)
    
    try:
        # Connect to the database
        logger.info(f"Connecting to database: {db_path}")
        db_conn = get_connection(db_path)
        schema_info = get_schema_info(db_path)
        
        # Get database schema
        tables = schema_info.get_all_tables()
        logger.info(f"Found {len(tables)} tables in the database:")
        for table in tables:
            table_schema = schema_info.get_table_schema(table)
            row_count = len(schema_info.get_table_sample(table, 1))
            logger.info(f"- {table}: {len(table_schema)} columns, {row_count}+ rows")
        
        # Format schema info for agent prompt
        schema_description = schema_info.get_schema_description()
        
        # Get agent instructions
        agent_instructions = get_prompt_for_agent(args.agent)
        
        # Add schema info to agent instructions
        agent_instructions = agent_instructions.replace("{{SCHEMA_INFO}}", schema_description)
        
        # Create the agent
        logger.info(f"Creating agent: {args.agent}")
        
        # Define tools
        tools = [query_database]
        
        # Create the agent using the new OpenAI Agents SDK
        from agents import Agent, ModelSettings, Runner
        from agents.tools import function_tool
        
        # Register the function tool for query_database
        query_func_tool = function_tool(query_database)
        
        # Define model settings
        model_settings = ModelSettings(
            temperature=0.2,
            max_tokens=4096,
            top_p=0.95
        )
        
        # Create the agent using the Agents SDK
        agent_sdk = Agent(
            name=args.agent,
            description=f"SMITE 2 Combat Log {args.agent.capitalize()} Agent",
            instructions=agent_instructions,
            model=settings.model_name,
            model_settings=model_settings,
            tools=[query_func_tool]
        )
        
        # Create a runner for the agent
        runner = Runner()
        
        # Wrap the SDK agent in our OpenAIAgent class for compatibility
        agent = OpenAIAgent(
            name=args.agent,
            description=f"SMITE 2 Combat Log {args.agent.capitalize()} Agent",
            instructions=agent_instructions,
            model_name=settings.model_name,
            tools=[query_func_tool]
        )
        
        # Run the agent
        if args.interactive:
            await run_interactive(agent)
        elif args.prompt:
            await run_agent_once(agent, args.prompt)
        else:
            logger.error("No prompt provided. Use --prompt or --interactive")
            sys.exit(1)
        
    except Exception as e:
        logger.exception(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
