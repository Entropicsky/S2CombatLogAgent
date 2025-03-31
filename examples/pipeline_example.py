#!/usr/bin/env python3
"""
Example demonstrating the SMITE 2 Combat Log Agent's multi-agent pipeline architecture.

This example creates a simple two-agent pipeline with an analyzer agent
and a formatter agent to process a query about combat data using the actual database.
Includes a data fidelity guardrail to ensure output matches database values.
"""

import asyncio
import os
import sys
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from agents.tool import function_tool
from agents import (
    Agent,
    GuardrailFunctionOutput,
    OutputGuardrailTripwireTriggered,
    RunContextWrapper,
    output_guardrail
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("pipeline_example")

# Add parent directory to path for importing smite2_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smite2_agent.pipeline import (
    BaseAgent,
    OAIBaseAgent,
    PipelineAgent,
    Pipeline,
    create_agent,
    create_pipeline,
)
from smite2_agent.tools.sql_tools import run_sql_query

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment")

# Set OpenAI API key for the Agents SDK
os.environ["OPENAI_API_KEY"] = api_key

# Path to the example database
DB_PATH = Path("data/CombatLogExample.db")

# Store DB query results for guardrail validation
db_query_results = {
    "players": {},
    "abilities": {},
    "damage_values": {},
    "discrepancies": []
}

class CombatAnalysisOutput(BaseModel):
    """Output schema for the combat analyzer agent."""
    response: str

# Define SQL query tool for agents
@function_tool
async def query_database(query: str) -> Dict[str, Any]:
    """
    Execute a SQL query on the SMITE 2 combat log database.
    
    Args:
        query: SQL SELECT query to run
        
    Returns:
        Dictionary with query results including:
        - success: Whether the query was successful
        - data: The query results as a list of dictionaries or a formatted table
        - row_count: Number of rows returned
        - query: The original query
    """
    global db_query_results
    
    logger.info(f"Executing SQL query: {query}")
    result = run_sql_query(query, DB_PATH, format_as="dict")  # Use dictionary format for better processing
    
    if result["success"]:
        logger.info(f"Query successful: {result['row_count']} rows returned")
        logger.info(f"Query result preview: {str(result['data'])[:500]}...")
        
        # Store query results for guardrail validation
        try:
            # Parse and store query results based on content
            if isinstance(result["data"], list) and len(result["data"]) > 0:
                # Store player information
                if "player" in result["data"][0]:
                    for row in result["data"]:
                        if "player" in row and "total_damage" in row:
                            db_query_results["players"][row["player"]] = row["total_damage"]
                            logger.info(f"Stored player damage: {row['player']} = {row['total_damage']}")
                
                # Store ability information
                if "ability_name" in result["data"][0]:
                    for row in result["data"]:
                        if "ability_name" in row and "total_damage" in row:
                            db_query_results["abilities"][row["ability_name"]] = row["total_damage"]
                            logger.info(f"Stored ability damage: {row['ability_name']} = {row['total_damage']}")
        except Exception as e:
            logger.error(f"Error storing query results: {str(e)}")
    else:
        logger.error(f"Query failed: {result.get('error', 'Unknown error')}")
    
    return result

