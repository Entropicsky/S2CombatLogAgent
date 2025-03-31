#!/usr/bin/env python3
"""
Simple test of the SMITE 2 Combat Log Agent with handoffs using the OpenAI Agents SDK.
"""

import os
import sys
import asyncio
import sqlite3
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment")
print(f"API key found: {api_key[:5]}...{api_key[-5:]}")

# Set OpenAI API key for the Agents SDK
os.environ["OPENAI_API_KEY"] = api_key

# Import agents
from agents import Agent, Runner, ModelSettings
from agents.tool import function_tool

# Database path
DB_PATH = "data/CombatLogExample.db"

# Query cache
query_cache = {}
tables_cache = None
schema_cache = {}

def get_read_only_connection():
    """Create a read-only connection to the database."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    return conn

# Define a database query tool that uses the actual database
@function_tool
def query_database(query: str) -> str:
    """Execute a read-only SQL query on the combat log database.
    
    Args:
        query: The SQL query to execute. Must be read-only (SELECT only).
    """
    print(f"Tool called: query_database with query: {query}")
    
    # Check cache first
    if query in query_cache:
        print("Cache hit! Using cached result.")
        return query_cache[query]
    
    # Validate query is SELECT only
    if not query.strip().lower().startswith("select"):
        return "Error: Only SELECT queries are allowed for security reasons."
    
    try:
        # Connect to the actual database
        conn = get_read_only_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            result = "Query returned no results."
        else:
            # Convert dataframe to markdown table format
            result = f"Query results:\n{df.to_markdown(index=False)}"
        
        # Cache the result
        query_cache[query] = result
        return result
    except Exception as e:
        return f"Error executing query: {str(e)}"

@function_tool
def list_tables() -> str:
    """List all tables in the database."""
    print("Tool called: list_tables")
    
    # Check cache
    global tables_cache
    if tables_cache is not None:
        print("Cache hit! Using cached tables list.")
        return tables_cache
    
    try:
        conn = get_read_only_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if not tables:
            conn.close()
            return "No tables found in the database."
        
        result = "Tables in database:\n"
        for i, table in enumerate(tables):
            result += f"{i+1}. {table[0]}\n"
        
        conn.close()
        
        # Cache the result
        tables_cache = result
        return result
    except Exception as e:
        return f"Error listing tables: {str(e)}"

@function_tool
def get_table_schema(table_name: str) -> str:
    """Get the schema for a specific table in the database.
    
    Args:
        table_name: The name of the table to get schema information for.
    """
    print(f"Tool called: get_table_schema for table: {table_name}")
    
    # Check cache
    if table_name in schema_cache:
        print(f"Cache hit! Using cached schema for {table_name}.")
        return schema_cache[table_name]
    
    try:
        conn = get_read_only_connection()
        cursor = conn.cursor()
        
        # Get column info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        if not columns:
            conn.close()
            return f"Table '{table_name}' not found."
        
        # Format the results
        result = f"Schema for table '{table_name}':\n"
        result += "Column Name | Type | Not Null | Default Value | Primary Key\n"
        result += "-" * 70 + "\n"
        
        for col in columns:
            col_id, name, dtype, not_null, default_val, primary_key = col
            result += f"{name} | {dtype} | {not_null} | {default_val} | {primary_key}\n"
        
        # Get sample data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
        sample = cursor.fetchall()
        
        if sample:
            result += f"\nSample data (3 rows):\n"
            # Get column names
            col_names = [col[1] for col in columns]
            result += " | ".join(col_names) + "\n"
            result += "-" * 70 + "\n"
            
            for row in sample:
                result += " | ".join(str(val) for val in row) + "\n"
        
        conn.close()
        
        # Cache the result
        schema_cache[table_name] = result
        return result
    except Exception as e:
        return f"Error getting schema: {str(e)}"

async def main():
    """Run a simple test of SMITE 2 Combat Log Agent with handoffs."""
    # Create model settings
    model_settings = ModelSettings(
        temperature=0.3,
        max_tokens=1500
    )
    
    # Create specialist agents
    combat_specialist = Agent(
        name="CombatDataSpecialist",
        handoff_description="Specialist for analyzing combat events, damage, kills, and general combat statistics",
        instructions="""You are a SMITE 2 combat data specialist who analyzes combat logs to provide insights about damage, kills, deaths, and other combat events.
        
        When analyzing combat data:
        1. Use the query_database tool to get data about damage, kills, and combat events
        2. Provide detailed analysis of the combat performance of players
        3. Look for patterns in combat behavior and effectiveness
        
        Be concise but informative in your analysis.""",
        model="gpt-4o",
        model_settings=model_settings,
        tools=[query_database, list_tables, get_table_schema]
    )
    
    player_specialist = Agent(
        name="PlayerSpecialist",
        handoff_description="Specialist for analyzing individual player performance, builds, and playstyles",
        instructions="""You are a SMITE 2 player specialist who analyzes individual player performance and playstyles.
        
        When analyzing player data:
        1. Use the query_database tool to get data about players, their items, and performance
        2. Analyze build choices and their effectiveness
        3. Evaluate overall player strategy
        
        Be concise but informative in your analysis.""",
        model="gpt-4o",
        model_settings=model_settings,
        tools=[query_database, list_tables, get_table_schema]
    )
    
    # Create the orchestrator agent
    orchestrator_agent = Agent(
        name="OrchestratorAgent",
        instructions="""You are a SMITE 2 combat log analysis assistant that helps users understand their match data.
        
        Your role is to:
        1. Understand the user's question about SMITE 2 match data
        2. Determine which specialist can best answer the question
        3. Hand off to the appropriate specialist
        
        For combat-related questions (damage, kills, combat events):
        - Hand off to the CombatDataSpecialist
        
        For player-focused questions (individual performance, builds):
        - Hand off to the PlayerSpecialist
        
        For general questions that don't clearly fit a specialist:
        - Answer directly using the query_database tool
        
        Always be helpful and informative.""",
        model="gpt-4o",
        model_settings=model_settings,
        tools=[query_database, list_tables, get_table_schema],
        handoffs=[combat_specialist, player_specialist]
    )
    
    # First, let's see what tables are available in the database
    print("\n=== Listing available tables ===")
    tables_result = await Runner.run(orchestrator_agent, "What tables are available in the database?")
    print(f"Response: {tables_result.final_output}")
    
    # Queries to test
    queries = [
        "Who dealt the most damage in the match?",
        "What items did players build during the match?",
        "Tell me about the gold distribution among players."
    ]
    
    # Run each query through the orchestrator agent
    for i, query in enumerate(queries):
        print(f"\n=== Query {i+1}: {query} ===")
        result = await Runner.run(orchestrator_agent, query)
        print(f"Response: {result.final_output}")
        
        # Print handoffs if any occurred
        if hasattr(result, 'handoffs') and result.handoffs:
            print("Handoffs:", [h.name for h in result.handoffs])
    
    # Demonstrate caching by repeating the last query
    print("\n=== Cache Test: Repeating the last query ===")
    last_query = queries[-1]
    print(f"Repeating query: '{last_query}'")
    result = await Runner.run(orchestrator_agent, last_query)
    print(f"Response: {result.final_output}")

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    asyncio.run(main())
    print("\nDone") 