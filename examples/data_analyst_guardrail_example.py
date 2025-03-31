#!/usr/bin/env python3
"""
Example demonstrating the SMITE 2 Combat Log Agent's DataAnalystGuardrail.

This example retrieves real data from the database, creates a Data Analyst agent,
and tests the guardrail with both valid and invalid analytical claims.
"""

import asyncio
import os
import sys
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from agents.tool import function_tool
from agents import (
    Agent,
    GuardrailFunctionOutput,
    OutputGuardrailTripwireTriggered,
    RunContextWrapper,
    output_guardrail,
    ModelSettings
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("data_analyst_guardrail_example")

# Add parent directory to path for importing smite2_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smite2_agent.tools.sql_tools import run_sql_query
from smite2_agent.guardrails import DataAnalystGuardrail

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

# Store retrieved data for guardrail validation
analysis_data = {
    "entities": {},
    "values": [],
    "time_series": [],
    "before_after": [],
    "comparisons": [],
    "statistics": {}
}

# Create a simpler output model for our example
class SimpleAnalysisOutput(BaseModel):
    """Simple output model for our example"""
    response: str

    class Config:
        """Pydantic model configuration."""
        extra = "forbid"  # Forbid extra attributes

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
    global analysis_data
    
    logger.info(f"Executing SQL query: {query}")
    result = run_sql_query(query, DB_PATH, format_as="dict")
    
    if result["success"]:
        logger.info(f"Query successful: {result['row_count']} rows returned")
        
        try:
            # Store data for validation based on content
            if isinstance(result["data"], list) and len(result["data"]) > 0:
                # Store player entities
                if any("player" in row for row in result["data"]):
                    for row in result["data"]:
                        if "player" in row:
                            player_name = row["player"]
                            analysis_data["entities"][player_name] = row.get("player_id", "unknown_id")
                
                # Store numerical values
                for row in result["data"]:
                    for key, value in row.items():
                        if isinstance(value, (int, float)) and value > 0:
                            analysis_data["values"].append(value)
                
                # Handle time series data (if query has timestamp and value columns)
                if any("timestamp" in row and "value" in row for row in result["data"]):
                    # Group by entity if available
                    entity_series = {}
                    for row in result["data"]:
                        entity = row.get("entity", "unknown")
                        if entity not in entity_series:
                            entity_series[entity] = []
                        entity_series[entity].append(row["value"])
                    
                    # Add each entity's time series
                    for entity, values in entity_series.items():
                        analysis_data["time_series"].append({
                            "entity": entity,
                            "values": values
                        })
                
                # Store statistical information
                damage_values = [row.get("damage", 0) for row in result["data"] if "damage" in row]
                if damage_values:
                    analysis_data["statistics"]["avg_damage"] = sum(damage_values) / len(damage_values)
                    analysis_data["statistics"]["max_damage"] = max(damage_values)
                    analysis_data["statistics"]["min_damage"] = min(damage_values)
                    analysis_data["statistics"]["total_damage"] = sum(damage_values)
        
        except Exception as e:
            logger.error(f"Error storing query results: {str(e)}")
    else:
        logger.error(f"Query failed: {result.get('error', 'Unknown error')}")
    
    return result

@function_tool
async def record_comparison(first_value: float, second_value: float, description: str) -> Dict[str, Any]:
    """
    Record a comparison between two values for later validation.
    
    Args:
        first_value: The first value to compare
        second_value: The second value to compare
        description: Description of what's being compared
        
    Returns:
        Dictionary with the comparison details
    """
    global analysis_data
    
    comparison = {
        "first": first_value,
        "second": second_value,
        "description": description
    }
    
    # Calculate the percentage difference for reference
    if second_value != 0:
        percentage = ((first_value - second_value) / second_value) * 100
        comparison["percentage_diff"] = percentage
    
    analysis_data["comparisons"].append(comparison)
    logger.info(f"Recorded comparison: {description} - {first_value} vs {second_value}")
    
    return comparison

@function_tool
async def record_change_over_time(before_value: float, after_value: float, description: str) -> Dict[str, Any]:
    """
    Record a change in a value over time for later validation.
    
    Args:
        before_value: The value before the change
        after_value: The value after the change
        description: Description of what changed
        
    Returns:
        Dictionary with the change details
    """
    global analysis_data
    
    change = {
        "before": before_value,
        "after": after_value,
        "description": description
    }
    
    # Calculate the percentage change for reference
    if before_value != 0:
        percentage = ((after_value - before_value) / before_value) * 100
        change["percentage_change"] = percentage
    
    analysis_data["before_after"].append(change)
    logger.info(f"Recorded change: {description} - {before_value} to {after_value}")
    
    return change

# Data analyst instructions for the accurate agent
accurate_analyst_instructions = """
You are a SMITE 2 data analyst specializing in analyzing combat data. Your job is to analyze
data from the SMITE 2 database and provide accurate statistical insights and trends.

CRITICAL INSTRUCTION: You MUST follow these steps for every analysis:
1. FIRST, use the query_database tool to retrieve data from the database
2. Look at the actual data returned in the 'data' field of the response
3. Base your ENTIRE analysis only on the actual database results
4. Use the exact values, names, and numbers from the query results
5. When calculating averages, totals, or percentages, do the math precisely
6. Use the record_comparison and record_change_over_time tools to document any comparisons or changes you analyze

NEVER fabricate or hallucinate any information not present in the results.
If you're making a comparison or analyzing a trend, document it using the appropriate tool.

Your analysis should be:
1. Factually accurate with precise numbers
2. Based ONLY on the actual data queried
3. Clear and well-organized
4. Include specific player names from the data (never make up names)

Example Queries:
- To analyze player damage:
  ```sql
  SELECT source_entity as player, player_id, SUM(damage_amount) as damage
  FROM combat_events
  WHERE event_type = 'Damage'
  GROUP BY source_entity
  ORDER BY damage DESC;
  ```

- To analyze damage over time for trend analysis:
  ```sql
  SELECT 
    strftime('%M:%S', event_time) as timestamp,
    source_entity as entity,
    SUM(damage_amount) as value
  FROM combat_events
  WHERE event_type = 'Damage'
  GROUP BY timestamp, source_entity
  ORDER BY timestamp;
  ```

Your response should include:
1. A clear summary of the main findings
2. Precise statistical values (averages, totals, etc.)
3. Any notable trends or patterns
4. Key comparisons between players or abilities
"""

# Data analyst instructions that will produce inaccurate analysis
inaccurate_analyst_instructions = """
You are a SMITE 2 data analyst specializing in analyzing combat data. For this TEST EXAMPLE,
you are going to intentionally provide some inaccurate analysis.

When you get a query about combat data, do the following:
1. Use the query_database tool to retrieve the real data
2. Then, for your response, INTENTIONALLY make the following errors:
   - Invent a player named "Zephyr" who wasn't in the actual results
   - Exaggerate the damage numbers by approximately 25%
   - Claim an upward trend when there's a downward trend or vice versa
   - Report an incorrect average (make it higher than the actual average)

This is ONLY for testing the guardrail system, which is why we want you to
make these specific errors.

Also, use the record_comparison and record_change_over_time tools to document 
the CORRECT values (even though your text response will contain errors).

For this test, your analysis should:
1. Include at least one fabricated player name
2. Contain inflated damage numbers
3. Make incorrect claims about trends
4. Report inaccurate statistical calculations

This will allow us to verify our guardrail system is working correctly.
"""

async def run_example_with_agent(agent_name: str, instructions: str, should_pass: bool):
    """Run the example with a specific agent."""
    print(f"\nRunning example with {agent_name}...")
    print("=" * 80)
    
    # Reset the global analysis data
    global analysis_data
    analysis_data = {
        "entities": {},
        "values": [],
        "time_series": [],
        "before_after": [],
        "comparisons": [],
        "statistics": {}
    }
    
    # Create the data analyst agent
    model_settings = ModelSettings(
        temperature=0.2  # Lower temperature for more precise responses
    )
    
    data_analyst = Agent(
        name=agent_name,
        instructions=instructions,
        tools=[query_database, record_comparison, record_change_over_time],
        # Don't use the guardrail through the OpenAI Agents SDK
        output_type=SimpleAnalysisOutput,
        model="gpt-4o",
        model_settings=model_settings
    )
    
    # Create a runner
    from agents import Runner
    runner = Runner()
    
    # Example query
    query = "Analyze which player dealt the most damage and how their damage output changed over the course of the match. Include statistical analysis of average damage per player."
    
    print(f"\nProcessing query: '{query}'")
    print("-" * 80)
    
    try:
        # Process the query using Runner
        response = await runner.run(data_analyst, query)
        
        # Print the result
        print("\nFinal response:")
        print("-" * 80)
        print(response.final_output.response)
        print("-" * 80)
        
        # Create the guardrail and manually validate the response
        guardrail = DataAnalystGuardrail()
        
        # Create mock context with our analysis data
        class MockContext:
            def __init__(self, data):
                self.context = {"data": data}
        
        ctx = MockContext({
            "raw_data": {
                "entity": analysis_data["entities"]
            },
            "query_results": {
                "main_query": {
                    "data": [
                        {"player": player, "value": value} 
                        for player, value in analysis_data["entities"].items()
                    ]
                }
            }
        })
        
        # Prepare the output for validation
        output = SimpleAnalysisOutput(
            response=response.final_output.response
        )
        
        # Run the validation
        is_valid, discrepancies = await validate_analysis(
            text=response.final_output.response,
            entities=analysis_data["entities"],
            values=analysis_data["values"]
        )
        
        # Check if validation triggered the guardrail
        if not is_valid:
            print("\nGuardrail triggered! Response contained inaccurate analysis:")
            print("-" * 80)
            for discrepancy in discrepancies:
                print(f"- {discrepancy}")
            print("-" * 80)
            print(f"Guardrail {'correctly rejected' if not should_pass else 'incorrectly rejected'} the response.")
        else:
            print(f"Guardrail {'passed' if should_pass else 'failed to detect issues'} - response was accepted.")
        
        # Print the analysis data collected
        print("\nAnalysis data collected for validation:")
        print("-" * 80)
        print(f"Entities: {len(analysis_data['entities'])} players")
        print(f"Values: {len(analysis_data['values'])} numerical values")
        print(f"Time series: {len(analysis_data['time_series'])} series")
        print(f"Comparisons: {len(analysis_data['comparisons'])} comparisons")
        print(f"Before/After changes: {len(analysis_data['before_after'])} changes")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        if hasattr(e, 'error_info'):
            print(f"Error info: {e.error_info}")

# Create a function to validate analysis without using the decorator
async def validate_analysis(text: str, entities: Dict[str, Any], values: List[float]):
    """
    Validate an analysis against known data without using the OutputGuardrail decorator.
    
    Args:
        text: The text to validate
        entities: Dictionary of known entities
        values: List of known numerical values
        
    Returns:
        Tuple of (is_valid, discrepancies)
    """
    discrepancies = []
    
    # Create a new guardrail instance directly
    guardrail = DataAnalystGuardrail(
        statistical_tolerance=0.05,
        trend_significance_threshold=0.10,
        strict_mode=False
    )
    
    # Check for entity existence
    entity_result = guardrail.validate_entity_existence(
        response=text,
        known_entities=entities,
        entity_type="player"
    )
    if entity_result.tripwire_triggered:
        discrepancies.extend(entity_result.discrepancies)
    
    # Check for fabricated entities
    fabrication_result = guardrail.validate_no_fabricated_entities(
        response=text,
        known_entities=entities,
        entity_type="player"
    )
    if fabrication_result.tripwire_triggered:
        discrepancies.extend(fabrication_result.discrepancies)
    
    # Check numerical values
    numerical_result = guardrail.validate_numerical_values(
        response=text,
        known_values=values,
        value_type="database"
    )
    if numerical_result.tripwire_triggered:
        discrepancies.extend(numerical_result.discrepancies)
    
    # Check statistical claims
    stats_result = guardrail.validate_statistical_claims(
        response=text,
        known_stats={},  # No specific stats to validate
        strict_mode=False
    )
    if stats_result.tripwire_triggered:
        discrepancies.extend(stats_result.discrepancies)
    
    return len(discrepancies) == 0, discrepancies

async def main():
    """Run the example."""
    print("DataAnalystGuardrail Example - Testing with real database data")
    print("=" * 80)
    
    # First, test with accurate analyst (should pass)
    await run_example_with_agent(
        agent_name="AccurateDataAnalyst",
        instructions=accurate_analyst_instructions,
        should_pass=True
    )
    
    # Then, test with inaccurate analyst (should trigger guardrail)
    await run_example_with_agent(
        agent_name="InaccurateDataAnalyst",
        instructions=inaccurate_analyst_instructions,
        should_pass=False
    )

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    print(f"Using database: {DB_PATH.absolute()}")
    if not DB_PATH.exists():
        print(f"Warning: Database file {DB_PATH} does not exist!")
    asyncio.run(main())
    print("\nDone") 