"""
Orchestrator Agent for SMITE 2 Combat Log Agent.

This module implements a simple Orchestrator that coordinates the
pipeline of specialized agents for processing user queries about
combat log data. It handles:

1. Receiving the initial user query
2. Routing the query through the appropriate agents
3. Coordinating between agents using a DataPackage
4. Handling errors and agent failures
5. Returning the final response to the user
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from smite2_agent.agents.query_analyst import QueryAnalystAgent
from smite2_agent.agents.data_engineer import DataEngineerAgent
from smite2_agent.agents.data_analyst import DataAnalystAgent
from smite2_agent.agents.response_composer import ResponseComposerAgent
from smite2_agent.pipeline.base.data_package import DataPackage

# Set up logging
logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Simple orchestrator that coordinates the processing pipeline for user queries.
    
    This orchestrator manages the flow between the four essential agents:
    1. Query Analyst Agent - Query analysis and intent detection
    2. Data Engineer Agent - SQL generation and database querying
    3. Data Analyst Agent - Analysis of query results
    4. Response Composer Agent - Final response creation
    """
    
    def __init__(
        self,
        db_path: Union[str, Path],
        model: str = "gpt-4o",
        strict_mode: bool = False,
        schema_cache_path: Optional[Path] = None
    ):
        """
        Initialize the orchestrator with the necessary agents.
        
        Args:
            db_path: Path to the SQLite database file
            model: The LLM model to use (default: gpt-4o)
            strict_mode: Whether to use strict mode for guardrails (default: False)
            schema_cache_path: Optional path to cache the database schema
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
        
        self.model = model
        self.strict_mode = strict_mode
        
        # Initialize the specialized agents
        self.query_analyst = QueryAnalystAgent(
            db_path=self.db_path,
            model=model,
            temperature=0.3,
            strict_mode=strict_mode,
            schema_cache_path=schema_cache_path
        )
        
        self.data_engineer = DataEngineerAgent(
            db_path=self.db_path,
            model=model,
            strict_mode=strict_mode,
            schema_cache_path=schema_cache_path
        )
        
        self.data_analyst = DataAnalystAgent(
            model=model,
            strict_mode=strict_mode
        )
        
        self.response_composer = ResponseComposerAgent(
            model=model,
            strict_mode=strict_mode
        )
        
        logger.info(f"Initialized Orchestrator with database: {self.db_path.name}")
    
    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a natural language query using the agent pipeline.
        
        Args:
            query: The natural language query from the user
            
        Returns:
            Dictionary with the response or error information
        """
        logger.info(f"Processing query: {query}")
        
        # Create a new data package
        data_package = DataPackage(query=query)
        data_package.set_db_path(self.db_path)
        
        # Start the pipeline
        try:
            # 1. Use Query Analyst agent to analyze the query and determine intent
            logger.info("Step 1: Query analysis")
            data_package = await self.query_analyst.analyze_query(data_package)
            
            # Check for errors from the Query Analyst
            if data_package.has_errors():
                error = data_package.get_first_error()
                return {
                    "success": False,
                    "response": f"Error analyzing query: {error['error']}",
                    "all_errors": data_package.get_all_errors()
                }
            
            # 2. Use Data Engineer agent to transform the query into SQL and execute it
            logger.info("Step 2: Data engineering")
            data_package = await self.data_engineer.process_question(data_package)
            
            # Check for errors from the Data Engineer
            if data_package.has_errors():
                error = data_package.get_first_error()
                return {
                    "success": False,
                    "response": f"Error generating SQL: {error['error']}",
                    "all_errors": data_package.get_all_errors()
                }
            
            # 3. Use Data Analyst agent to analyze the query results
            logger.info("Step 3: Data analysis")
            data_package = await self.data_analyst.process_data(data_package)
            
            # Check for errors from the Data Analyst
            if data_package.has_errors():
                error = data_package.get_first_error()
                return {
                    "success": False,
                    "response": f"Error analyzing data: {error['error']}",
                    "all_errors": data_package.get_all_errors()
                }
            
            # 4. Use Response Composer agent to generate the final response
            logger.info("Step 4: Response composition")
            data_package = await self.response_composer.generate_response(data_package)
            
            # Check for errors from the Response Composer
            if data_package.has_errors():
                error = data_package.get_first_error()
                return {
                    "success": False,
                    "response": f"Error composing response: {error['error']}",
                    "all_errors": data_package.get_all_errors()
                }
            
            # Get the final response
            response = data_package.get_response()
            
            return {
                "success": True,
                "response": response,
                "data_package": data_package.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                "success": False,
                "response": f"An unexpected error occurred: {str(e)}",
                "error_type": "unexpected_error"
            }
    
    def _create_error_response(self, data_package: DataPackage) -> Dict[str, Any]:
        """
        Create a user-friendly error response from a failed data package.
        
        Args:
            data_package: DataPackage containing errors
            
        Returns:
            Dictionary with error information and user-friendly message
        """
        errors = data_package.get_errors()
        query = data_package.get_user_query()
        
        # Extract error messages
        error_messages = []
        for error in errors:
            agent = error.get("agent", "Unknown")
            message = error.get("error", "Unknown error")
            error_messages.append(f"{agent}: {message}")
        
        # Create a user-friendly response
        user_message = """
I'm sorry, but I encountered an issue while processing your question.

Please try:
1. Rephrasing your question to be more specific
2. Asking about data that exists in the combat log database
3. Breaking complex questions into simpler ones
        """
        
        if self.strict_mode:
            # In strict mode, include technical details
            user_message += "\n\nTechnical details:\n" + "\n".join(error_messages)
        
        return {
            "success": False,
            "error": error_messages[0] if error_messages else "Unknown error",
            "all_errors": error_messages,
            "response": user_message,
            "data_package": data_package.get_debug_info() if self.strict_mode else None
        }
    
    async def chat(self, query: str) -> str:
        """
        Simple chat interface for direct interaction.
        
        Args:
            query: The user's question
            
        Returns:
            Response text
        """
        result = await self.process_query(query)
        
        if result["success"]:
            return result["response"]
        else:
            return result["response"]
    
    def update_database(self, new_db_path: Union[str, Path]) -> None:
        """
        Update the database path and reset all agents.
        
        Args:
            new_db_path: Path to the new database file
        """
        new_db_path = Path(new_db_path)
        if not new_db_path.exists():
            raise FileNotFoundError(f"Database file not found: {new_db_path}")
        
        self.db_path = new_db_path
        
        # Update each agent with the new database
        self.query_analyst.update_match_context(self.db_path)
        
        # For other agents, we'll rely on the data package to pass the new path
        logger.info(f"Updated database to: {self.db_path.name}") 