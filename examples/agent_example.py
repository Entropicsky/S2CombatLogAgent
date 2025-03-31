#!/usr/bin/env python3
"""
SMITE 2 Combat Log Agent example using the OpenAI Agents SDK.
"""

import os
import sys
import asyncio
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set OpenAI API key for the Agents SDK
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment")
os.environ["OPENAI_API_KEY"] = api_key

# Import agents
from agents import Agent, Runner, ModelSettings
from agents.tool import function_tool

# Define database connection
DB_PATH = "data/CombatLogExample.db"

def get_read_only_connection():
    """Create a read-only connection to the database."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    return conn

# Tool definitions
@function_tool
def run_sql_query(query: str) -> str:
    """Execute a read-only SQL query on the combat log database.
    
    Args:
        query: The SQL query to execute. Must be read-only (SELECT only).
    """
    print(f"Tool called: run_sql_query with query: {query}")
    
    # Validate query is SELECT only
    if not query.strip().lower().startswith("select"):
        return "Error: Only SELECT queries are allowed for security reasons."
    
    try:
        conn = get_read_only_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return "Query returned no results."
        
        # Convert dataframe to string representation for output
        return f"Query results:\n{df.to_string()}"
    except Exception as e:
        return f"Error executing query: {str(e)}"

@function_tool
def get_table_schema(table_name: str) -> str:
    """Get the schema for a specific table in the database.
    
    Args:
        table_name: The name of the table to get schema information for.
    """
    print(f"Tool called: get_table_schema for table: {table_name}")
    
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
        return result
    except Exception as e:
        return f"Error getting schema: {str(e)}"

@function_tool
def list_tables() -> str:
    """List all tables in the database."""
    print("Tool called: list_tables")
    
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
        return result
    except Exception as e:
        return f"Error listing tables: {str(e)}"

@function_tool
def create_chart(query: str, chart_type: str, x_column: str, y_column: str, title: str) -> str:
    """Create a chart from SQL query results.
    
    Args:
        query: SQL query to get data for the chart
        chart_type: Type of chart (bar, line, pie, scatter)
        x_column: Column to use for x-axis
        y_column: Column to use for y-axis
        title: Chart title
    """
    print(f"Tool called: create_chart with type: {chart_type}")
    
    # Validate query
    if not query.strip().lower().startswith("select"):
        return "Error: Only SELECT queries are allowed for security reasons."
    
    try:
        # Get data
        conn = get_read_only_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            return "Query returned no results, cannot create chart."
        
        if x_column not in df.columns or y_column not in df.columns:
            return f"Error: Columns {x_column} and/or {y_column} not found in query results."
        
        # Create chart
        plt.figure(figsize=(10, 6))
        
        if chart_type.lower() == "bar":
            df.plot(kind="bar", x=x_column, y=y_column, title=title)
        elif chart_type.lower() == "line":
            df.plot(kind="line", x=x_column, y=y_column, title=title)
        elif chart_type.lower() == "pie":
            df.plot(kind="pie", y=y_column, title=title)
        elif chart_type.lower() == "scatter":
            df.plot(kind="scatter", x=x_column, y=y_column, title=title)
        else:
            return f"Unsupported chart type: {chart_type}. Please use bar, line, pie, or scatter."
        
        # Save chart
        chart_path = "temp_chart.png"
        plt.savefig(chart_path)
        plt.close()
        
        return f"Chart created and saved to {chart_path}"
    except Exception as e:
        return f"Error creating chart: {str(e)}"

async def main():
    """Run the SMITE 2 Combat Log Agent example."""
    # Create model settings
    model_settings = ModelSettings(
        temperature=0.2,
        max_tokens=4096
    )
    
    # Create specialist agents
    combat_specialist = Agent(
        name="CombatDataSpecialist",
        handoff_description="Specialist for analyzing combat events, damage, kills, and general combat statistics",
        instructions="""You are a SMITE 2 combat data specialist who analyzes combat logs to provide insights about damage, kills, deaths, and other combat events.
        
        When analyzing combat data:
        1. Use specific SQL queries to extract relevant combat information
        2. Provide detailed breakdowns of damage types, sources, and targets
        3. Look for patterns in combat behavior and effectiveness
        4. Create visualizations when appropriate to illustrate your findings
        
        Use the provided tools to query the database and create visualizations.""",
        model="gpt-4o",
        model_settings=model_settings,
        tools=[run_sql_query, get_table_schema, list_tables, create_chart]
    )
    
    timeline_specialist = Agent(
        name="TimelineSpecialist",
        handoff_description="Specialist for chronological analysis, match progression, and phase-based insights",
        instructions="""You are a SMITE 2 timeline specialist who analyzes the chronological progression of matches.
        
        When analyzing timeline data:
        1. Focus on how matches evolve over time
        2. Identify key moments and turning points
        3. Analyze different phases of the game (early, mid, late)
        4. Track objective timing and its impact
        
        Use the provided tools to query the database and create visualizations.""",
        model="gpt-4o",
        model_settings=model_settings,
        tools=[run_sql_query, get_table_schema, list_tables, create_chart]
    )
    
    player_specialist = Agent(
        name="PlayerSpecialist",
        handoff_description="Specialist for analyzing individual player performance, builds, and playstyles",
        instructions="""You are a SMITE 2 player specialist who analyzes individual player performance and playstyles.
        
        When analyzing player data:
        1. Focus on individual performance metrics
        2. Analyze build choices and their effectiveness
        3. Evaluate positioning and map presence
        4. Compare performance to team averages
        
        Use the provided tools to query the database and create visualizations.""",
        model="gpt-4o",
        model_settings=model_settings,
        tools=[run_sql_query, get_table_schema, list_tables, create_chart]
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
        
        For timeline/chronological questions (match progression, phases, timing):
        - Hand off to the TimelineSpecialist
        
        For player-focused questions (individual performance, builds):
        - Hand off to the PlayerSpecialist
        
        For general questions that don't clearly fit a specialist:
        - Answer directly using the database tools
        
        Always be helpful and informative.""",
        model="gpt-4o",
        model_settings=model_settings,
        tools=[list_tables, get_table_schema],
        handoffs=[combat_specialist, timeline_specialist, player_specialist]
    )
    
    # Queries to test
    queries = [
        "What tables are available in the database?",
        "Who dealt the most damage in the match?",
        "How did player gold progress throughout the match?",
        "What items did the top player build?"
    ]
    
    # Run each query through the orchestrator agent
    for i, query in enumerate(queries):
        print(f"\n=== Query {i+1}: {query} ===")
        result = await Runner.run(orchestrator_agent, query)
        print(f"Response: {result.final_output}")
        
        # Print handoffs if any
        if hasattr(result, 'handoffs') and result.handoffs:
            print("Handoffs:", [h.name for h in result.handoffs])

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    asyncio.run(main())
    print("\nDone") 