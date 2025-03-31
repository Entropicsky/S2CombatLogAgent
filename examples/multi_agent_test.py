#!/usr/bin/env python3
"""
Multi-agent test for the OpenAI Agents SDK with handoffs and tools.
"""

import os
import sys
import asyncio
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

# Define a simple tool
@function_tool
def get_weather(location: str) -> str:
    """Get the weather for a location."""
    print(f"Tool called: get_weather({location})")
    return f"It's sunny in {location} today with a high of 75°F."

# Define a tool for time-based information
@function_tool
def get_current_time(timezone: str) -> str:
    """Get the current time in a specific timezone."""
    print(f"Tool called: get_current_time({timezone})")
    from datetime import datetime
    return f"The current time is {datetime.now().strftime('%H:%M:%S')} in {timezone}."

async def main():
    """Run a multi-agent test with handoffs."""
    # Create model settings
    model_settings = ModelSettings(
        temperature=0.2,
        max_tokens=1000
    )
    
    # Create specialist agents
    weather_agent = Agent(
        name="WeatherAgent",
        handoff_description="Specialist agent for weather-related questions",
        instructions="""You are a weather specialist who can provide weather information for any location.
        Use the get_weather tool to fetch current weather data when asked.""",
        model="gpt-4o",
        model_settings=model_settings,
        tools=[get_weather]
    )
    
    time_agent = Agent(
        name="TimeAgent",
        handoff_description="Specialist agent for time-related questions",
        instructions="""You are a time specialist who can provide current time information.
        Use the get_current_time tool to fetch the current time when asked.""",
        model="gpt-4o",
        model_settings=model_settings,
        tools=[get_current_time]
    )
    
    # Create the orchestrator (triage) agent
    triage_agent = Agent(
        name="TriageAgent",
        instructions="""You are a helpful assistant that routes questions to specialist agents.
        
        For weather-related questions, hand off to the WeatherAgent.
        For time-related questions, hand off to the TimeAgent.
        For general questions, answer directly.
        
        Be responsive and helpful.""",
        model="gpt-4o",
        model_settings=model_settings,
        handoffs=[weather_agent, time_agent]
    )
    
    # Queries to test
    queries = [
        "What is the weather in New York?",
        "What time is it now?",
        "What is the capital of Japan?"
    ]
    
    # Run each query through the triage agent
    for i, query in enumerate(queries):
        print(f"\n=== Query {i+1}: {query} ===")
        result = await Runner.run(triage_agent, query)
        print(f"Response: {result.final_output}")
        
        # Print agent trace info
        if hasattr(result, 'trace_id'):
            print(f"Trace ID: {result.trace_id}")
        
        # Print tool usage and handoffs
        print("Tools used:", [t.name for t in result.tools_used] if hasattr(result, 'tools_used') and result.tools_used else "None")
        print("Handoffs:", [h.name for h in result.handoffs] if hasattr(result, 'handoffs') and result.handoffs else "None")

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    asyncio.run(main())
    print("\nDone") 