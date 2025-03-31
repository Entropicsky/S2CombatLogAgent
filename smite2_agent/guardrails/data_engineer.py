"""
Implementation of the DataEngineerGuardrail.

This module provides a guardrail for validating Data Engineer agent outputs,
focusing on SQL query correctness and database schema understanding.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set
from pydantic import BaseModel

from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    output_guardrail
)

from smite2_agent.guardrails.base import DataFidelityGuardrail, ValidationResult

# Set up logging
logger = logging.getLogger(__name__)


class DataEngineerOutput(BaseModel):
    """Expected output structure from a Data Engineer agent."""
    response: str
    sql_query: Optional[str] = None
    table_references: Optional[List[str]] = None
    query_result: Optional[Dict[str, Any]] = None


class DataEngineerGuardrail(DataFidelityGuardrail):
    """
    Guardrail for validating Data Engineer agent outputs.
    
    This guardrail focuses on:
    1. SQL query correctness
    2. Database schema understanding
    3. SQL result accuracy
    """
    
    def __init__(
        self,
        valid_tables: Optional[List[str]] = None,
        valid_columns: Optional[Dict[str, List[str]]] = None,
        forbidden_sql_keywords: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Initialize a new DataEngineerGuardrail.
        
        Args:
            valid_tables: List of valid table names in the database
            valid_columns: Dictionary mapping table names to valid column names
            forbidden_sql_keywords: SQL keywords that should not be used
            **kwargs: Additional arguments to pass to the parent class
        """
        # Call the parent constructor with a default name and description
        super().__init__(
            name="DataEngineerGuardrail",
            description="Validates SQL queries and database schema understanding",
            **kwargs
        )
        
        # Set up database schema validation parameters
        self.valid_tables = valid_tables or [
            "players", "combat_events", "matches", "abilities", 
            "item_events", "timeline_events", "player_events", "player_stats"
        ]
        
        self.valid_columns = valid_columns or {
            "players": [
                "player_id", "match_id", "player_name", "team_id", 
                "role", "god_id", "god_name"
            ],
            "combat_events": [
                "event_id", "match_id", "event_time", "timestamp", "event_type",
                "source_entity", "target_entity", "ability_name", "location_x", 
                "location_y", "damage_amount", "damage_mitigated", "event_text"
            ],
            "matches": [
                "match_id", "map_name", "match_time", "match_duration", 
                "game_mode", "winner_team_id"
            ],
            "abilities": [
                "ability_id", "ability_name", "god_id", "ability_type",
                "cooldown", "ability_description"
            ],
            "item_events": [
                "event_id", "match_id", "event_time", "player_id", 
                "item_id", "item_name", "event_type"
            ],
            "timeline_events": [
                "event_id", "match_id", "event_time", "event_type",
                "entity_id", "location_x", "location_y", "event_details"
            ]
        }
        
        self.forbidden_sql_keywords = forbidden_sql_keywords or [
            "DELETE", "DROP", "INSERT", "UPDATE", "ALTER", "CREATE DATABASE",
            "TRUNCATE", "GRANT", "REVOKE", "PRAGMA", "VACUUM", "ATTACH"
        ]
        
        logger.info(f"Initialized {self.name} with {len(self.valid_tables)} valid tables")
    
    def validate_sql_query(self, sql_query: str) -> ValidationResult:
        """
        Validate an SQL query for safety and correctness.
        
        Args:
            sql_query: The SQL query to validate
            
        Returns:
            ValidationResult with any discrepancies found
        """
        discrepancies = []
        
        # Skip validation if no query provided
        if not sql_query:
            return ValidationResult(
                discrepancies=["No SQL query provided"],
                context={"query": None},
                tripwire_triggered=True
            )
        
        # Check for forbidden SQL keywords (case-insensitive)
        sql_upper = sql_query.upper()
        for keyword in self.forbidden_sql_keywords:
            keyword_upper = keyword.upper()
            if keyword_upper in sql_upper:
                pattern = r'\b' + re.escape(keyword_upper) + r'\b'
                if re.search(pattern, sql_upper):
                    discrepancies.append(f"SQL query contains forbidden keyword: {keyword}")
        
        # Basic syntax check - ensure it's a SELECT or WITH query
        if not (sql_upper.strip().startswith("SELECT") or sql_upper.strip().startswith("WITH")):
            discrepancies.append("SQL query must be a SELECT or WITH query")
        
        # Extract table references
        table_references = self._extract_table_references(sql_query)
        
        # Validate table references
        for table in table_references:
            if table.lower() not in [t.lower() for t in self.valid_tables]:
                discrepancies.append(f"SQL query references non-existent table: {table}")
        
        # Extract and validate column references
        column_references = self._extract_column_references(sql_query)
        for column, table in column_references:
            # Skip validation if table is unknown
            if table and table.lower() not in [t.lower() for t in self.valid_tables]:
                continue
                
            # If table is specified, validate column against that table
            if table:
                table_lower = table.lower()
                table_name = next((t for t in self.valid_tables if t.lower() == table_lower), None)
                
                if table_name and table_name in self.valid_columns:
                    valid_columns_lower = [c.lower() for c in self.valid_columns[table_name]]
                    if column.lower() not in valid_columns_lower:
                        discrepancies.append(f"SQL query references non-existent column {column} in table {table}")
        
        return ValidationResult(
            discrepancies=discrepancies,
            context={
                "query": sql_query,
                "table_references": table_references,
                "column_references": column_references
            },
            tripwire_triggered=len(discrepancies) > 0
        )
    
    def _extract_table_references(self, sql_query: str) -> List[str]:
        """
        Extract table references from an SQL query.
        
        Args:
            sql_query: The SQL query
            
        Returns:
            List of table names referenced in the query
        """
        tables = set()
        
        # Basic FROM pattern
        from_pattern = r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        for match in re.finditer(from_pattern, sql_query, re.IGNORECASE):
            tables.add(match.group(1))
        
        # JOIN pattern
        join_pattern = r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        for match in re.finditer(join_pattern, sql_query, re.IGNORECASE):
            tables.add(match.group(1))
        
        return list(tables)
    
    def _extract_column_references(self, sql_query: str) -> List[tuple]:
        """
        Extract column references from an SQL query.
        
        Args:
            sql_query: The SQL query
            
        Returns:
            List of (column_name, table_name) tuples
        """
        columns = []
        
        # Table.column pattern
        table_column_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)'
        for match in re.finditer(table_column_pattern, sql_query, re.IGNORECASE):
            columns.append((match.group(2), match.group(1)))
        
        # Column in SELECT without table qualifier
        select_pattern = r'SELECT\s+(.+?)\s+FROM'
        select_matches = re.search(select_pattern, sql_query, re.IGNORECASE | re.DOTALL)
        if select_matches:
            select_clause = select_matches.group(1)
            
            # Skip columns with table qualifiers (already handled)
            select_clause = re.sub(r'[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*', '', select_clause)
            
            # Extract column names
            column_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)'
            for match in re.finditer(column_pattern, select_clause):
                # Skip SQL keywords and function names
                col = match.group(1)
                if col.upper() not in [
                    "SELECT", "FROM", "WHERE", "GROUP", "BY", "HAVING",
                    "ORDER", "LIMIT", "COUNT", "SUM", "AVG", "MIN", "MAX", "AS"
                ]:
                    columns.append((col, None))
        
        return columns
    
    def validate_query_result(
        self,
        response: str,
        query_result: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate that the response accurately reflects the query result.
        
        Args:
            response: The agent's response text
            query_result: The result of the executed SQL query
            
        Returns:
            ValidationResult with any discrepancies found
        """
        discrepancies = []
        
        # Skip validation if no query result
        if not query_result or "data" not in query_result:
            return ValidationResult(
                discrepancies=["No query result provided for validation"],
                context={"result": None},
                tripwire_triggered=False  # Don't trigger for missing results
            )
        
        # Extract numerical values from the result for validation
        known_values = []
        
        # For dict-based results
        if isinstance(query_result["data"], list) and len(query_result["data"]) > 0:
            for row in query_result["data"]:
                for key, value in row.items():
                    if isinstance(value, (int, float)) and value > 0:
                        known_values.append(value)
        
        # For markdown or other text formats, use regex to extract numbers
        elif isinstance(query_result["data"], str):
            number_pattern = r'\|\s*(\d+(?:,\d+)?)\s*\|'
            for match in re.finditer(number_pattern, query_result["data"]):
                try:
                    value = int(match.group(1).replace(",", ""))
                    if value > 0:
                        known_values.append(value)
                except ValueError:
                    pass
        
        # Validate numerical values in the response
        numerical_validation = self.validate_numerical_values(
            response=response,
            known_values=known_values,
            value_type="database"
        )
        
        discrepancies.extend(numerical_validation.discrepancies)
        
        return ValidationResult(
            discrepancies=discrepancies,
            context={
                "known_values": known_values,
                "query_result_summary": f"Result with {len(known_values)} extractable values"
            },
            tripwire_triggered=len(discrepancies) > 0
        )
    
    @output_guardrail
    async def validate(
        self,
        ctx: RunContextWrapper,
        agent: Agent,
        output: DataEngineerOutput
    ) -> GuardrailFunctionOutput:
        """
        Validate the Data Engineer agent's output.
        
        Args:
            ctx: The run context
            agent: The agent that generated the output
            output: The output to validate
            
        Returns:
            GuardrailFunctionOutput with validation results
        """
        logger.info(f"Validating Data Engineer output")
        
        validation_results = []
        
        # Validate SQL query if present
        if output.sql_query:
            sql_validation = self.validate_sql_query(output.sql_query)
            validation_results.append(sql_validation)
        
        # Validate response content (no hallucinated values)
        if output.query_result:
            result_validation = self.validate_query_result(output.response, output.query_result)
            validation_results.append(result_validation)
        
        # Combine all validation results
        combined_validation = self.combine_validation_results(validation_results)
        
        logger.info(
            f"Validation completed with {len(combined_validation.discrepancies)} discrepancies. "
            f"Tripwire triggered: {combined_validation.tripwire_triggered}"
        )
        
        # Return the guardrail output
        return self.create_guardrail_output(combined_validation) 