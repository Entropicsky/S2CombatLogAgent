#!/usr/bin/env python3
"""
Example demonstrating the SMITE 2 Combat Log Agent's VisualizationGuardrail.

This example retrieves real data from the database, creates a Visualization Specialist agent,
and tests the guardrail with both valid and invalid chart visualizations.
"""

import asyncio
import os
import sys
import json
import logging
import re
import matplotlib.pyplot as plt
import io
import base64
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
logger = logging.getLogger("visualization_guardrail_example")

# Add parent directory to path for importing smite2_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smite2_agent.tools.sql_tools import run_sql_query
from smite2_agent.guardrails import (
    VisualizationGuardrail, 
    VisualizationOutput, 
    ChartData, 
    ChartMetadata
)

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
visualization_data = {
    "entities": {},
    "values": [],
    "query_results": {},
    "charts": []
}

# Define SQL query tool for agents
@function_tool(strict_mode=False)
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
    global visualization_data
    
    logger.info(f"Executing SQL query: {query}")
    result = run_sql_query(query, DB_PATH, format_as="dict")
    
    if result["success"]:
        logger.info(f"Query successful: {result['row_count']} rows returned")
        
        # Store query result for validation
        query_id = f"query_{len(visualization_data['query_results']) + 1}"
        visualization_data["query_results"][query_id] = result
        
        try:
            # Store player entities
            if isinstance(result["data"], list) and len(result["data"]) > 0:
                if any("player" in row for row in result["data"]):
                    for row in result["data"]:
                        if "player" in row:
                            player_name = row["player"]
                            visualization_data["entities"][player_name] = row.get("player_id", "unknown_id")
                
                # Store numerical values
                for row in result["data"]:
                    for key, value in row.items():
                        if isinstance(value, (int, float)) and value > 0:
                            visualization_data["values"].append(value)
        
        except Exception as e:
            logger.error(f"Error storing query results: {str(e)}")
    else:
        logger.error(f"Query failed: {result.get('error', 'Unknown error')}")
    
    return result