# Data fidelity guardrail to ensure output matches database values
@output_guardrail
async def data_fidelity_guardrail(ctx: RunContextWrapper, agent: Agent, output: CombatAnalysisOutput) -> GuardrailFunctionOutput:
    """
    Validate that the agent's output contains factual data that matches the database queries.
    
    Checks for:
    1. Player names mentioned match those in the database
    2. Damage values are accurate (no made-up numbers)
    3. Ability names are accurate
    """
    global db_query_results
    logger.info("Running data fidelity guardrail check")
    
    response = output.response
    discrepancies = []
    
    # Check for player name accuracy
    for player_name, damage in db_query_results["players"].items():
        # If the player is mentioned in the database, it should be in the response
        if player_name in db_query_results["players"]:
            if player_name not in response:
                discrepancies.append(f"Player '{player_name}' from database not found in response")
            
            # Check if any made-up player names are in the response
            made_up_names = ["Zephyr", "Ares", "Apollo"]
            for name in made_up_names:
                if name in response and name not in db_query_results["players"]:
                    discrepancies.append(f"Made-up player name '{name}' found in response")
    
    # Check for damage value accuracy (rough check for fabricated values)
    # Look for specific patterns like "Total Damage: 35,000" or "35000 damage"
    damage_patterns = [
        r"Total Damage:?\s+(\d{1,3}(?:,\d{3})*|\d+)",
        r"(\d{1,3}(?:,\d{3})*|\d+)\s+damage",
        r"damage of\s+(\d{1,3}(?:,\d{3})*|\d+)"
    ]
    
    for pattern in damage_patterns:
        matches = re.finditer(pattern, response, re.IGNORECASE)
        for match in matches:
            damage_str = match.group(1).replace(",", "")
            try:
                damage_value = int(damage_str)
                
                # Check if this is a made-up value
                real_values = list(db_query_results["players"].values()) + list(db_query_results["abilities"].values())
                
                # Allow for some approximation in reporting (within 5%)
                is_real = any(abs(damage_value - real_value) / real_value < 0.05 for real_value in real_values if real_value > 0)
                
                if not is_real:
                    discrepancies.append(f"Made-up damage value '{damage_value}' found in response")
            except ValueError:
                pass
    
    # Check ability names
    for ability_name in db_query_results["abilities"]:
        if ability_name in db_query_results["abilities"] and ability_name not in response:
            # Only flag this if it's one of the top abilities
            sorted_abilities = sorted(db_query_results["abilities"].items(), key=lambda x: x[1], reverse=True)
            top_3_abilities = [name for name, _ in sorted_abilities[:3]]
            if ability_name in top_3_abilities:
                discrepancies.append(f"Top ability '{ability_name}' from database not found in response")
    
    # Store discrepancies in the global db_query_results dict so we can access them elsewhere
    db_query_results["discrepancies"] = discrepancies
    
    logger.info(f"Guardrail check completed. Found {len(discrepancies)} discrepancies.")
    for discrepancy in discrepancies:
        logger.info(f"Discrepancy: {discrepancy}")
    
    return GuardrailFunctionOutput(
        output_info={"discrepancies": discrepancies},
        tripwire_triggered=len(discrepancies) > 0
    )

# Define a comprehensive analyzer agent with database access
analyzer_instructions = """
You are a SMITE 2 combat data analyzer AND formatter. Your role is to analyze queries about
combat data using the actual database and provide well-formatted, factually accurate responses.

CRITICAL INSTRUCTION: You MUST follow these steps for every query:
1. FIRST, use the query_database tool to retrieve data from the database
2. Look at the actual data returned in the 'data' field of the response
3. Base your ENTIRE response only on the actual database results
4. Use the exact values, names, and numbers from the query results
5. Do not fabricate or hallucinate any information not present in the results

NEVER substitute actual player names or values with fictional ones. 
For example, if the results show player 'MateoUwU' with damage of 114622, you MUST use those
exact names and values in your response, not any other names or rounded numbers.

You have access to a SQLite database containing SMITE 2 combat log data.
Key tables in the database include:

1. players:
   - player_id (INTEGER, PRIMARY KEY)
   - match_id (VARCHAR, FOREIGN KEY to matches.match_id)
   - player_name (VARCHAR)
   - team_id (INTEGER)
   - role (VARCHAR)
   - god_id (INTEGER)
   - god_name (VARCHAR)

2. combat_events:
   - event_id (INTEGER, PRIMARY KEY)
   - match_id (VARCHAR, FOREIGN KEY to matches.match_id)
   - event_time (DATETIME)
   - timestamp (DATETIME)
   - event_type (VARCHAR) - Types include "Damage", "Healing", "CrowdControl", etc.
   - source_entity (VARCHAR) - The entity causing the event (usually player_name)
   - target_entity (VARCHAR) - The entity receiving the event
   - ability_name (VARCHAR)
   - location_x (FLOAT)
   - location_y (FLOAT)
   - damage_amount (INTEGER)
   - damage_mitigated (INTEGER)
   - event_text (TEXT)

3. matches:
   - Contains match metadata (match_id is the primary key)

4. abilities:
   - Contains ability information

5. item_events:
   - Contains information about item purchases

6. timeline_events:
   - Contains chronological match events

Example Queries:
- To find the player who dealt the most damage:
  ```sql
  SELECT source_entity as player, SUM(damage_amount) as total_damage
  FROM combat_events
  WHERE event_type = 'Damage'
  GROUP BY source_entity
  ORDER BY total_damage DESC
  LIMIT 1;
  ```

- To see what types of damage a player used:
  ```sql
  SELECT ability_name, COUNT(*) as times_used, SUM(damage_amount) as total_damage
  FROM combat_events
  WHERE event_type = 'Damage' AND source_entity = 'PlayerName'
  GROUP BY ability_name
  ORDER BY total_damage DESC;
  ```

Use the query_database tool to run SQL queries against this database.
Always ensure your SQL queries use the correct column names as shown above.
Remember to use only valid SQL queries.

Your response should be:
1. Well-formatted with markdown
2. Start with a clear, direct answer to the original question
3. Include key insights as a bulleted list
4. Include suggested visualizations if relevant
5. Professional and easy to scan
6. 100% factually accurate using the EXACT data from the database
"""

