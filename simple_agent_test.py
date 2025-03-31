#!/usr/bin/env python3
"""
Simple test for creating and running an agent with the OpenAI Agents SDK.
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

async def main():
    """Run a simple test with an agent."""
    # Create a simple agent
    simple_agent = Agent(
        name="SimpleAgent",
        instructions="You are a helpful assistant that answers questions concisely.",
        model="gpt-4o",
        model_settings=ModelSettings(
            temperature=0.7,
            max_tokens=1000
        )
    )
    print(f"Created agent: {simple_agent.name}")
    
    # Run the agent with a simple query
    query = "What is the capital of France?"
    print(f"\nRunning agent with query: '{query}'")
    
    # Use the static run method from Runner
    result = await Runner.run(simple_agent, query)
    
    # Print the response
    print("\nResponse:")
    print(f"Content: {result.final_output}")
    
    return result

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    asyncio.run(main())
    print("Done") 