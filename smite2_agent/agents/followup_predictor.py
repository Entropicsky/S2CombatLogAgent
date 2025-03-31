"""
FollowUp Predictor Agent for SMITE 2 Combat Log Agent.

This module implements the FollowUp Predictor Agent responsible for:
1. Analyzing query responses to predict follow-up questions
2. Proactively answering the most likely follow-up question
3. Enhancing responses with suggested follow-up questions
4. Guiding the user toward deeper data exploration

The agent integrates with the pipeline to create a more conversational
and exploratory experience for users.
"""

import os
import logging
import json
import asyncio
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

from agents import Agent, GuardrailFunctionOutput, output_guardrail
from smite2_agent.pipeline.base.agent import BaseAgent
from smite2_agent.pipeline.base.data_package import DataPackage
from smite2_agent.agents.data_engineer import DataEngineerAgent
from smite2_agent.tools.sql_tools import get_table_schema

# Set up logging
logger = logging.getLogger(__name__)

class FollowUpPredictorAgent(BaseAgent):
    """
    FollowUp Predictor Agent that enhances responses with follow-up questions.
    
    This agent analyzes the original query and response to predict what the
    user might ask next, then enhances the response with additional information
    and suggested follow-up questions.
    """
    
    def __init__(
        self,
        name: str = "followup_predictor",
        model: str = "gpt-4o",
        temperature: float = 0.3,
        strict_mode: bool = False,
        db_path: Optional[Path] = None
    ):
        """
        Initialize a new FollowUp Predictor Agent.
        
        Args:
            name: The name of the agent
            model: The model to use
            temperature: Temperature for generation
            strict_mode: Whether to use strict mode for validation
            db_path: Optional path to the database file
        """
        self.strict_mode = strict_mode
        self.db_path = db_path
        
        # Create the instructions
        instructions = """
        You are a FollowUp Predictor Agent for the SMITE 2 Combat Log Agent.
        
        Your role is to:
        1. Analyze the user's original query and the generated response
        2. Predict the most likely follow-up questions the user might ask
        3. Proactively answer the single most likely follow-up question
        4. Include 3-4 suggested follow-up questions at the end of the response
        
        IMPORTANT GUIDELINES:
        - Suggest follow-up questions that are directly related to the original query
        - Ensure questions lead to deeper insights about the data
        - Include diverse types of questions (details, comparisons, explanations, etc.)
        - Format the enhanced response to flow naturally
        - Make clear distinctions between the original response and your enhancements
        
        ENHANCEMENT FORMAT:
        
        [Original response content]
        
        Additional Insight:
        [Proactive answer to the top follow-up question]
        
        Suggested Follow-up Questions:
        1. [Question 1]
        2. [Question 2]
        3. [Question 3]
        
        You should always aim to guide the user toward the most valuable insights
        in the data without making them explicitly ask for each piece of information.
        """
        
        # Initialize the base agent - don't pass strict_mode
        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            temperature=temperature
        )
        
        # Create a data engineer agent for executing follow-up queries if needed
        if self.db_path:
            self.data_engineer = DataEngineerAgent(
                db_path=self.db_path,
                model=model,
                temperature=0.2,
                strict_mode=strict_mode
            )
            
            # Cache the database schema
            try:
                self.db_schema = get_table_schema(self.db_path)
            except Exception as e:
                logger.warning(f"Could not load database schema: {str(e)}")
                self.db_schema = {}
        else:
            self.data_engineer = None
            self.db_schema = {}
            
        # Load SMITE domain knowledge
        self.domain_knowledge = self._load_domain_knowledge()
            
        logger.info(f"Initialized FollowUpPredictorAgent with model: {model}")
    
    def _load_domain_knowledge(self) -> Dict[str, Any]:
        """
        Load SMITE domain knowledge for better context-aware question generation.
        
        Returns:
            Dictionary with SMITE domain knowledge
        """
        return {
            "game_concepts": {
                "objectives": ["Fire Giant", "Gold Fury", "Oni Fury", "Pyromancer", "Tower", "Phoenix", "Titan"],
                "roles": ["Solo", "Jungle", "Mid", "Support", "Carry/ADC"],
                "stat_categories": ["damage", "healing", "gold", "experience", "kills", "deaths", "assists"],
                "match_phases": ["early game", "mid game", "late game", "laning phase", "team fight phase"],
                "combat_stats": ["damage dealt", "damage taken", "healing done", "crowd control time", "mitigations"],
                "player_metrics": ["KDA", "GPM (Gold Per Minute)", "damage per gold", "efficiency"],
                "item_categories": ["starter items", "core items", "situational items", "defensive items"]
            },
            "analysis_approaches": {
                "timeline_analysis": ["progression over time", "key turning points", "power spikes", "objective control"],
                "comparative_analysis": ["player vs player", "team vs team", "early vs late game", "performance vs benchmark"],
                "performance_analysis": ["effectiveness", "efficiency", "impact", "contribution"],
                "pattern_recognition": ["recurring behaviors", "successful strategies", "failure patterns"]
            },
            "exploration_patterns": {
                "zoom_in": "Examine specific details about a high-level finding",
                "zoom_out": "Understand broader context or patterns",
                "compare": "Contrast different players, periods, or metrics",
                "analyze_causes": "Understand why certain outcomes occurred",
                "find_outliers": "Identify exceptional performances or anomalies",
                "explore_correlations": "Discover relationships between different metrics"
            }
        }
    
    async def _process(self, data_package: DataPackage) -> DataPackage:
        """
        Process the data package and enhance with follow-up questions.
        
        Args:
            data_package: The input DataPackage
            
        Returns:
            The enhanced DataPackage
        """
        logger.info("Predicting follow-up questions and enhancing response")
        
        try:
            # Extract the original query and response
            original_query = data_package.get_user_query()
            response = data_package.get_response()
            
            # Skip prediction if no valid response
            if not response:
                logger.warning("No response to enhance in DataPackage")
                return data_package
            
            # Get the query results and analysis for context
            query_results = data_package.get_query_results()
            analysis_results = data_package.get_analysis_results()
            
            # Generate follow-up questions and the enhanced response
            enhanced_response, suggested_questions = await self._generate_intelligent_followups(
                original_query, 
                response, 
                query_results,
                analysis_results,
                data_package
            )
            
            # Update the data package with the enhanced response
            package_dict = data_package.to_dict()
            package_dict["final_output"] = {
                "formatted_response": enhanced_response
            }
            
            # Add the suggested follow-up questions to the data package for metadata
            if "enhancement" not in package_dict:
                package_dict["enhancement"] = {}
            
            package_dict["enhancement"]["suggested_questions"] = suggested_questions
            
            data_package = DataPackage.from_dict(package_dict)
            
            return data_package
            
        except Exception as e:
            logger.error(f"Error in FollowUpPredictorAgent: {str(e)}")
            data_package.add_error({
                "agent": "FollowUpPredictorAgent",
                "error": str(e),
                "error_type": "exception"
            })
            return data_package
    
    async def _generate_intelligent_followups(
        self,
        query: str,
        response: str,
        query_results: Dict[str, Any],
        analysis_results: Optional[Dict[str, Any]],
        data_package: DataPackage
    ) -> Tuple[str, List[str]]:
        """
        Generate intelligent follow-up questions based on query context.
        
        This method uses the LLM to directly generate contextualized follow-up
        questions based on a rich understanding of the query, data, and domain.
        
        Args:
            query: The original user query
            response: The response content
            query_results: The query results from the database
            analysis_results: The analysis results (if available)
            data_package: The full data package
            
        Returns:
            Tuple of (enhanced response, list of suggested questions)
        """
        logger.info("Generating intelligent follow-up questions")
        
        # Format actual data from query results for inclusion in the prompt
        formatted_results = []
        all_entity_names = set()
        all_ability_names = set()
        
        # Extract all entity names and ability names from the data for specificity
        for query_id, result in query_results.items():
            data = result.get("data", [])
            
            if data:
                formatted_results.append({
                    "query_id": query_id,
                    "data": data[:10]  # First 10 rows only to avoid token limits
                })
                
                # Extract entity and ability names
                for row in data:
                    # Collect player and entity names
                    for field in ['PlayerName', 'source_entity', 'target_entity', 'entity_name', 'player_name']:
                        if field in row and row[field]:
                            all_entity_names.add(str(row[field]))
                    
                    # Collect ability names
                    for field in ['AbilityName', 'ability_name', 'name']:
                        if field in row and row[field]:
                            all_ability_names.add(str(row[field]))
        
        # Create summarized versions for the prompt
        entity_names_str = ", ".join(sorted(list(all_entity_names)))
        ability_names_str = ", ".join(sorted(list(all_ability_names)))
        results_summary = self._summarize_query_results(query_results)
        
        # Create a prompt for generating follow-up questions
        prompt = f"""
        # Context for Follow-Up Question Generation
        
        ## Original User Query
        ```
        {query}
        ```
        
        ## Current Response 
        ```
        {response}
        ```
        
        ## Database Schema Summary
        ```
        {json.dumps(self._get_schema_summary(self.db_schema), indent=2)}
        ```
        
        ## Query Results Summary
        ```
        {results_summary}
        ```
        
        ## Actual Entity Names in Data
        Player/Entity Names: {entity_names_str}
        
        ## Actual Ability Names in Data
        Ability Names: {ability_names_str}
        
        ## Analysis Results
        ```
        {json.dumps(analysis_results, indent=2) if analysis_results else "No analysis results available"}
        ```
        
        ## Domain Knowledge Context
        SMITE 2 is a team-based competitive game where players choose gods with unique abilities.
        Combat logs track damage, healing, abilities used, player stats, and objective control.
        Key metrics include damage, healing, kills, gold earned, and objective control.
        
        # Your Task
        
        1. Based on the ACTUAL DATA above, generate the most valuable follow-up question that expands on the original query.
        2. Suggest 3 additional follow-up questions that would provide further valuable insights.
        
        IMPORTANT GUIDELINES:
        - Questions MUST use ACTUAL player names, ability names, and other entities from the data provided
        - Questions must reference specific quantitative values mentioned in the response
        - DO NOT use placeholder or template language like "[Ability Name]" or "[Player]" - use the actual names
        - Each question should be specific, concrete, and directly answerable from the database
        - Focus on different analytical dimensions (comparisons, explanations, details, context)
        - Questions should build on the original analysis but explore new aspects of interest
        
        # Output Format
        
        Provide a JSON response with these fields:
        - top_question: The most valuable follow-up question
        - additional_questions: Array of 3 additional follow-up questions
        """
        
        try:
            # Use OpenAI to generate follow-up questions
            from openai import OpenAI
            client = OpenAI()
            response_obj = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert SMITE 2 analyst specializing in developing specific, data-driven follow-up questions for combat log analysis. Use ACTUAL names and values from the data, never placeholders or templates."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            followup_json = response_obj.choices[0].message.content
            followups = json.loads(followup_json)
            
            # Log the generated follow-ups
            logger.info(f"Generated top follow-up question: {followups.get('top_question', 'None')}")
            
            # Validate the questions don't contain placeholder patterns
            placeholder_patterns = ["[", "]", "<", ">", "{player}", "{ability}"]
            valid_questions = []
            
            # Clean up and validate all questions
            all_questions = [followups.get('top_question', '')] + followups.get('additional_questions', [])
            for question in all_questions:
                # Check for placeholder patterns
                has_placeholder = any(pattern in question for pattern in placeholder_patterns)
                
                if not has_placeholder and question.strip():
                    valid_questions.append(question)
                else:
                    # Replace with a more specific question
                    logger.warning(f"Question contains placeholder or is empty: {question}")
            
            # Ensure we have at least one valid question
            if not valid_questions:
                valid_questions = ["What other performance metrics would be valuable to analyze from this match?"]
            
            # Process the top follow-up question through the main agent pipeline
            top_question = valid_questions[0]
            if top_question and self.db_path:
                logger.info(f"Processing top follow-up question through main pipeline: {top_question}")
                top_answer = await self._process_followup_through_pipeline(top_question, data_package)
            else:
                logger.warning("No top follow-up question or database path available")
                top_answer = "Additional information is not available."
            
            # Format the enhanced response
            enhanced_response = f"""
{response}

**Additional Insight**
*You might also want to know: {top_question}*
{top_answer}

**Suggested Follow-up Questions**
"""
            # Add up to 3 additional questions from the valid questions
            for i, question in enumerate(valid_questions[1:4], 1):
                enhanced_response += f"{i}. {question}\n"
            
            return enhanced_response, valid_questions
            
        except Exception as e:
            logger.error(f"Error generating intelligent follow-ups: {str(e)}")
            return response, []
    
    async def _process_followup_through_pipeline(self, followup_question: str, original_data_package: DataPackage) -> str:
        """
        Process a follow-up question through the main agent pipeline to get a data-driven answer.
        
        Args:
            followup_question: The follow-up question to answer
            original_data_package: The data package from the original query
            
        Returns:
            A data-driven answer to the follow-up question
        """
        try:
            logger.info(f"Processing follow-up question through pipeline: {followup_question}")
            
            # Import necessary components here to avoid circular imports
            from smite2_agent.agents.query_analyst import QueryAnalystAgent
            from smite2_agent.agents.data_analyst import DataAnalystAgent
            from smite2_agent.agents.response_composer import ResponseComposerAgent

            # Create a new data package for the follow-up question
            followup_package = DataPackage(query=followup_question)
            
            # Copy relevant context from the original data package
            original_dict = original_data_package.to_dict()
            
            # Explicitly set the database path
            followup_package.set_db_path(str(self.db_path))
            
            # Copy match context and other relevant data
            followup_dict = followup_package.to_dict()
            if "match_context" in original_dict:
                followup_dict["match_context"] = original_dict["match_context"]
            
            # Make sure the database path is set in the input context
            if "input" not in followup_dict:
                followup_dict["input"] = {}
            followup_dict["input"]["db_path"] = str(self.db_path)
            
            # Copy any other relevant metadata from the original package
            for key in ["metadata", "domain_analysis"]:
                if key in original_dict:
                    followup_dict[key] = original_dict[key]
            
            followup_package = DataPackage.from_dict(followup_dict)
            
            # Create the necessary agents
            query_analyst = QueryAnalystAgent(
                db_path=str(self.db_path),
                model=self.model,
                temperature=0.3
            )
            
            # Reuse the existing DataEngineerAgent instance or create a new one if needed
            if not self.data_engineer or self.data_engineer.db_path != self.db_path:
                data_engineer = DataEngineerAgent(
                    db_path=self.db_path,
                    model=self.model,
                    temperature=0.2
                )
            else:
                data_engineer = self.data_engineer
            
            data_analyst = DataAnalystAgent(
                model=self.model,
                temperature=0.3
            )
            
            response_composer = ResponseComposerAgent(
                model=self.model,
                temperature=0.2
            )
            
            # Explicitly log the database path to help with debugging
            logger.info(f"Processing follow-up with DB path: {self.db_path}")
            
            # Process through pipeline (skip FollowUpPredictorAgent to avoid recursion)
            # 1. Query Analysis
            followup_package = await query_analyst._process(followup_package)
            
            # 2. Data Engineering 
            followup_package = await data_engineer.process_question(followup_package)
            
            # 3. Data Analysis
            followup_package = await data_analyst.process_data(followup_package)
            
            # 4. Response Composition
            followup_package = await response_composer.generate_response(followup_package)
            
            # Get the response
            followup_response = followup_package.get_response()
            
            # Check for errors in the data package
            followup_dict = followup_package.to_dict()
            errors = followup_dict.get("errors", [])
            
            # Check for specific errors that might indicate DB issues
            db_error = False
            for error in errors:
                error_msg = error.get('error', '').lower()
                if any(term in error_msg for term in ["database", "sql", "db path", "no path"]):
                    db_error = True
                    logger.warning(f"Database error during follow-up processing: {error_msg}")
                    break
                    
            # Also check if there are no query results, which likely indicates a DB issue
            query_results = followup_dict.get("data", {}).get("query_results", {})
            no_results = not query_results or len(query_results) == 0
            
            if errors or db_error or no_results:
                error_details = "; ".join([f"{e.get('agent', 'Unknown')}: {e.get('error', 'Unknown error')}" for e in errors])
                if errors:
                    logger.warning(f"Errors occurred during follow-up processing: {error_details}")
                
                # Generate a fallback answer since we have issues
                logger.info("SQL errors detected or no query results, attempting fallback answer generation")
                return await self._generate_fallback_answer(followup_question, original_data_package)
            
            # If we got a response, use it; otherwise, use fallback
            if followup_response:
                # Extract just the answer part without headers and sections
                # Simplify the response by removing markdown headers and keeping it concise
                simplified_response = self._simplify_response_for_followup(followup_response)
                return simplified_response
            else:
                # No valid response, use fallback
                logger.info("No valid response from follow-up pipeline, using fallback")
                return await self._generate_fallback_answer(followup_question, original_data_package)
            
        except Exception as e:
            logger.error(f"Error processing follow-up through pipeline: {str(e)}")
            # Try the fallback mechanism
            try:
                logger.info("Attempting fallback answer generation after exception")
                return await self._generate_fallback_answer(followup_question, original_data_package)
            except Exception as fallback_error:
                logger.error(f"Fallback answer generation failed: {str(fallback_error)}")
                return f"I tried to answer this follow-up question but encountered a technical issue: {str(e)}"
    
    async def _generate_fallback_answer(self, followup_question: str, original_data_package: DataPackage) -> str:
        """
        Generate a fallback answer when the full pipeline processing fails.
        
        This method uses OpenAI directly to create a relevant response based on the
        original query, response, and follow-up question.
        
        Args:
            followup_question: The follow-up question to answer
            original_data_package: The data package from the original query
            
        Returns:
            A fallback answer to the follow-up question
        """
        logger.info("Generating fallback answer for follow-up question")
        
        # Extract relevant information from the original data package
        original_query = original_data_package.get_user_query()
        original_response = original_data_package.get_response()
        query_results = original_data_package.get_query_results()
        
        # Create a prompt for the fallback answer
        prompt = f"""
        # Context
        
        ## Original User Query
        ```
        {original_query}
        ```
        
        ## Original Response
        ```
        {original_response}
        ```
        
        ## Follow-up Question
        ```
        {followup_question}
        ```
        
        # Your Task
        
        Given the original query and response above, provide a concise but informative answer to the follow-up question.
        Since we couldn't query the database directly for this answer, use the information already available in the original response
        and make logical inferences based on SMITE 2 gameplay mechanics and patterns.
        
        Keep your answer factual and data-driven where possible, acknowledging limitations when speculating.
        Focus on the specific timeframe or entities mentioned in the follow-up question.
        Be concise (3-5 sentences) but comprehensive.
        """
        
        try:
            # Use OpenAI to generate a fallback answer
            from openai import OpenAI
            client = OpenAI()
            response_obj = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert SMITE 2 analyst providing helpful answers to follow-up questions about match data."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=250
            )
            
            fallback_answer = response_obj.choices[0].message.content.strip()
            logger.info(f"Generated fallback answer: {fallback_answer[:100]}...")
            
            return fallback_answer
            
        except Exception as e:
            logger.error(f"Error generating fallback answer: {str(e)}")
            return "I couldn't find specific information to answer this follow-up question based on the available data."
    
    def _simplify_response_for_followup(self, response: str) -> str:
        """
        Simplify a response to make it appropriate for inclusion as a follow-up answer.
        
        This removes excessive markdown formatting, headers, and keeps the content concise.
        
        Args:
            response: The full response to simplify
            
        Returns:
            A simplified version suitable for a follow-up answer
        """
        # Remove markdown headers
        simplified = re.sub(r'#+\s*.*?\n', '', response)
        
        # Remove section dividers
        simplified = re.sub(r'[-=*]{3,}', '', simplified)
        
        # Remove excessive newlines
        simplified = re.sub(r'\n{3,}', '\n\n', simplified)
        
        # Truncate if too long (aim for ~200 words)
        words = simplified.split()
        if len(words) > 200:
            simplified = ' '.join(words[:200]) + '...'
        
        return simplified.strip()
    
    def _summarize_query_results(self, query_results: Dict[str, Any]) -> str:
        """
        Create a summarized version of query results for inclusion in prompts.
        
        Args:
            query_results: The raw query results
            
        Returns:
            A string summarizing the key aspects of the query results
        """
        if not query_results:
            return "No query results available."
        
        summary_parts = []
        
        for query_id, result in query_results.items():
            if "data" not in result or not isinstance(result["data"], list):
                continue
                
            data = result["data"]
            row_count = len(data)
            
            # Get column names from the first row if available
            columns = list(data[0].keys()) if row_count > 0 else []
            
            # Add summary for this query result
            query_summary = f"Query {query_id}:\n"
            query_summary += f"- Row count: {row_count}\n"
            query_summary += f"- Columns: {', '.join(columns)}\n"
            
            # Add the first few rows as examples
            if row_count > 0:
                query_summary += "- Sample data:\n"
                for i, row in enumerate(data[:3]):  # First 3 rows only
                    query_summary += f"  Row {i+1}: {json.dumps(row)}\n"
                
                if row_count > 3:
                    query_summary += f"  ... and {row_count - 3} more rows\n"
            
            summary_parts.append(query_summary)
        
        return "\n".join(summary_parts)
    
    def _get_schema_summary(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a simplified summary of the database schema.
        
        Args:
            schema: The full database schema
            
        Returns:
            A simplified schema summary
        """
        if not schema:
            return {"tables": []}
            
        summary = {"tables": []}
        
        for table_name, table_data in schema.items():
            table_summary = {
                "name": table_name,
                "columns": []
            }
            
            # Add columns
            for column in table_data.get("columns", []):
                table_summary["columns"].append({
                    "name": column["name"],
                    "type": column["type"]
                })
            
            summary["tables"].append(table_summary)
        
        return summary

    def update_db_path(self, db_path: Path) -> None:
        """
        Update the database path.
        
        Args:
            db_path: New database path
        """
        self.db_path = db_path
        if self.data_engineer:
            self.data_engineer = DataEngineerAgent(
                db_path=self.db_path,
                model=self.model,
                temperature=0.2,
                strict_mode=self.strict_mode
            )
            
        # Update schema with the new database
        try:
            self.db_schema = get_table_schema(self.db_path)
        except Exception as e:
            logger.warning(f"Could not load database schema: {str(e)}")
            self.db_schema = {} 