async def main():
    """Run the example."""
    print("Creating analyzer agent...")
    
    # Create a single comprehensive analyzer agent directly with the Agent class
    from agents import Agent, ModelSettings, Runner
    
    model_settings = ModelSettings(
        temperature=0.1  # Lower temperature for more precise responses
    )
    
    analyzer = Agent(
        name="CombatDataAnalyzer",
        instructions=analyzer_instructions,
        tools=[query_database],
        output_guardrails=[data_fidelity_guardrail],
        output_type=CombatAnalysisOutput,
        model="gpt-4o",
        model_settings=model_settings
    )
    
    runner = Runner()
    
    # Example query
    query = "Who dealt the most damage in the match and what types of damage did they use?"
    
    print(f"\nProcessing query: '{query}'")
    print("=" * 80)
    
    try:
        # Process the query using Runner
        response = await runner.run(analyzer, query)
        
        # Print the result
        print("\nFinal response:")
        print("-" * 80)
        print(response.final_output.response)
        print("-" * 80)
        
        print("Guardrail passed - response contains accurate database information.")
        
        # Now let's test the guardrail with a deliberately incorrect response
        print("\nTesting guardrail with a deliberately incorrect response...")
        
        # Create a testing agent with hardcoded incorrect response
        fake_response_instructions = """
        You are a testing agent. Your purpose is to return a specific response for testing.
        
        When asked any question, you MUST respond with exactly the following text, preserving all formatting:
        
        ### Top Damage Dealer
        
        **Player:** Zephyr
        **Total Damage Dealt:** 35,000
        
        ### Types of Damage Used
        
        Zephyr utilized a variety of abilities to deal damage:
        
        - **Wind Blast**
          - **Times Used:** 120
          - **Total Damage:** 20,000
        - **Arcane Surge**
          - **Times Used:** 45
          - **Total Damage:** 10,000
        - **Tornado**
          - **Times Used:** 30
          - **Total Damage:** 5,000
          
        ### Insights
        - **Wind Blast** was the most frequently used and highest damage-dealing ability.
        - **Arcane Surge** and **Tornado** also contributed significantly to the total damage.
        
        ### Suggested Visualizations
        - **Bar Chart** showing total damage per ability.
        - **Pie Chart** illustrating the proportion of total damage contributed by each ability.
        """
        
        fake_agent = Agent(
            name="FakeDataAgent",
            instructions=fake_response_instructions,
            output_guardrails=[data_fidelity_guardrail],
            output_type=CombatAnalysisOutput,
            model="gpt-4o",
            model_settings=model_settings
        )
        
        try:
            # This should trigger the guardrail
            fake_response = await runner.run(fake_agent, query)
            print("\nERROR: Guardrail failed to detect fake response!")
        except OutputGuardrailTripwireTriggered as e:
            print("\nGuardrail triggered for fake response! Discrepancies detected:")
            print("-" * 80)
            # Log all discrepancies that were detected by the guardrail check
            for discrepancy in db_query_results["discrepancies"]:
                print(f"- {discrepancy}")
            print("-" * 80)
            print("Success: The guardrail correctly rejected the response with fake data.")
            
    except OutputGuardrailTripwireTriggered as e:
        print("\nGuardrail triggered! Response contained inaccurate information:")
        print("-" * 80)
        # Log all discrepancies that were detected by the guardrail check
        for discrepancy in db_query_results["discrepancies"]:
            print(f"- {discrepancy}")
        print("-" * 80)
        print("Agent response was rejected due to data inaccuracies.")

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    print(f"Using database: {DB_PATH.absolute()}")
    if not DB_PATH.exists():
        print(f"Warning: Database file {DB_PATH} does not exist!")
    asyncio.run(main())
    print("\nDone") 