#!/usr/bin/env python3
"""
Test script for the FollowUpPredictorAgent.

This script tests the FollowUpPredictorAgent by processing a query
through the full agent pipeline with the follow-up predictor added.
"""

import os
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

from smite2_agent.pipeline.base.data_package import DataPackage
from smite2_agent.agents.query_analyst import QueryAnalystAgent
from smite2_agent.agents.data_engineer import DataEngineerAgent
from smite2_agent.agents.data_analyst import DataAnalystAgent
from smite2_agent.agents.response_composer import ResponseComposerAgent
from smite2_agent.agents.followup_predictor import FollowUpPredictorAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_followup_agent(query: str, db_path: Path, model: str = "gpt-4o"):
    """
    Test the FollowUpPredictorAgent by processing a query through the pipeline.
    
    Args:
        query: Query to process
        db_path: Path to the database
        model: Model to use
    """
    logger.info(f"Testing FollowUpPredictorAgent with query: {query}")
    
    # Create a new data package
    data_package = DataPackage(query=query)
    if db_path:
        data_package.set_db_path(str(db_path))
    
    # Create the agents
    query_analyst = QueryAnalystAgent(
        db_path=str(db_path),
        model=model,
        temperature=0.3
    )
    
    data_engineer = DataEngineerAgent(
        db_path=db_path,
        model=model,
        temperature=0.2
    )
    
    data_analyst = DataAnalystAgent(
        model=model,
        temperature=0.3
    )
    
    response_composer = ResponseComposerAgent(
        model=model,
        temperature=0.7
    )
    
    followup_predictor = FollowUpPredictorAgent(
        model=model,
        temperature=0.4,
        db_path=db_path
    )
    
    # Process the query through the pipeline
    logger.info("Step 1: Processing with QueryAnalystAgent")
    data_package = await query_analyst._process(data_package)
    print_step_output("Query Analysis", data_package)
    
    logger.info("Step 2: Processing with DataEngineerAgent")
    data_package = await data_engineer.process_question(data_package)
    print_step_output("Data Engineering", data_package)
    
    logger.info("Step 3: Processing with DataAnalystAgent")
    data_package = await data_analyst.process_data(data_package)
    print_step_output("Data Analysis", data_package)
    
    logger.info("Step 4: Processing with ResponseComposerAgent")
    data_package = await response_composer.generate_response(data_package)
    print_step_output("Response Composition", data_package)
    
    logger.info("Step 5: Processing with FollowUpPredictorAgent")
    data_package = await followup_predictor._process(data_package)
    
    # Print the final, enhanced response
    print("\n\n========== FINAL ENHANCED RESPONSE ==========")
    print(data_package.get_response())
    print("==============================================\n")
    
    # Print suggested follow-up questions if available
    package_dict = data_package.to_dict()
    if "enhancement" in package_dict and "suggested_questions" in package_dict["enhancement"]:
        print("\n========== SUGGESTED FOLLOW-UP QUESTIONS ==========")
        for i, question in enumerate(package_dict["enhancement"]["suggested_questions"]):
            print(f"{i+1}. {question}")
        print("====================================================\n")
    
    return data_package

def print_step_output(step_name: str, data_package: DataPackage):
    """
    Print the output from a pipeline step.
    
    Args:
        step_name: Name of the step
        data_package: Data package after the step
    """
    print(f"\n\n========== {step_name} Output ==========")
    
    package_dict = data_package.to_dict()
    
    if step_name == "Query Analysis":
        if "query_analysis" in package_dict:
            query_analysis = package_dict["query_analysis"]
            if "sql_suggestion" in query_analysis:
                if isinstance(query_analysis["sql_suggestion"], list):
                    for i, sql in enumerate(query_analysis["sql_suggestion"]):
                        print(f"SQL Query {i+1}: {sql['query']}")
                        print(f"Purpose: {sql['purpose']}\n")
                else:
                    print(f"SQL Query: {query_analysis['sql_suggestion']}")
            print(f"Needs Multiple Queries: {query_analysis.get('needs_multiple_queries', False)}")
    
    elif step_name == "Data Engineering":
        if "query_results" in package_dict:
            query_results = package_dict["query_results"]
            for query_id, result in query_results.items():
                print(f"\nQuery {query_id} Results:")
                if "column_names" in result:
                    print(f"Columns: {result['column_names']}")
                if "data" in result:
                    print(f"Row count: {len(result['data'])}")
                    if len(result['data']) > 0:
                        print(f"First row: {result['data'][0]}")
    
    elif step_name == "Data Analysis":
        if "analysis_results" in package_dict:
            analysis = package_dict["analysis_results"]
            print(f"Analysis: {analysis}")
    
    elif step_name == "Response Composition":
        if "response" in package_dict:
            print(f"Response: {package_dict['response']}")
    
    print("=====================================\n")

async def main():
    """Run the test script."""
    # Define test queries
    test_queries = [
        "Which player dealt the most damage in the match?",
        "How many kills did each player get?",
        "Which god performed best in the match?",
        "Compare the top 2 damage dealers in the match",
    ]
    
    # Get the database path
    db_path = Path("data/CombatLogExample.db")
    if not db_path.exists():
        logger.error(f"Database file not found at {db_path}")
        return
    
    # Process one query
    selected_query = test_queries[0]  # You can change the index to test different queries
    
    await test_followup_agent(selected_query, db_path)

if __name__ == "__main__":
    asyncio.run(main()) 