@function_tool(strict_mode=False)
async def create_bar_chart(
    data: List[Dict[str, Any]],
    x_field: str,
    y_field: str,
    title: str,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a bar chart from data.
    
    Args:
        data: List of data points
        x_field: Field to use for x-axis
        y_field: Field to use for y-axis
        title: Chart title
        x_label: Optional x-axis label (defaults to x_field)
        y_label: Optional y-axis label (defaults to y_field)
        
    Returns:
        Dictionary with chart information including:
        - success: Whether chart creation was successful
        - chart_id: Unique ID for the chart
        - title: Chart title
        - type: "bar"
        - data_summary: Summary of the data used
    """
    global visualization_data
    
    # Use field names for axis labels if not provided
    if not x_label:
        x_label = x_field
    if not y_label:
        y_label = y_field
    
    try:
        # Extract x and y values
        x_values = [row.get(x_field, "") for row in data]
        y_values = [row.get(y_field, 0) for row in data]
        
        # Create chart metadata
        chart_id = len(visualization_data["charts"])
        chart_metadata = ChartMetadata(
            title=title,
            x_label=x_label,
            y_label=y_label,
            chart_type="bar",
            data_source=f"query_{len(visualization_data['query_results'])}"
        )
        
        # Create chart data
        chart_data = ChartData(
            data=data,
            x_values=x_values,
            y_values=y_values,
            categories=x_values
        )
        
        # Store for validation
        visualization_data["charts"].append({
            "metadata": chart_metadata,
            "data": chart_data,
            "description": f"Bar chart showing {y_label} by {x_label}."
        })
        
        # Create actual chart (not saved, just for demonstration)
        plt.figure(figsize=(10, 6))
        plt.bar(x_values, y_values)
        plt.title(title)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Convert plot to base64 string (simulating chart creation)
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        return {
            "success": True,
            "chart_id": chart_id,
            "title": title,
            "type": "bar",
            "data_summary": {
                "x_values": x_values,
                "y_values": y_values
            },
            "image": f"data:image/png;base64,{image_base64[:20]}..." # Truncated for brevity
        }
        
    except Exception as e:
        logger.error(f"Error creating bar chart: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@function_tool(strict_mode=False)
async def create_line_chart(
    data: List[Dict[str, Any]],
    x_field: str,
    y_field: str,
    title: str,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    series_field: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a line chart from data.
    
    Args:
        data: List of data points
        x_field: Field to use for x-axis
        y_field: Field to use for y-axis
        title: Chart title
        x_label: Optional x-axis label (defaults to x_field)
        y_label: Optional y-axis label (defaults to y_field)
        series_field: Optional field to split data into multiple series
        
    Returns:
        Dictionary with chart information including:
        - success: Whether chart creation was successful
        - chart_id: Unique ID for the chart
        - title: Chart title
        - type: "line"
        - data_summary: Summary of the data used
    """
    global visualization_data
    
    # Use field names for axis labels if not provided
    if not x_label:
        x_label = x_field
    if not y_label:
        y_label = y_field
    
    try:
        # Extract data series
        if series_field:
            # Create multiple series
            series = {}
            for row in data:
                series_name = str(row.get(series_field, "Unknown"))
                if series_name not in series:
                    series[series_name] = {"x": [], "y": []}
                series[series_name]["x"].append(row.get(x_field, ""))
                series[series_name]["y"].append(row.get(y_field, 0))
            
            x_values = [row.get(x_field, "") for row in data]
            y_values = [row.get(y_field, 0) for row in data]
            
            # Create chart metadata
            chart_id = len(visualization_data["charts"])
            chart_metadata = ChartMetadata(
                title=title,
                x_label=x_label,
                y_label=y_label,
                chart_type="line",
                data_source=f"query_{len(visualization_data['query_results'])}"
            )
            
            # Create chart data with series
            chart_data = ChartData(
                data=data,
                x_values=list(set(x_values)),  # Unique x values
                y_values=y_values,
                series=series
            )
            
            # Store for validation
            visualization_data["charts"].append({
                "metadata": chart_metadata,
                "data": chart_data,
                "description": f"Line chart showing {y_label} over {x_label} by {series_field}."
            })
            
            # Create actual chart (not saved, just for demonstration)
            plt.figure(figsize=(10, 6))
            for series_name, values in series.items():
                plt.plot(values["x"], values["y"], label=series_name)
            plt.title(title)
            plt.xlabel(x_label)
            plt.ylabel(y_label)
            plt.legend()
            plt.xticks(rotation=45)
            plt.tight_layout()
            
        else:
            # Single series
            x_values = [row.get(x_field, "") for row in data]
            y_values = [row.get(y_field, 0) for row in data]
            
            # Create chart metadata
            chart_id = len(visualization_data["charts"])
            chart_metadata = ChartMetadata(
                title=title,
                x_label=x_label,
                y_label=y_label,
                chart_type="line",
                data_source=f"query_{len(visualization_data['query_results'])}"
            )
            
            # Create chart data
            chart_data = ChartData(
                data=data,
                x_values=x_values,
                y_values=y_values
            )
            
            # Store for validation
            visualization_data["charts"].append({
                "metadata": chart_metadata,
                "data": chart_data,
                "description": f"Line chart showing {y_label} over {x_label}."
            })
            
            # Create actual chart (not saved, just for demonstration)
            plt.figure(figsize=(10, 6))
            plt.plot(x_values, y_values)
            plt.title(title)
            plt.xlabel(x_label)
            plt.ylabel(y_label)
            plt.xticks(rotation=45)
            plt.tight_layout()
        
        # Convert plot to base64 string (simulating chart creation)
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        return {
            "success": True,
            "chart_id": chart_id,
            "title": title,
            "type": "line",
            "data_summary": {
                "x_values": x_values[:5] + (["..."] if len(x_values) > 5 else []),
                "y_values": y_values[:5] + (["..."] if len(y_values) > 5 else [])
            },
            "image": f"data:image/png;base64,{image_base64[:20]}..." # Truncated for brevity
        }
        
    except Exception as e:
        logger.error(f"Error creating line chart: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@function_tool(strict_mode=False)
async def create_pie_chart(
    data: List[Dict[str, Any]],
    label_field: str,
    value_field: str,
    title: str,
    max_slices: int = 7
) -> Dict[str, Any]:
    """
    Create a pie chart from data.
    
    Args:
        data: List of data points
        label_field: Field to use for slice labels
        value_field: Field to use for slice values
        title: Chart title
        max_slices: Maximum number of slices (will group small values as "Other")
        
    Returns:
        Dictionary with chart information including:
        - success: Whether chart creation was successful
        - chart_id: Unique ID for the chart
        - title: Chart title
        - type: "pie"
        - data_summary: Summary of the data used
    """
    global visualization_data
    
    try:
        # Extract labels and values
        labels = [row.get(label_field, "") for row in data]
        values = [row.get(value_field, 0) for row in data]
        
        # Group small values if there are too many slices
        if len(labels) > max_slices:
            sorted_data = sorted(zip(labels, values), key=lambda x: x[1], reverse=True)
            top_labels = [item[0] for item in sorted_data[:max_slices-1]]
            top_values = [item[1] for item in sorted_data[:max_slices-1]]
            other_value = sum(item[1] for item in sorted_data[max_slices-1:])
            
            labels = top_labels + ["Other"]
            values = top_values + [other_value]
        
        # Calculate percentages
        total = sum(values)
        percentages = [100 * v / total for v in values] if total > 0 else values
        
        # Create chart metadata
        chart_id = len(visualization_data["charts"])
        chart_metadata = ChartMetadata(
            title=title,
            chart_type="pie",
            data_source=f"query_{len(visualization_data['query_results'])}"
        )
        
        # Create chart data
        chart_data = ChartData(
            data=[{"label": label, "value": value, "percentage": pct} 
                  for label, value, pct in zip(labels, values, percentages)],
            x_values=labels,
            y_values=percentages,
            categories=labels
        )
        
        # Store for validation
        visualization_data["charts"].append({
            "metadata": chart_metadata,
            "data": chart_data,
            "description": f"Pie chart showing distribution of {value_field} by {label_field}."
        })
        
        # Create actual chart (not saved, just for demonstration)
        plt.figure(figsize=(10, 6))
        plt.pie(values, labels=labels, autopct='%1.1f%%')
        plt.title(title)
        plt.axis('equal')
        
        # Convert plot to base64 string (simulating chart creation)
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        return {
            "success": True,
            "chart_id": chart_id,
            "title": title,
            "type": "pie",
            "data_summary": {
                "labels": labels,
                "values": values,
                "percentages": [f"{p:.1f}%" for p in percentages]
            },
            "image": f"data:image/png;base64,{image_base64[:20]}..." # Truncated for brevity
        }
        
    except Exception as e:
        logger.error(f"Error creating pie chart: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# Visualization specialist instructions for the accurate agent
accurate_vis_instructions = """
You are a SMITE 2 visualization specialist focusing on creating informative and accurate
visualizations of combat data. Your job is to create charts and graphs that help users
understand the data trends and patterns.

CRITICAL INSTRUCTION: You MUST follow these steps for every visualization:
1. FIRST, use the query_database tool to retrieve data from the database
2. Look at the actual data returned in the 'data' field of the response
3. Create appropriate visualizations based ONLY on the actual database results
4. Use the exact values, names, and numbers from the query results
5. Choose appropriate chart types for the data being visualized
6. Provide clear titles, labels, and descriptions for all charts

NEVER fabricate or hallucinate any information not present in the results.
All visualizations must accurately represent the actual data.

Guidelines for selecting chart types:
- Use bar charts for comparing values across categories
- Use line charts for time series data
- Use pie charts for showing composition or part-to-whole relationships (limit to 7 slices max)

Your visualizations should be:
1. Factually accurate with precise numbers from the database
2. Appropriately labeled with clear titles and axis labels
3. The right type of chart for the data being presented
4. Include proper references to specific player names from the data (never make up names)

Always consider the data structure when choosing a visualization:
- Categorical data (player names, ability names) work well as bar chart categories or pie chart slices
- Numeric data over time should use line charts
- Ranked data (most damage to least) works well with horizontal bar charts

Example Queries:
- To visualize player damage:
  ```sql
  SELECT source_entity as player, SUM(damage_amount) as damage
  FROM combat_events
  WHERE event_type = 'Damage'
  GROUP BY source_entity
  ORDER BY damage DESC;
  ```

- To visualize damage over time:
  ```sql
  SELECT 
    strftime('%M:%S', event_time) as timestamp,
    SUM(damage_amount) as damage
  FROM combat_events
  WHERE event_type = 'Damage'
  GROUP BY timestamp
  ORDER BY timestamp;
  ```

Your response should include:
1. A description of the visualizations created
2. The insights that can be gained from each visualization
3. Any patterns or trends visible in the charts
"""

# Visualization specialist instructions that will produce inaccurate visualizations
inaccurate_vis_instructions = """
You are a SMITE 2 visualization specialist focusing on creating visualizations of combat data.
For this TEST EXAMPLE, you are going to intentionally create some inaccurate visualizations.

When you get a query about combat data, do the following:
1. Use the query_database tool to retrieve the real data
2. Then, for your charts, INTENTIONALLY make the following errors:
   - Include a made-up player named "Zephyr" in one of your charts
   - Exaggerate the top values by approximately 25% in your charts
   - Choose an inappropriate chart type for at least one visualization (e.g., pie chart for time series)
   - Omit axis labels or use incorrect labels
   - Include too many slices in a pie chart (more than 7)

This is ONLY for testing the guardrail system, which is why we want you to
make these specific errors.

For this test, your visualizations should:
1. Include at least one fabricated entity name
2. Contain inflated values
3. Use at least one inappropriate chart type
4. Have missing or incorrect labels
5. Violate best practices for the chart type (e.g., too many pie slices)

This will allow us to verify our guardrail system is working correctly.
"""

async def run_example_with_agent(agent_name: str, instructions: str, should_pass: bool):
    """Run the example with a specific agent."""
    print(f"\nRunning example with {agent_name}...")
    print("=" * 80)
    
    # Reset the global visualization data
    global visualization_data
    visualization_data = {
        "entities": {},
        "values": [],
        "query_results": {},
        "charts": []
    }
    
    # Create the visualization specialist agent
    model_settings = ModelSettings(
        temperature=0.2  # Lower temperature for more precise responses
    )
    
    # Create a visualization specialist agent
    visualization_agent = Agent(
        name=agent_name,
        instructions=instructions,
        tools=[query_database, create_bar_chart, create_line_chart, create_pie_chart],
        output_type=None,  # Set to None to avoid schema conflicts
        model="gpt-4o",
        model_settings=model_settings
    )
    
    # Create a runner
    from agents import Runner
    runner = Runner()
    
    # Example query
    query = "Create visualizations to show which player dealt the most damage and how damage output changed over time during the match."
    
    print(f"\nProcessing query: '{query}'")
    print("-" * 80)
    
    try:
        # Process the query using Runner
        response = await runner.run(visualization_agent, query)
        
        # Extract visualization output
        output_text = response.final_output
        if isinstance(output_text, str):
            output_response = output_text
        else:
            output_response = getattr(output_text, 'response', str(output_text))

        # Print the result
        print("\nFinal response:")
        print("-" * 80)
        print(output_response)
        print("-" * 80)
        
        # Summarize charts created
        print(f"\nCharts created: {len(visualization_data['charts'])}")
        for i, chart in enumerate(visualization_data["charts"]):
            metadata = chart["metadata"]
            print(f"Chart {i+1}: {metadata.title} ({metadata.chart_type})")
            if hasattr(metadata, "x_label") and metadata.x_label:
                print(f"  X-axis: {metadata.x_label}")
            if hasattr(metadata, "y_label") and metadata.y_label:
                print(f"  Y-axis: {metadata.y_label}")
        print("-" * 80)
        
        # Create the guardrail
        guardrail = VisualizationGuardrail()
        
        # Create visualization output for validation
        charts = []
        chart_data = {}
        chart_metadata = {}
        chart_descriptions = []
        
        for i, chart in enumerate(visualization_data["charts"]):
            charts.append({"id": i})
            chart_data[str(i)] = chart["data"]
            chart_metadata[str(i)] = chart["metadata"]
            chart_descriptions.append(chart["description"])
        
        # Directly validate the response content
        try:
            response_validation = guardrail.validate_visualization_response(
                response=output_response,
                raw_data=visualization_data
            )
            
            # Validate charts if available
            chart_validations = []
            for i, chart in enumerate(visualization_data["charts"]):
                # Get the original data for this chart
                data_source = chart["metadata"].data_source
                original_data = visualization_data.get("query_results", {}).get(data_source, {}).get("data", [])
                
                chart_validation = guardrail.validate_chart(
                    chart_data=chart["data"],
                    chart_metadata=chart["metadata"],
                    chart_description=chart["description"],
                    original_data=original_data,
                    known_entities=visualization_data["entities"]
                )
                chart_validations.append(chart_validation)
            
            # Combine all validation results
            all_validations = [response_validation] + chart_validations
            combined_validation = guardrail.combine_validation_results(all_validations)
            
            # Check if validation triggered the guardrail
            if combined_validation.tripwire_triggered:
                print("\nGuardrail triggered! Visualizations contained inaccuracies:")
                print("-" * 80)
                for discrepancy in combined_validation.discrepancies:
                    print(f"- {discrepancy}")
                print("-" * 80)
                print(f"Guardrail {'correctly rejected' if not should_pass else 'incorrectly rejected'} the response.")
            else:
                print(f"Guardrail {'passed' if should_pass else 'failed to detect issues'} - response was accepted.")
        
        except Exception as e:
            print(f"\nValidation error: {str(e)}")
        
        # Print the data collected for validation
        print("\nData collected for validation:")
        print("-" * 80)
        print(f"Entities: {len(visualization_data['entities'])} players")
        print(f"Values: {len(visualization_data['values'])} numerical values")
        print(f"Queries: {len(visualization_data['query_results'])} database queries")
        print(f"Charts: {len(visualization_data['charts'])} visualizations")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        if hasattr(e, 'error_info'):
            print(f"Error info: {e.error_info}")

async def main():
    """Run the example."""
    print("VisualizationGuardrail Example - Testing with real database data")
    print("=" * 80)
    
    # First, test with accurate visualization specialist (should pass)
    await run_example_with_agent(
        agent_name="AccurateVisSpecialist",
        instructions=accurate_vis_instructions,
        should_pass=True
    )
    
    # Then, test with inaccurate visualization specialist (should trigger guardrail)
    await run_example_with_agent(
        agent_name="InaccurateVisSpecialist",
        instructions=inaccurate_vis_instructions,
        should_pass=False
    )

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    print(f"Using database: {DB_PATH.absolute()}")
    if not DB_PATH.exists():
        print(f"Warning: Database file {DB_PATH} does not exist!")
    asyncio.run(main())
    print("\nDone") 