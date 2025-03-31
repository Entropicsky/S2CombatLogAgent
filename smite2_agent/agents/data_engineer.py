"""
Data Engineer Agent for SMITE 2 Combat Log Agent.

This module implements the Data Engineer Agent responsible for:
1. Understanding the database schema
2. Creating SQL queries based on user questions
3. Executing queries against the database
4. Validating query results for accuracy

The agent is integrated with the DataEngineerGuardrail to ensure
SQL validity and data accuracy.
"""

import os
import logging
import json
import asyncio
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

from agents import Agent, GuardrailFunctionOutput, output_guardrail
from smite2_agent.guardrails import DataEngineerGuardrail, DataEngineerOutput
from smite2_agent.tools.sql_tools import get_table_schema, run_sql_query
from smite2_agent.pipeline.base.data_package import DataPackage

# Set up logging
logger = logging.getLogger(__name__)

class DataEngineerAgent:
    """
    Data Engineer Agent that handles SQL creation and database queries.
    
    This agent is responsible for translating natural language questions
    into SQL queries, executing them against the database, and ensuring
    the results are accurate and useful for downstream agents.
    """
    
    def __init__(
        self,
        db_path: Union[str, Path],
        model: str = "gpt-4o",
        temperature: float = 0.2,
        strict_mode: bool = False,
        schema_cache_path: Optional[Path] = None
    ):
        """
        Initialize a new Data Engineer Agent.
        
        Args:
            db_path: Path to the SQLite database file
            model: The LLM model to use (default: gpt-4o)
            temperature: Model temperature for generation (default: 0.2)
            strict_mode: Whether to use strict mode for guardrails (default: False)
            schema_cache_path: Optional path to cache the database schema
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
        
        self.model = model
        self.temperature = temperature
        self.strict_mode = strict_mode
        self.schema_cache_path = schema_cache_path
        
        # Cache for database schema
        self._schema_cache = None
        
        # Create the guardrail
        self.guardrail = DataEngineerGuardrail(
            strict_mode=strict_mode
        )
        
        # Create agent instructions
        self.instructions = self._build_agent_instructions()
        
        # Initialize the OpenAI agent
        self.agent = self._create_agent()
        
        logger.info(f"Initialized DataEngineerAgent with database: {self.db_path.name}")
    
    def _build_agent_instructions(self) -> str:
        """
        Build the instruction prompt for the Data Engineer Agent.
        
        Returns:
            Instruction string for the agent
        """
        # Load the database schema
        schema = self._get_db_schema()
        schema_description = json.dumps(schema, indent=2)
        
        # Create the instruction prompt
        instructions = f"""
        You are a Data Engineer Agent for the SMITE 2 Combat Log Agent.
        Your primary responsibility is to translate user questions about combat logs
        into SQL queries, execute them, and ensure the results are accurate and useful.

        You have access to a SQLite database with the following schema:
        ```
        {schema_description}
        ```
        
        When responding to requests, follow these steps:
        1. Analyze the question to understand what data is being requested
        2. Identify the relevant tables and columns from the schema
        3. Create a valid SQL query to retrieve the requested information
        4. Execute the query against the database
        5. Return the results in a structured format
        
        SQL RULES:
        - Use only tables and columns that exist in the schema
        - Write clear, efficient queries with appropriate JOINs and WHERE clauses
        - Use aliases for clarity when joining multiple tables
        - Limit to 100 rows by default unless specified otherwise
        - Use LIMIT for safe execution when exploring data
        - Include comments in your SQL to explain complex parts or reasoning
        
        IMPORTANT:
        - Never make up information that isn't in the data
        - If a query returns no results, don't invent data - report that no results were found
        - Always double-check your SQL syntax before execution
        - Provide error explanations if a query fails
        
        Your output will be structured as a DataEngineerOutput with the following:
        - sql_query: The SQL query you created
        - explanation: Brief explanation of the query logic
        - query_result: The result of executing the query
        - error: Any error encountered during execution (if applicable)
        """
        
        return instructions
    
    def _get_db_schema(self) -> Dict[str, Any]:
        """
        Get the database schema.
        
        Returns:
            Dictionary with schema information
        """
        try:
            # Check if schema cache exists
            if self.schema_cache_path and self.schema_cache_path.exists():
                logger.info(f"Using cached schema from {self.schema_cache_path}")
                with open(self.schema_cache_path, 'r') as f:
                    return json.load(f)
            
            # Otherwise, get schema from database
            logger.info(f"Getting schema from database: {self.db_path}")
            schema = get_table_schema(self.db_path)
            
            # Cache schema if requested
            if self.schema_cache_path:
                logger.info(f"Caching schema to {self.schema_cache_path}")
                with open(self.schema_cache_path, 'w') as f:
                    json.dump(schema, f, indent=2)
            
            return schema
                
        except Exception as e:
            logger.error(f"Failed to fetch database schema: {str(e)}")
            raise
            
    def _format_schema_for_prompt(self, schema: Dict[str, Any]) -> str:
        """
        Format the database schema for inclusion in a prompt.
        
        Args:
            schema: Database schema dictionary
            
        Returns:
            Formatted schema string
        """
        formatted_schema = []
        
        for table_name, table_data in schema.items():
            # Start with table name
            table_info = [f"Table: {table_name}"]
            
            # Add columns
            columns = []
            for column in table_data.get('columns', []):
                column_str = f"{column['name']} ({column['type']})"
                if column.get('pk'):
                    column_str += " PRIMARY KEY"
                if column.get('notnull'):
                    column_str += " NOT NULL"
                columns.append(column_str)
            
            table_info.append("Columns: " + ", ".join(columns))
            
            # Add foreign keys if available
            foreign_keys = table_data.get('foreign_keys', [])
            if foreign_keys:
                fk_lines = []
                for fk in foreign_keys:
                    fk_lines.append(f"{fk['from']} -> {fk['table']}.{fk['to']}")
                table_info.append("Foreign Keys: " + ", ".join(fk_lines))
            
            # Add sample data if available (limited to first 3 rows)
            sample_data = table_data.get('sample_data', [])
            if sample_data:
                sample_rows = []
                for i, row in enumerate(sample_data[:3]):
                    row_str = ", ".join([f"{k}: {v}" for k, v in row.items()])
                    sample_rows.append(f"Row {i+1}: {{{row_str}}}")
                table_info.append("Sample Data: " + "; ".join(sample_rows))
            
            # Add table to formatted schema
            formatted_schema.append("\n".join(table_info))
        
        return "\n\n".join(formatted_schema)
    
    def _create_agent(self) -> Agent:
        """
        Create an OpenAI Agent instance with the necessary tools.
        
        Returns:
            Configured Agent instance
        """
        # Create the function tools
        tools = [
            self._run_sql_query
        ]
        
        # Create the agent - don't pass strict_mode as it's not supported
        agent = Agent(
            name="DataEngineerAgent",
            instructions=self.instructions,
            tools=tools,
            output_type=DataEngineerOutput,
            model=self.model,
            model_settings={"temperature": self.temperature}
        )
        
        return agent
    
    async def _run_sql_query(self, query: str) -> Dict[str, Any]:
        """
        Tool for executing SQL queries against the database.
        
        Args:
            query: SQL query to execute
            
        Returns:
            Dictionary with query results
        """
        logger.info(f"Executing SQL query: {query}")
        result = run_sql_query(query, self.db_path, format_as="dict")
        
        if result["success"]:
            logger.info(f"Query successful: {result['row_count']} rows returned")
        else:
            logger.error(f"Query failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    async def _fetch_dimensional_data(self, schema: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Proactively fetch valid values for key dimensional data to help with SQL generation.
        
        Args:
            schema: The database schema
            
        Returns:
            Dictionary mapping dimension names to lists of valid values
        """
        logger.info("Fetching dimensional data to aid SQL generation")
        dimensions = {}
        
        # Define key dimensions to fetch
        dimension_queries = {
            "player_names": "SELECT DISTINCT player_name FROM players ORDER BY player_name",
            "entity_names": "SELECT DISTINCT entity_name FROM timeline_events ORDER BY entity_name",
            "ability_names": "SELECT DISTINCT ability_name FROM abilities ORDER BY ability_name",
            "item_names": "SELECT DISTINCT item_name FROM items ORDER BY item_name",
            "event_types": "SELECT DISTINCT event_type FROM combat_events ORDER BY event_type",
            "objective_types": "SELECT DISTINCT event_type FROM timeline_events WHERE event_type LIKE '%Objective%' OR event_type LIKE '%Kill%' ORDER BY event_type",
            "god_names": "SELECT DISTINCT god_name FROM players ORDER BY god_name"
        }
        
        # Execute each query and store results
        for dimension, query in dimension_queries.items():
            try:
                # Only attempt if table exists in schema
                if dimension == "player_names" and "players" not in schema:
                    continue
                if dimension == "ability_names" and "abilities" not in schema:
                    continue
                if dimension == "entity_names" and "timeline_events" not in schema:
                    continue
                if dimension == "item_names" and "items" not in schema:
                    continue
                if dimension == "event_types" and "combat_events" not in schema:
                    continue
                if dimension == "objective_types" and "timeline_events" not in schema:
                    continue
                if dimension == "god_names" and "players" not in schema:
                    continue
                
                result = run_sql_query(query, self.db_path)
                if result["success"]:
                    # Extract values from the result
                    values = []
                    for row in result["data"]:
                        # Get the first column value regardless of column name
                        values.append(list(row.values())[0])
                        
                    dimensions[dimension] = values
                    logger.info(f"Fetched {len(values)} values for dimension {dimension}")
                else:
                    logger.warning(f"Failed to fetch values for dimension {dimension}: {result.get('error')}")
            except Exception as e:
                logger.warning(f"Error fetching dimension {dimension}: {str(e)}")
        
        return dimensions
        
    async def _analyze_domain_concepts(self, query: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        First stage: Analyze the query to identify domain-specific concepts and 
        how they map to the database schema.
        
        Args:
            query: The user's query
            schema: The database schema
            
        Returns:
            Dictionary with domain concept analysis
        """
        logger.info(f"Analyzing domain concepts in query: {query}")
        
        # Fetch valid dimensional data to aid analysis
        dimensional_data = await self._fetch_dimensional_data(schema)
        
        # Format dimensional data as a string for the prompt
        dimension_str = ""
        for dimension, values in dimensional_data.items():
            # Limit to 50 values to avoid excessively long prompts
            sample_values = values[:50] if len(values) > 50 else values
            dimension_str += f"\n{dimension} ({len(values)} total): {', '.join(sample_values)}"
            if len(values) > 50:
                dimension_str += f" (plus {len(values) - 50} more...)"
        
        domain_analysis_prompt = f"""
        Analyze this query to identify SMITE-specific concepts and how they map to database schema:
        
        Query: {query}
        
        Database Schema:
        {self._format_schema_for_prompt(schema)}
        
        Valid Dimensional Values:
        {dimension_str}
        
        INSTRUCTIONS:
        1. Identify game-specific terms in the query (objectives, NPCs, event types, etc.)
        2. Map these terms to their EXACT representation in the database
        3. Check for special concepts like:
           - "final X" → requires finding MAX(timestamp)
           - "initial X" → requires finding MIN(timestamp)
           - "most common X" → requires COUNT() and GROUP BY
           - "highest/lowest X" → requires sorting with ORDER BY
        
        For each entity or concept mentioned:
        - Find the EXACT match in the dimensional values provided
        - Use fuzzy matching only if necessary (e.g., "Fire Giant" might be "FireGiant" in the database)
        - If a player or entity name is mentioned, verify it exists in the valid values
        - Always prioritize exact database terminology over natural language
        
        Return analysis as detailed JSON with:
        - identified_concepts: List of game terms found
        - database_mappings: How each maps to exact database values/columns
        - required_tables: List of tables needed
        - special_logic: Any special handling required (timestamps, aggregations, etc.)
        """
        
        try:
            # Use direct API call 
            from openai import OpenAI
            client = OpenAI()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a database expert that specializes in mapping domain concepts to SQL databases."},
                    {"role": "user", "content": domain_analysis_prompt}
                ],
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            
            analysis_json = response.choices[0].message.content
            analysis = json.loads(analysis_json)
            
            # Enhance the analysis with the dimensional data
            analysis["dimensional_data"] = {
                k: f"{len(v)} values fetched" for k, v in dimensional_data.items()
            }
            
            logger.info(f"Domain concept analysis completed: {json.dumps(analysis, indent=2)}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing domain concepts: {str(e)}")
            # Return basic structure if analysis fails
            return {
                "identified_concepts": [],
                "database_mappings": {},
                "required_tables": [],
                "special_logic": {}
            }
    
    async def _generate_sql_with_domain_knowledge(self, query: str, schema: Dict[str, Any], domain_analysis: Dict[str, Any]) -> str:
        """
        Second stage: Generate SQL using the domain concept analysis.
        
        Args:
            query: The user's query
            schema: The database schema
            domain_analysis: Results from domain concept analysis
            
        Returns:
            SQL query string
        """
        logger.info(f"Generating SQL with domain knowledge for query: {query}")
        
        # Create prompts with verification checks for entity values
        verification_checks = []
        
        if "database_mappings" in domain_analysis:
            for concept, mapping in domain_analysis.get("database_mappings", {}).items():
                # Extract any specific entity values that were identified
                if isinstance(mapping, dict):
                    # If a specific entity value was matched to a database value
                    if "exact_value" in mapping:
                        verification_checks.append(
                            f"- The concept '{concept}' maps exactly to '{mapping['exact_value']}' in the database"
                        )
                    # If the mapping includes a "values" field with potential matches
                    elif "values" in mapping and isinstance(mapping["values"], list) and mapping["values"]:
                        verification_checks.append(
                            f"- The concept '{concept}' should use one of these exact values: {', '.join(mapping['values'])}"
                        )
                    # If a table and column were specified but no exact value
                    elif "table" in mapping and "columns" in mapping:
                        verification_checks.append(
                            f"- The concept '{concept}' should be queried in table '{mapping['table']}', column(s) {mapping['columns']}"
                        )
                        
        verification_str = "\n".join(verification_checks) if verification_checks else "No specific entity value verifications required."
        
        sql_generation_prompt = f"""
        Generate SQL for this question using the domain analysis results:
        
        Query: {query}
        
        Domain Analysis:
        {json.dumps(domain_analysis, indent=2)}
        
        Database Schema:
        {self._format_schema_for_prompt(schema)}
        
        Entity Value Verifications:
        {verification_str}
        
        IMPORTANT GUIDELINES:
        1. Generate ONLY a single SELECT query (no CREATE, UPDATE, etc.)
        2. Use EXACT database terms identified in the domain analysis
        3. Include special logic identified in the analysis (e.g., MAX(timestamp) for "final")
        4. Double-check that all column names exist in the schema
        5. Use the required_tables from the analysis
        6. Include appropriate JOINs between related tables if needed
        7. Format the response to be clear and readable for humans
        8. When using entity values (player names, ability names, etc.) use the EXACT values from the database
        9. Always compare entity values using the correct case sensitivity
        
        Return ONLY the SQL query, nothing else.
        """
        
        try:
            # Use direct API call
            from openai import OpenAI
            client = OpenAI()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a SQL expert that generates precise SQL queries."},
                    {"role": "user", "content": sql_generation_prompt}
                ],
                temperature=0.2
            )
            
            sql_query = response.choices[0].message.content.strip()
            
            # Remove SQL code block markers if present
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            
            logger.info(f"Generated SQL query with domain knowledge: {sql_query}")
            return sql_query
            
        except Exception as e:
            logger.error(f"Error generating SQL with domain knowledge: {str(e)}")
            raise
    
    async def process_question(self, data_package: DataPackage) -> DataPackage:
        """
        Process a question by executing SQL queries suggested by QueryAnalystAgent.
        
        Args:
            data_package: The input DataPackage containing the query and query analysis
            
        Returns:
            Updated DataPackage with query results
        """
        query = data_package.get_user_query()
        logger.info(f"Processing question with enhanced approach: {query}")
        
        try:
            # Mark the start of processing
            data_package.start_processing("data_engineer", "DataEngineerAgent")
            
            # Get the database schema
            logger.info(f"Getting schema from database: {self.db_path}")
            schema = get_table_schema(self.db_path)
            
            # Check if the data package already contains SQL query suggestions from QueryAnalystAgent
            package_data = data_package.to_dict()
            query_analysis = package_data.get("query_analysis", {})
            has_sql_suggestions = query_analysis and "sql_suggestion" in query_analysis and query_analysis["sql_suggestion"]
            needs_multiple_queries = query_analysis.get("needs_multiple_queries", False)
            
            if has_sql_suggestions and needs_multiple_queries:
                # Use the SQL queries suggested by the QueryAnalystAgent
                return await self._execute_multiple_queries(data_package, query_analysis["sql_suggestion"])
            elif has_sql_suggestions:
                # Use the single SQL query suggested by the QueryAnalystAgent
                sql_suggestion = query_analysis["sql_suggestion"][0]
                sql_query = sql_suggestion["query"]
                purpose = sql_suggestion["purpose"]
                
                logger.info(f"Using SQL query suggested by QueryAnalystAgent: {purpose}")
                logger.info(f"SQL: {sql_query}")
                
                # Track query execution time
                query_start_time = datetime.now()
                
                # Execute the SQL query
                query_result = run_sql_query(sql_query, self.db_path)
                
                # Calculate execution time
                query_end_time = datetime.now()
                execution_time_ms = round((query_end_time - query_start_time).total_seconds() * 1000, 2)
                
                # Check if the query was successful
                if not query_result.get("success", False):
                    error_msg = query_result.get("error", "Unknown error")
                    logger.error(f"SQL query execution failed: {error_msg}")
                    
                    # Add error to data package
                    data_package.add_error({
                        "agent": "DataEngineerAgent",
                        "error": f"SQL execution error: {error_msg}",
                        "error_type": "sql_execution_error"
                    })
                    
                    # Mark the end of processing with failure
                    data_package.end_processing(success=False)
                    return data_package
                
                # Add query result to data package with execution time
                data_package.add_query_result(
                    query_id="query1",
                    sql=sql_query,
                    data=query_result.get("data", []),
                    raw_result=query_result,
                    execution_time_ms=execution_time_ms
                )
                
                # Mark the end of processing with success
                data_package.end_processing(success=True)
                return data_package
            else:
                # Perform regular processing with domain analysis and SQL generation
                
                # Get domain analysis
                domain_analysis = data_package.get_domain_analysis()
                if not domain_analysis:
                    # STAGE 1: Fetch dimensional data
                    dimensional_data = await self._fetch_dimensional_data(schema)
                    
                    # STAGE 2: Analyze domain concepts in the query
                    logger.info(f"Analyzing domain concepts in query: {query}")
                    domain_analysis = await self._analyze_domain_concepts(query, dimensional_data)
                    
                    # Add domain analysis to the data package for later use
                    data_package.add_domain_analysis(domain_analysis)
                
                # STAGE 3: Generate SQL using the domain concept analysis
                logger.info(f"Generating SQL with domain knowledge for query: {query}")
                sql_query = await self._generate_sql_with_domain_knowledge(query, domain_analysis)
                
                # Log the generated SQL query
                logger.info(f"Generated SQL query: {sql_query}")
                
                # Track query execution time
                query_start_time = datetime.now()
                
                # Execute the SQL query
                query_result = run_sql_query(sql_query, self.db_path)
                
                # Calculate execution time
                query_end_time = datetime.now()
                execution_time_ms = round((query_end_time - query_start_time).total_seconds() * 1000, 2)
                
                # Check if the query was successful
                if not query_result.get("success", False):
                    error_msg = query_result.get("error", "Unknown error")
                    logger.error(f"SQL query execution failed: {error_msg}")
                    
                    # Add error to data package
                    data_package.add_error({
                        "agent": "DataEngineerAgent",
                        "error": f"SQL execution error: {error_msg}",
                        "error_type": "sql_execution_error"
                    })
                    
                    # Mark the end of processing with failure
                    data_package.end_processing(success=False)
                    return data_package
                
                # Add query result to data package with execution time
                data_package.add_query_result(
                    query_id="query1", 
                    sql=sql_query, 
                    data=query_result.get("data", []),
                    raw_result=query_result,
                    execution_time_ms=execution_time_ms
                )
                
                # Mark the end of processing with success
                data_package.end_processing(success=True)
                return data_package
            
        except Exception as e:
            logger.error(f"Error in DataEngineerAgent: {str(e)}")
            
            # Add error to data package
            data_package.add_error({
                "agent": "DataEngineerAgent",
                "error": str(e),
                "error_type": "exception"
            })
            
            # Ensure we mark the end of processing even if there's an error
            data_package.end_processing(success=False)
            return data_package

    async def _find_closest_entity_value(self, value: str, dimension: str, dimensional_data: Dict[str, List[str]]) -> Optional[str]:
        """
        Find the closest matching entity value in the dimensional data.
        
        Args:
            value: The value to look up
            dimension: The dimension to search in
            dimensional_data: Dictionary of dimensional data
            
        Returns:
            The closest matching value or None if not found
        """
        if dimension not in dimensional_data or not dimensional_data[dimension]:
            return None
            
        # First try exact match (case insensitive)
        value_lower = value.lower()
        for actual_value in dimensional_data[dimension]:
            if actual_value.lower() == value_lower:
                return actual_value
                
        # Then try contains match (e.g. "Fire Giant" might match "FireGiant")
        # Remove spaces and compare
        value_nospace = value_lower.replace(" ", "")
        for actual_value in dimensional_data[dimension]:
            actual_nospace = actual_value.lower().replace(" ", "")
            if value_nospace == actual_nospace:
                return actual_value
                
        # Try fuzzy matching (starts with)
        for actual_value in dimensional_data[dimension]:
            if actual_value.lower().startswith(value_lower) or value_lower.startswith(actual_value.lower()):
                return actual_value
        
        # No match found
        return None
        
    async def _refine_domain_analysis_with_exact_values(self, domain_analysis: Dict[str, Any], dimensional_data: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Refine the domain analysis with exact entity values from the dimensional data.
        
        Args:
            domain_analysis: The domain analysis
            dimensional_data: Dictionary of dimensional data
            
        Returns:
            Refined domain analysis
        """
        # Skip if no database mappings
        if "database_mappings" not in domain_analysis:
            return domain_analysis
            
        # Track any refinements for logging
        refinements = []
        
        # Iterate over each concept and try to refine its value
        for concept, mapping in domain_analysis["database_mappings"].items():
            if not isinstance(mapping, dict):
                continue
                
            # Skip if an exact value is already specified
            if "exact_value" in mapping:
                continue
                
            # Look for natural language values that need mapping to database values
            if "natural_language_value" in mapping:
                nl_value = mapping["natural_language_value"]
                
                # Determine which dimension to look in based on the mapped table/column
                dimension = None
                if "table" in mapping:
                    table = mapping["table"]
                    if table == "players":
                        dimension = "player_names"
                    elif table == "timeline_events":
                        dimension = "entity_names"
                    elif table == "abilities":
                        dimension = "ability_names"
                    elif table == "items":
                        dimension = "item_names"
                    elif table == "combat_events" and "column" in mapping:
                        col = mapping["column"]
                        if col == "event_type":
                            dimension = "event_types"
                
                # If we determined a dimension, try to look up the exact value
                if dimension:
                    exact_value = await self._find_closest_entity_value(nl_value, dimension, dimensional_data)
                    if exact_value:
                        mapping["exact_value"] = exact_value
                        refinements.append(f"Refined '{concept}': '{nl_value}' → '{exact_value}'")
        
        # Log refinements if any
        if refinements:
            logger.info(f"Refined domain analysis with exact values: {', '.join(refinements)}")
        
        return domain_analysis 

    async def _execute_multiple_queries(self, data_package: DataPackage, sql_suggestions: List[Dict[str, Any]]) -> DataPackage:
        """
        Execute multiple SQL queries in parallel.
        
        Args:
            data_package: The data package containing the user query
            sql_suggestions: List of SQL query suggestions from QueryAnalystAgent
            
        Returns:
            Updated data package with query results
        """
        logger.info(f"Executing {len(sql_suggestions)} SQL queries in parallel")
        
        # Create a list of tasks for parallel execution
        tasks = []
        for i, suggestion in enumerate(sql_suggestions):
            query_id = f"query{i+1}"
            sql_query = suggestion["query"]
            purpose = suggestion["purpose"]
            
            logger.info(f"Preparing SQL query {query_id}: {purpose}")
            logger.info(f"SQL: {sql_query}")
            
            # Create a task to execute the query
            task = asyncio.create_task(self._execute_query(query_id, sql_query, purpose))
            tasks.append(task)
        
        # Execute all queries in parallel
        query_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process the results
        success_count = 0
        for i, result in enumerate(query_results):
            query_id = f"query{i+1}"
            
            # Check if the result is an exception
            if isinstance(result, Exception):
                logger.error(f"Query {query_id} failed with exception: {str(result)}")
                
                # Add error to data package
                data_package.add_error({
                    "agent": "DataEngineerAgent",
                    "error": f"SQL execution error for {query_id}: {str(result)}",
                    "error_type": "sql_execution_error"
                })
                continue
            
            # Check if the query was successful
            if not result.get("success", False):
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Query {query_id} execution failed: {error_msg}")
                
                # Add error to data package
                data_package.add_error({
                    "agent": "DataEngineerAgent",
                    "error": f"SQL execution error for {query_id}: {error_msg}",
                    "error_type": "sql_execution_error"
                })
                continue
            
            # Add query result to data package with purpose
            purpose = sql_suggestions[i]["purpose"]
            sql_query = sql_suggestions[i]["query"]
            
            # Use a modified version of add_query_result that includes purpose
            # Create a DTO to use with add_query_result
            data_package.add_query_result(
                query_id=query_id,
                sql=sql_query,
                data=result.get("data", []),
                raw_result=result
            )
            
            # Add purpose to the result dictionary
            package_dict = data_package.to_dict()
            if "query_results" in package_dict["data"] and query_id in package_dict["data"]["query_results"]:
                package_dict["data"]["query_results"][query_id]["purpose"] = purpose
                # Convert back to data package
                data_package = DataPackage.from_dict(package_dict)
            
            success_count += 1
        
        logger.info(f"Executed {len(sql_suggestions)} queries: {success_count} succeeded, {len(sql_suggestions) - success_count} failed")
        
        # If all queries failed, add a general error
        if success_count == 0:
            data_package.add_error({
                "agent": "DataEngineerAgent",
                "error": "All SQL queries failed to execute",
                "error_type": "all_queries_failed"
            })
        
        return data_package

    async def _execute_query(self, query_id: str, sql_query: str, purpose: str) -> Dict[str, Any]:
        """
        Execute a single SQL query.
        
        Args:
            query_id: Identifier for the query
            sql_query: SQL query to execute
            purpose: Purpose of the query
            
        Returns:
            Dictionary with query results
        """
        logger.info(f"Executing SQL query {query_id}: {purpose}")
        
        try:
            # Execute the query
            result = run_sql_query(sql_query, self.db_path)
            
            if result["success"]:
                logger.info(f"Query {query_id} successful: {result['row_count']} rows returned")
            else:
                logger.error(f"Query {query_id} failed: {result.get('error', 'Unknown error')}")
            
            # Add purpose to the result
            result["purpose"] = purpose
            
            return result
        except Exception as e:
            logger.error(f"Exception executing query {query_id}: {str(e)}")
            raise 