"""
Data Analyst Agent for SMITE 2 Combat Log Agent.

This module implements the Data Analyst Agent responsible for:
1. Analyzing query results from the database
2. Generating statistical insights and trends
3. Identifying key patterns in the data
4. Preparing analytical summaries for visualization

The agent is integrated with the DataAnalystGuardrail to ensure
analytical accuracy and factual correctness.
"""

import os
import logging
import json
import asyncio
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

from agents import Agent, GuardrailFunctionOutput, output_guardrail
from smite2_agent.guardrails import DataAnalystGuardrail, DataAnalystOutput
from smite2_agent.tools.pandasai_tools import run_pandasai_prompt, load_dataframe_from_db
from smite2_agent.pipeline.base.data_package import DataPackage

# Set up logging
logger = logging.getLogger(__name__)

class DataAnalystAgent:
    """
    Data Analyst Agent that analyzes query results and generates insights.
    
    This agent is responsible for examining data returned by the Data Engineer Agent,
    performing statistical analysis, identifying trends, and preparing analytical
    summaries for visualization and response composition.
    """
    
    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.2,
        strict_mode: bool = False
    ):
        """
        Initialize a new Data Analyst Agent.
        
        Args:
            model: The LLM model to use (default: gpt-4o)
            temperature: Model temperature for generation (default: 0.2)
            strict_mode: Whether to use strict mode for guardrails (default: False)
        """
        self.model = model
        self.temperature = temperature
        self.strict_mode = strict_mode
        
        # Create the guardrail
        self.guardrail = DataAnalystGuardrail(
            strict_mode=strict_mode
        )
        
        # Create agent instructions
        self.instructions = self._build_agent_instructions()
        
        # Initialize the OpenAI agent
        self.agent = self._create_agent()
        
        logger.info(f"Initialized DataAnalystAgent with model: {self.model}")
    
    def _build_agent_instructions(self) -> str:
        """
        Build the instruction prompt for the Data Analyst Agent.
        
        Returns:
            Instruction string for the agent
        """
        instructions = """
        You are a Data Analyst Agent for the SMITE 2 Combat Log Agent.
        Your primary responsibility is to analyze query results, identify trends,
        and generate statistical insights about combat data.

        When analyzing data, follow these steps:
        1. Review the query results carefully
        2. Identify key patterns, outliers, and relationships in the data
        3. Perform statistical analysis to quantify findings
        4. Generate clear and concise insights based on the data
        5. Prepare summary analysis for visualization and reporting
        
        ANALYSIS GUIDELINES:
        - Focus on data-driven insights only - never invent information
        - Identify player performance patterns (damage, healing, deaths)
        - Analyze ability effectiveness and usage patterns
        - Look for statistical correlations and relationships
        - Quantify findings with specific metrics when possible
        - Identify the most significant/meaningful insights first
        
        IMPORTANT:
        - Never make up statistics that aren't supported by the data
        - If data is insufficient for a conclusive insight, acknowledge limitations
        - Be precise with numbers and player names from the data
        - Always tie insights back to specific data points
        - Format numerical values clearly and consistently
        
        Your output will be structured as a DataAnalystOutput with the following:
        - insights: List of key insights discovered in the data
        - trends: Identified patterns or trends over time
        - statistics: Key statistical measures and calculations
        - findings: Overall interpretation and summary of the analysis
        - suggestions: Recommendations for further analysis or visualization
        """
        
        return instructions
    
    def _create_agent(self) -> Agent:
        """
        Create an OpenAI Agent instance with the necessary tools.
        
        Returns:
            Configured Agent instance
        """
        # Create the function tools
        tools = [
            self._analyze_data,
            self._calculate_statistics,
            self._identify_trends
        ]
        
        # Create the agent - don't pass strict_mode as it's not supported
        agent = Agent(
            name="DataAnalystAgent",
            instructions=self.instructions,
            tools=tools,
            output_type=DataAnalystOutput,
            model=self.model,
            model_settings={"temperature": self.temperature}
        )
        
        return agent
    
    async def _analyze_data(self, data: List[Dict[str, Any]], analysis_goal: str) -> Dict[str, Any]:
        """
        Tool for analyzing data with a specific goal in mind.
        
        Args:
            data: List of data points to analyze
            analysis_goal: What you want to analyze in the data
            
        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Analyzing data for goal: {analysis_goal}")
        
        try:
            # Basic validation
            if not data or not isinstance(data, list):
                return {
                    "success": False,
                    "error": "Invalid data format or empty data"
                }
            
            # Extract column names
            columns = list(data[0].keys()) if data else []
            
            # Count rows
            row_count = len(data)
            
            # Simple statistics for numeric columns
            stats = {}
            for col in columns:
                # Check if column has numeric values
                numeric_values = []
                for row in data:
                    if col in row and isinstance(row[col], (int, float)):
                        numeric_values.append(row[col])
                
                if numeric_values:
                    stats[col] = {
                        "min": min(numeric_values),
                        "max": max(numeric_values),
                        "avg": sum(numeric_values) / len(numeric_values),
                        "count": len(numeric_values)
                    }
            
            return {
                "success": True,
                "row_count": row_count,
                "columns": columns,
                "statistics": stats,
                "analysis_goal": analysis_goal
            }
            
        except Exception as e:
            logger.error(f"Error analyzing data: {str(e)}")
            return {
                "success": False,
                "error": f"Analysis error: {str(e)}"
            }
    
    async def _calculate_statistics(self, data: List[Dict[str, Any]], columns: List[str]) -> Dict[str, Any]:
        """
        Tool for calculating statistics on specific columns.
        
        Args:
            data: List of data points
            columns: Columns to calculate statistics for
            
        Returns:
            Dictionary with statistical calculations
        """
        logger.info(f"Calculating statistics for columns: {columns}")
        
        try:
            # Basic validation
            if not data or not isinstance(data, list):
                return {
                    "success": False,
                    "error": "Invalid data format or empty data"
                }
            
            # Calculate statistics for each column
            stats = {}
            for col in columns:
                if col not in data[0]:
                    stats[col] = {"error": f"Column '{col}' not found in data"}
                    continue
                
                # Extract values for this column
                values = []
                for row in data:
                    if col in row and isinstance(row[col], (int, float)):
                        values.append(row[col])
                
                if not values:
                    stats[col] = {"error": f"No numeric values found in column '{col}'"}
                    continue
                
                # Calculate statistics
                sorted_values = sorted(values)
                stats[col] = {
                    "min": min(values),
                    "max": max(values),
                    "sum": sum(values),
                    "avg": sum(values) / len(values),
                    "median": sorted_values[len(sorted_values) // 2],
                    "count": len(values)
                }
                
                # Calculate standard deviation
                mean = stats[col]["avg"]
                sum_squared_diff = sum((x - mean) ** 2 for x in values)
                if len(values) > 1:
                    stats[col]["std_dev"] = (sum_squared_diff / (len(values) - 1)) ** 0.5
                else:
                    stats[col]["std_dev"] = 0
            
            return {
                "success": True,
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"Error calculating statistics: {str(e)}")
            return {
                "success": False,
                "error": f"Statistics error: {str(e)}"
            }
    
    async def _identify_trends(self, data: List[Dict[str, Any]], time_column: Optional[str] = None) -> Dict[str, Any]:
        """
        Tool for identifying trends in data, optionally over time.
        
        Args:
            data: List of data points
            time_column: Optional column name containing time or sequential data
            
        Returns:
            Dictionary with identified trends
        """
        logger.info(f"Identifying trends in data")
        
        try:
            # Basic validation
            if not data or not isinstance(data, list):
                return {
                    "success": False,
                    "error": "Invalid data format or empty data"
                }
            
            # If time column specified, sort data by that column
            if time_column and time_column in data[0]:
                try:
                    sorted_data = sorted(data, key=lambda x: x.get(time_column, 0))
                except Exception as e:
                    logger.warning(f"Failed to sort by {time_column}: {str(e)}")
                    sorted_data = data
            else:
                sorted_data = data
            
            # Simple trend identification for numeric columns
            trends = {}
            columns = list(data[0].keys())
            
            for col in columns:
                # Skip non-numeric columns and the time column
                if col == time_column:
                    continue
                
                # Check if column has numeric values
                numeric_values = []
                for row in sorted_data:
                    if col in row and isinstance(row[col], (int, float)):
                        numeric_values.append(row[col])
                
                if len(numeric_values) <= 1:
                    continue
                
                # Calculate simple trend (increasing, decreasing, fluctuating)
                increases = 0
                decreases = 0
                for i in range(1, len(numeric_values)):
                    if numeric_values[i] > numeric_values[i-1]:
                        increases += 1
                    elif numeric_values[i] < numeric_values[i-1]:
                        decreases += 1
                
                # Determine trend direction
                if increases > decreases * 2:
                    trend = "strongly increasing"
                elif increases > decreases:
                    trend = "slightly increasing"
                elif decreases > increases * 2:
                    trend = "strongly decreasing"
                elif decreases > increases:
                    trend = "slightly decreasing"
                else:
                    trend = "fluctuating"
                
                # Calculate trend metrics
                first_value = numeric_values[0]
                last_value = numeric_values[-1]
                percent_change = ((last_value - first_value) / first_value * 100) if first_value != 0 else float('inf')
                
                trends[col] = {
                    "trend": trend,
                    "first_value": first_value,
                    "last_value": last_value,
                    "change": last_value - first_value,
                    "percent_change": percent_change
                }
            
            return {
                "success": True,
                "trends": trends,
                "time_column": time_column
            }
            
        except Exception as e:
            logger.error(f"Error identifying trends: {str(e)}")
            return {
                "success": False,
                "error": f"Trend analysis error: {str(e)}"
            }
    
    async def process_data(self, data_package: DataPackage) -> DataPackage:
        """
        Process query results and generate analytical insights.
        
        Args:
            data_package: DataPackage containing query results
            
        Returns:
            Updated DataPackage with analysis results
        """
        logger.info(f"Processing data package for analysis")
        
        # Check if we have query results to analyze
        query_results = data_package.get_query_results()
        if not query_results:
            logger.warning("No query results found in data package")
            data_package.add_error({
                "agent": "DataAnalystAgent",
                "error": "No query results found for analysis",
                "error_type": "missing_data"
            })
            return data_package
        
        # Get the original user query and database path
        user_query = data_package.get_user_query()
        db_path = data_package.get_db_path()
        if not db_path:
            logger.warning("No database path found in data package")
            data_package.add_error({
                "agent": "DataAnalystAgent",
                "error": "Database path not found",
                "error_type": "missing_database_path"
            })
            return data_package
        
        try:
            # Get the latest SQL query from the data package
            last_query_result = list(query_results.values())[-1]
            sql_query = last_query_result.get('sql', '')
            
            if not sql_query:
                logger.warning("No SQL query found in data package")
                data_package.add_error({
                    "agent": "DataAnalystAgent",
                    "error": "SQL query not found in query results",
                    "error_type": "missing_query"
                })
                return data_package
            
            # Get the data directly
            data = last_query_result.get('data', [])
            if not data:
                logger.warning("No data found in query results")
                data_package.add_error({
                    "agent": "DataAnalystAgent",
                    "error": "No data found in query results",
                    "error_type": "empty_data"
                })
                return data_package
            
            # Create a simple prompt for analysis
            analysis_prompt = f"""
            Analyze this data to answer the user's question: "{user_query}"
            
            The data comes from executing this SQL query:
            {sql_query}
            
            The data contains {len(data)} rows.
            First few rows: {str(data[:3])}
            
            IMPORTANT INSTRUCTIONS:
            1. Focus on computing these factual elements IN THIS EXACT ORDER:
               a. EXACT NUMERICAL VALUES - Always extract precise numbers (never omit these)
               b. RANKINGS - List at least top 3 entries with their exact values
               c. COMPARISONS - Calculate difference and percentage difference between 1st, 2nd, 3rd places
               d. AGGREGATES - Calculate sum, average, median, min, max for relevant columns
               e. DISTRIBUTION - Provide percentiles or counts in ranges when helpful
            
            2. Format numerical results with EXPLICIT LABELS to make them clear:
               For example: "Kills: 15" not just "15"
               For ratios: "K/D Ratio: 3.2" not just "3.2"
            
            3. NEVER omit the exact numerical values - these are REQUIRED
               If you see a "count" or "sum" type column, always provide the exact value
            
            4. Include ONLY observations directly supported by the data
               
            5. Present key statistics in a structured way
            
            YOUR GOAL: Provide ALL relevant numerical facts from the data. 
            BE EXTREMELY THOROUGH in extracting exact values and statistics.
            """
            
            # Use direct API call instead of the agent
            from openai import OpenAI
            client = OpenAI()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data analyst that provides insights based on query results."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=self.temperature
            )
            
            # Extract the analysis from the response
            analysis_result = response.choices[0].message.content.strip()
            
            # Add simple analysis results to the data package
            data_package.add_analysis_results({
                "insights": analysis_result,
                "findings": analysis_result,
                "raw_analysis": analysis_result
            })
            
            return data_package
            
        except Exception as e:
            # Handle errors
            logger.error(f"Error in DataAnalystAgent: {str(e)}")
            
            # Add error to data package
            data_package.add_error({
                "agent": "DataAnalystAgent",
                "error": str(e),
                "error_type": "exception"
            })
            
            return data_package 