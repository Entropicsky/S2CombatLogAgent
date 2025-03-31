"""
Response Composer Agent for SMITE 2 Combat Log Agent.

This module implements the Response Composer Agent responsible for:
1. Combining query results and analysis into a cohesive response
2. Structuring information in a logical and user-friendly way
3. Providing comprehensive explanations and summaries
4. Ensuring the final response is factually accurate

The agent is integrated with the ResponseComposerGuardrail to ensure
factual accuracy and consistency in the final output.
"""

import os
import logging
import json
import asyncio
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from agents import Agent, GuardrailFunctionOutput, output_guardrail
from smite2_agent.guardrails import ResponseComposerGuardrail, ComposerOutput, ResponseSection
from smite2_agent.tools.chart_tools import generate_chart, chart_type_from_data
from smite2_agent.pipeline.base.data_package import DataPackage

# Set up logging
logger = logging.getLogger(__name__)

class ResponseComposerAgent:
    """
    Response Composer Agent that creates the final user response.
    
    This agent is responsible for taking query results, analysis, and 
    visualizations to create a comprehensive response that answers
    the user's original question with factual accuracy.
    """
    
    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.2,
        strict_mode: bool = False
    ):
        """
        Initialize a new Response Composer Agent.
        
        Args:
            model: The LLM model to use (default: gpt-4o)
            temperature: Model temperature for generation (default: 0.2)
            strict_mode: Whether to use strict mode for guardrails (default: False)
        """
        self.model = model
        self.temperature = temperature
        self.strict_mode = strict_mode
        
        # Create the guardrail
        self.guardrail = ResponseComposerGuardrail(
            strict_mode=strict_mode
        )
        
        # Create agent instructions
        self.instructions = self._build_agent_instructions()
        
        # Initialize the OpenAI agent
        self.agent = self._create_agent()
        
        logger.info(f"Initialized ResponseComposerAgent with model: {self.model}")
    
    def _build_agent_instructions(self) -> str:
        """
        Build the instruction prompt for the Response Composer Agent.
        
        Returns:
            Instruction string for the agent
        """
        instructions = """
        You are a Response Composer Agent for the SMITE 2 Combat Log Agent.
        Your primary responsibility is to create the final response for the user
        by combining database query results, analytical insights, and visualizations
        into a comprehensive, accurate, and user-friendly response.

        When composing responses, follow these steps:
        1. Understand the original user question to ensure you answer it completely
        2. Structure your response with clear sections for different aspects of the answer
        3. Include an executive summary that highlights key findings
        4. Reference specific data points to support your statements
        5. Include explanations that help the user understand the significance of the results
        
        COMPOSITION GUIDELINES:
        - Organize information logically with clear headings and sections
        - Prioritize the most important information first
        - Include specific numbers and metrics from the data
        - Use concise language that is easy to understand
        - Apply formatting to improve readability (markdown supported)
        - Maintain factual accuracy and consistency throughout
        
        IMPORTANT:
        - Never make up information that isn't supported by the data
        - Ensure all player names, ability names, and statistics match the source data
        - Maintain consistency between different sections of your response
        - Include all key findings from the analysis
        - If visualization results are available, reference them appropriately
        
        Your output will be structured as a ComposerOutput with the following:
        - response: The complete response text with formatting
        - sections: Individual sections of the response
        - summary: Executive summary of key findings
        - raw_data_references: References to the raw data used
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
            self._create_response_section,
            self._create_executive_summary,
            self._format_data_table
        ]
        
        # Create the agent - don't pass strict_mode as it's not supported
        agent = Agent(
            name="ResponseComposerAgent",
            instructions=self.instructions,
            tools=tools,
            output_type=ComposerOutput,
            model=self.model,
            model_settings={"temperature": self.temperature}
        )
        
        return agent
    
    async def _create_response_section(
        self, 
        title: str, 
        content: str, 
        source_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Tool for creating a response section.
        
        Args:
            title: Section title
            content: Section content
            source_data: Optional source data for the section
            
        Returns:
            Dictionary with the section information
        """
        logger.info(f"Creating response section: {title}")
        
        section = {
            "title": title,
            "content": content
        }
        
        if source_data:
            section["source_data"] = source_data
        
        return section
    
    async def _create_executive_summary(self, content: str) -> Dict[str, Any]:
        """
        Tool for creating an executive summary.
        
        Args:
            content: Summary content
            
        Returns:
            Dictionary with the summary information
        """
        logger.info(f"Creating executive summary")
        
        return {
            "summary": content
        }
    
    async def _format_data_table(self, data: List[Dict[str, Any]], title: str = "Data Table") -> Dict[str, Any]:
        """
        Tool for formatting data as a markdown table.
        
        Args:
            data: List of data points to format
            title: Optional title for the table
            
        Returns:
            Dictionary with the formatted table
        """
        logger.info(f"Formatting data table: {title}")
        
        try:
            # Basic validation
            if not data or not isinstance(data, list):
                return {
                    "success": False,
                    "error": "Invalid data format or empty data",
                    "markdown": f"# {title}\n\nNo data available."
                }
            
            # Extract column names
            columns = list(data[0].keys())
            
            # Create header row
            header = "| " + " | ".join(columns) + " |"
            separator = "| " + " | ".join(["---"] * len(columns)) + " |"
            
            # Create data rows
            rows = []
            for row in data:
                row_values = []
                for col in columns:
                    value = row.get(col, "")
                    # Format values as strings with comma for large numbers
                    if isinstance(value, (int, float)) and abs(value) >= 1000:
                        value = f"{value:,}"
                    row_values.append(str(value))
                rows.append("| " + " | ".join(row_values) + " |")
            
            # Combine into table
            table = f"## {title}\n\n" + header + "\n" + separator + "\n" + "\n".join(rows)
            
            return {
                "success": True,
                "markdown": table
            }
            
        except Exception as e:
            logger.error(f"Error formatting data table: {str(e)}")
            return {
                "success": False,
                "error": f"Table formatting error: {str(e)}",
                "markdown": f"# {title}\n\nError formatting data."
            }
    
    async def generate_response(self, data_package: DataPackage) -> DataPackage:
        """
        Generate the final response to the user's question.
        
        Args:
            data_package: DataPackage containing query results and analysis
            
        Returns:
            Updated DataPackage with final response
        """
        logger.info(f"Generating final response")
        
        # Check if we have query results
        query_results = data_package.get_query_results()
        if not query_results:
            logger.warning("No query results found in data package")
            data_package.add_error({
                "agent": "ResponseComposerAgent",
                "error": "No query results found for response composition",
                "error_type": "missing_data"
            })
            return data_package
        
        # Get analysis results if available
        analysis_results = data_package.get_analysis_results()
        
        # Get the user query
        user_query = data_package.get_user_query()
        
        try:
            # Format query results into a more accessible format for the model
            formatted_results = []
            for query_id, result in query_results.items():
                formatted_results.append({
                    "query_id": query_id,
                    "purpose": result.get("purpose", f"Query {query_id}"),
                    "sql": result.get("sql", ""),
                    "row_count": len(result.get("data", [])),
                    "data": result.get("data", [])
                })
            
            # Create a simplified prompt with ALL query result data
            prompt = f"""
            Create a factual, concise response to the user's question: "{user_query}"
            
            IMPORTANT INSTRUCTIONS:
            1. ALWAYS include ALL exact numerical values from the data and analysis:
               - For rankings: EXACT counts/values for each ranked item
               - For comparisons: ACTUAL numerical differences and percentages
               - For aggregates: PRECISE sums, averages, medians
            
            2. When answering about rankings or "who is best/most" questions:
               - ALWAYS include the top 3 with their EXACT values
               - ALWAYS show the numerical difference between 1st and 2nd place
               - ALWAYS include the total, average, and median values for context
            
            3. Format data for clarity:
               - Use lists, tables, or bullet points instead of paragraphs
               - Highlight the most important numbers visually
               - Keep the format structured and consistent
            
            4. Keep it factual and concise:
               - NO interpretations beyond what's in the data
               - NO unnecessary adjectives or marketing language
               - NO phrases like "based on the data", "analysis shows", etc.
               
            5. CRITICAL - DO NOT USE PLACEHOLDERS:
               - NEVER use placeholders like "[Ability Name]" or "[Damage Value]"
               - ALWAYS insert the actual values from the data
               - Every number or name mentioned must come directly from the query results
            
            Your response MUST include ALL relevant numerical facts, presented clearly and directly.
            NEVER omit exact values - the user needs PRECISE NUMBERS.
            """
            
            # Add complete query results data
            prompt += "\n\nCOMPLETE QUERY RESULTS:\n"
            
            for i, result in enumerate(formatted_results):
                data = result["data"]
                prompt += f"\n--- QUERY {i+1}: {result['purpose']} ---\n"
                prompt += f"SQL: {result['sql']}\n"
                prompt += f"Rows: {result['row_count']}\n\n"
                
                # Include more complete data (up to 15 rows to avoid token limits)
                if data:
                    prompt += "DATA (JSON format):\n"
                    try:
                        # Format the first 15 rows as readable JSON
                        data_sample = json.dumps(data[:15], indent=2)
                        prompt += f"{data_sample}\n"
                    except:
                        # Fallback to str representation if JSON formatting fails
                        prompt += f"{str(data[:15])}\n"
                else:
                    prompt += "No data returned\n"
            
            # Add analysis if available
            if analysis_results:
                prompt += f"\n\nANALYSIS RESULTS:\n"
                
                # Format analysis insights
                for key, value in analysis_results.items():
                    prompt += f"\n{key}: {value}\n"
            
            # Final formatting instructions
            prompt += """
            
            Format your response with these guidelines:
            1. Start with a direct answer to the question that includes specific data points
            2. Organize information in clear sections with markdown headings
            3. Use bullet points for lists of values or comparisons
            4. Include ALL relevant numerical data - numbers must be directly from the dataset
            5. Present exact player names, ability names, and statistics exactly as they appear in the data
            
            REMEMBER: DO NOT USE TEMPLATE PLACEHOLDERS - every value must be the actual data value.
            """
            
            # Use direct API call
            from openai import OpenAI
            client = OpenAI()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data analyst that creates comprehensive, accurate answers based on EXACT data values. Never use placeholders or template language - only present actual numbers and names from the data."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
            )
            
            # Get the final response
            final_response = response.choices[0].message.content.strip()
            
            # Verify the response doesn't contain placeholder patterns
            placeholder_patterns = [
                "[Ability Name]", "[Damage Value]", "[Difference Value]", 
                "[Percentage Value]", "[Average Value]", "[Count Value]"
            ]
            
            for pattern in placeholder_patterns:
                if pattern in final_response:
                    # Fix the response by injecting a warning
                    warning = "\n\n**WARNING: This response contains placeholder values. Please try a more specific query.**\n\n"
                    final_response = warning + final_response
                    break
            
            # Set the response in the data package
            data_package.set_final_output(final_response)
            
            return data_package
            
        except Exception as e:
            # Handle errors
            logger.error(f"Error in ResponseComposerAgent: {str(e)}")
            
            # Add error to data package
            data_package.add_error({
                "agent": "ResponseComposerAgent",
                "error": str(e),
                "error_type": "exception"
            })
            
            return data_package 