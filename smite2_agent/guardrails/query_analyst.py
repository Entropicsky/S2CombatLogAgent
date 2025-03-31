"""
Query Analyst Guardrail for SMITE 2 Combat Log Agent.

This module implements guardrails to validate the outputs of the Query Analyst Agent,
ensuring that the query analysis is accurate and that identified entities exist in
the actual database data.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Set
from pydantic import BaseModel

from agents import GuardrailFunctionOutput, RunContextWrapper, output_guardrail
from smite2_agent.guardrails.base import DataFidelityGuardrail

# Set up logging
logger = logging.getLogger(__name__)

class QueryAnalystOutput(BaseModel):
    """Output schema for the Query Analyst Agent."""
    query_type: str
    intent: str
    entities: List[Dict[str, Any]]
    metrics: List[Dict[str, Any]]
    tables_needed: List[str]
    sql_suggestions: List[str]
    enhanced_query: str

class QueryAnalystGuardrail(DataFidelityGuardrail):
    """
    Guardrail for validating Query Analyst Agent outputs.
    
    Validates that:
    1. Query type is one of the supported types
    2. Identified entities exist in the database
    3. Required tables exist in the database schema
    4. SQL suggestions follow security guidelines
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize a new Query Analyst Guardrail.
        
        Args:
            strict_mode: Whether to use strict mode for validation (default: False)
        """
        super().__init__(name="QueryAnalystGuardrail", strict_mode=strict_mode)
    
    @output_guardrail
    async def validate(self, ctx: RunContextWrapper, agent: Any, output: QueryAnalystOutput) -> GuardrailFunctionOutput:
        """
        Validate the Query Analyst output.
        
        Args:
            ctx: Run context wrapper containing data package information
            agent: The agent that produced the output
            output: The output to validate
            
        Returns:
            GuardrailFunctionOutput with validation results
        """
        logger.info("Running Query Analyst guardrail validation")
        discrepancies = []
        
        # Extract data package from context
        data_package = getattr(ctx, "context", {})
        
        # 1. Validate query type
        valid_query_types = [
            "combat_analysis", 
            "timeline_analysis", 
            "player_analysis", 
            "comparison_analysis", 
            "meta_analysis"
        ]
        
        if output.query_type not in valid_query_types:
            discrepancy = f"Invalid query type: {output.query_type}. Must be one of: {', '.join(valid_query_types)}"
            discrepancies.append(discrepancy)
            logger.warning(discrepancy)
        
        # 2. Validate tables existence if schema available
        if "input" in data_package and "db_path" in data_package["input"]:
            try:
                from smite2_agent.tools.sql_tools import get_table_schema
                import os
                
                db_path = data_package["input"]["db_path"]
                if db_path and os.path.exists(db_path):
                    schema = get_table_schema(db_path)
                    existing_tables = set(schema.keys())
                    
                    for table in output.tables_needed:
                        if table not in existing_tables:
                            discrepancy = f"Table '{table}' does not exist in the database schema"
                            discrepancies.append(discrepancy)
                            logger.warning(discrepancy)
            except Exception as e:
                logger.warning(f"Error validating tables: {str(e)}")
        
        # 3. Validate SQL suggestions for security
        for i, suggestion in enumerate(output.sql_suggestions):
            # Check for destructive SQL operations
            if re.search(r'\b(DELETE|UPDATE|DROP|ALTER|INSERT|CREATE)\b', suggestion, re.IGNORECASE):
                discrepancy = f"SQL suggestion {i+1} contains forbidden operations: {suggestion}"
                discrepancies.append(discrepancy)
                logger.warning(discrepancy)
        
        # 4. Validate entity identification (if entity data available)
        if "data" in data_package and "raw_data" in data_package["data"]:
            raw_data = data_package["data"]["raw_data"]
            
            # Check for players
            if "entity" in raw_data:
                player_entities = [e for e in output.entities if e.get("type", "") == "player"]
                
                # Access player names from database if available
                player_names_in_db = set()
                if "query_results" in data_package["data"]:
                    for query_result in data_package["data"]["query_results"].values():
                        if query_result.get("data"):
                            for row in query_result["data"]:
                                if "player" in row or "player_name" in row or "source_entity" in row:
                                    name = row.get("player") or row.get("player_name") or row.get("source_entity")
                                    if name:
                                        player_names_in_db.add(name)
                
                # If we have player names, validate entities
                if player_names_in_db and player_entities:
                    for player_entity in player_entities:
                        name = player_entity.get("name", "")
                        if name and name not in player_names_in_db:
                            # Only add as discrepancy in strict mode, otherwise just log
                            if self.strict_mode:
                                discrepancy = f"Player entity '{name}' not found in database"
                                discrepancies.append(discrepancy)
                                logger.warning(discrepancy)
                            else:
                                logger.info(f"Player entity '{name}' not found in database, but continuing in non-strict mode")
        
        # 5. Validate metrics exist for query type
        if not output.metrics:
            discrepancy = "No metrics identified for analysis"
            discrepancies.append(discrepancy)
            logger.warning(discrepancy)
        
        # Check for nonsensical metrics by query type
        combat_metrics = {"damage", "healing", "mitigated", "kills", "deaths", "assists"}
        timeline_metrics = {"time", "duration", "events", "sequence", "progression"}
        player_metrics = {"performance", "kda", "efficiency", "gold", "build", "items"}
        
        if output.query_type == "combat_analysis":
            relevant_metrics = combat_metrics
        elif output.query_type == "timeline_analysis":
            relevant_metrics = timeline_metrics
        elif output.query_type == "player_analysis":
            relevant_metrics = player_metrics
        else:
            relevant_metrics = combat_metrics.union(timeline_metrics).union(player_metrics)
        
        metric_names = {m.get("name", "").lower() for m in output.metrics}
        has_relevant = any(any(rel in name for rel in relevant_metrics) for name in metric_names)
        
        if not has_relevant and metric_names:
            discrepancy = f"Metrics {metric_names} don't seem to match query type {output.query_type}"
            discrepancies.append(discrepancy)
            logger.warning(discrepancy)
        
        # Return the validation result
        logger.info(f"Query Analyst guardrail validation completed: {len(discrepancies)} discrepancies found")
        
        return GuardrailFunctionOutput(
            output_info={"discrepancies": discrepancies},
            tripwire_triggered=len(discrepancies) > 0
        ) 