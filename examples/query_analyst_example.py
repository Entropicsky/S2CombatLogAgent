#!/usr/bin/env python3
"""
Example demonstrating the Query Analyst Agent functionality.

This example shows how the Query Analyst Agent:
1. Extracts match context from a database
2. Analyzes different types of user queries
3. Provides enhanced context for downstream agents
"""

import os
import sys
import asyncio
from pathlib import Path
from pprint import pprint
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment")

# Set OpenAI API key for the Agents SDK
os.environ["OPENAI_API_KEY"] = api_key

# Add parent directory to path for importing smite2_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smite2_agent.agents.query_analyst import QueryAnalystAgent
from smite2_agent.pipeline.base.data_package import DataPackage

# Database path
DB_PATH = Path("data/CombatLogExample.db")

async def main():
    """Run the example."""
    print(f"Using database: {DB_PATH.absolute()}")
    if not DB_PATH.exists():
        print(f"Error: Database file {DB_PATH} does not exist!")
        return
    
    print("\n=== Initializing Query Analyst Agent ===")
    # Create the Query Analyst Agent
    agent = QueryAnalystAgent(
        db_path=DB_PATH,
        model="gpt-4o",
        temperature=0.2
    )
    
    # Display match context
    print("\n=== Match Context ===")
    if agent.match_context["initialized"]:
        print(f"Players: {len(agent.match_context['players'])}")
        
        if agent.match_context["top_damage_dealers"]:
            top_damage = agent.match_context["top_damage_dealers"][0]
            print(f"Top damage dealer: {top_damage['player']} with {top_damage['total_damage']} damage")
        
        if agent.match_context["top_healing"]:
            top_healing = agent.match_context["top_healing"][0]
            print(f"Top healer: {top_healing['player']} with {top_healing['total_healing']} healing")
        
        print(f"Match duration: {agent.match_context['match_duration']}")
        
        print("\nPlayer details:")
        for i, player in enumerate(agent.match_context["players"][:5]):  # Show first 5 players
            print(f"  {i+1}. {player['name']} playing {player['god']} as {player['role']} on Team {player['team_id']}")
    else:
        print("Match context initialization failed")
    
    # Test different types of queries
    test_queries = [
        "Who dealt the most damage in the match?",
        "Which ability did the most healing?",
        "How did MateoUwU perform in the match?",
        "What objectives were taken in the first 10 minutes?",
        "Compare the damage output between the mid and jungle players"
    ]
    
    for query in test_queries:
        print(f"\n\n=== Analyzing Query: '{query}' ===")
        
        # Create a data package for the query
        data_package = DataPackage(query=query)
        data_package.set_db_path(DB_PATH)
        
        # Process the query
        result_package = await agent.analyze_query(data_package)
        
        # Display the results
        if result_package.has_errors():
            print("Error analyzing query:")
            pprint(result_package.get_all_errors())
            continue
        
        domain_analysis = result_package.get_domain_analysis()
        if domain_analysis:
            print(f"Query type: {domain_analysis['query_type']}")
            print(f"Intent: {domain_analysis['intent']}")
            
            print("\nEntities:")
            for entity in domain_analysis['entities']:
                print(f"  - {entity.get('name', 'Unknown')} ({entity.get('type', 'Unknown')})")
            
            print("\nMetrics:")
            for metric in domain_analysis['metrics']:
                print(f"  - {metric.get('name', 'Unknown')}")
            
            print("\nEnhanced query:")
            print(f"  {domain_analysis['enhanced_query']}")
            
            # Show SQL suggestions if available
            query_analysis = result_package.to_dict().get("query_analysis", {})
            if "sql_queries" in query_analysis and query_analysis["sql_queries"]:
                print("\nSQL suggestions:")
                for i, suggestion in enumerate(query_analysis["sql_queries"]):
                    print(f"\n  Suggestion {i+1}: {suggestion.get('description', '')}")
                    print(f"  {suggestion.get('query', 'No query')}")

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    asyncio.run(main())
    print("\nDone") 