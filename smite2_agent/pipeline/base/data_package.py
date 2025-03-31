"""
Data Package module for inter-agent communication in the pipeline.

This module implements the standardized data structure that flows through
the multi-agent pipeline, containing all information needed by each agent
and accumulating results as it moves through the pipeline.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path


class DataPackage:
    """
    Standardized data package for inter-agent communication in the pipeline.
    
    The DataPackage is immutable from the perspective of agents - they
    receive a copy, modify it, and pass a new copy forward.
    """
    
    def __init__(
        self,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        match_id: Optional[str] = None,
        previous_queries: Optional[List[Dict[str, Any]]] = None,
        pipeline_type: Optional[str] = None,
        db_path: Optional[str] = None,
    ):
        """
        Initialize a new DataPackage with the user query.
        
        Args:
            query: The user's query string
            user_id: Optional user identifier
            session_id: Optional session identifier
            match_id: Optional match identifier
            previous_queries: Optional list of previous queries in the conversation
            pipeline_type: Optional pipeline type (combat_analysis, timeline_analysis, player_analysis)
            db_path: Optional path to the database
        """
        # Generate unique identifiers if not provided
        self.query_id = str(uuid.uuid4())
        self.timestamp = datetime.now().isoformat()
        
        # Initialize the package structure
        self._data = {
            "metadata": {
                "query_id": self.query_id,
                "timestamp": self.timestamp,
                "user_id": user_id or "anonymous",
                "session_id": session_id or self.query_id,
                "pipeline_type": pipeline_type,
                "processing_stage": "orchestrator",
                "processing_history": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            },
            "input": {
                "raw_query": query,
                "context": {
                    "previous_queries": previous_queries or [],
                    "match_id": match_id,
                    "focus_entities": [],
                    "db_path": db_path
                }
            },
            "query_analysis": {},
            "data": {
                "query_results": {},
                "transformed_data": {},
                "raw_query_results": {},  # Storage for raw query results for validation
                "raw_data": {}
            },
            "analysis": {
                "key_findings": [],
                "patterns": [],
                "comparisons": [],
                "recommended_visualizations": [],
                "results": {}
            },
            "visualizations": {},
            "response": {
                "direct_answer": "",
                "key_insights": [],
                "visualizations": [],
                "supporting_data": "",
                "additional_context": "",
                "followup_answers": {}
            },
            "final_output": {
                "formatted_response": ""
            },
            "validation": {
                "validated": False,
                "validation_history": [],
                "validation_errors": []
            },
            "errors": [],
            "domain_analysis": {}
        }
    
    def start_processing(self, stage: str, agent_id: str) -> None:
        """
        Record the start of processing by an agent.
        
        Args:
            stage: The processing stage (e.g., 'query_analyst')
            agent_id: The identifier of the agent
        """
        self._data["metadata"]["processing_stage"] = stage
        
        # Create precise timestamp with microseconds
        start_time = datetime.now().isoformat(timespec='microseconds')
        
        # Add to processing history
        self._data["metadata"]["processing_history"].append({
            "stage": stage,
            "agent_id": agent_id,
            "start_time": start_time,
            "end_time": None,
            "duration_ms": None,
            "status": "in_progress"
        })
    
    def end_processing(self, success: bool = True) -> None:
        """
        Record the end of processing by the current agent.
        
        Args:
            success: Whether processing was successful
        """
        if self._data["metadata"]["processing_history"]:
            current = self._data["metadata"]["processing_history"][-1]
            
            # Create precise timestamp with microseconds
            end_time = datetime.now().isoformat(timespec='microseconds')
            current["end_time"] = end_time
            current["status"] = "success" if success else "failed"
            
            # Calculate duration in milliseconds
            try:
                start = datetime.fromisoformat(current["start_time"])
                end = datetime.fromisoformat(end_time)
                duration_ms = round((end - start).total_seconds() * 1000, 2)
                current["duration_ms"] = duration_ms
            except (ValueError, TypeError):
                current["duration_ms"] = None
    
    def add_error(self, stage: str, error_type: str, description: str, handled: bool, recovery_action: Optional[str] = None) -> None:
        """
        Add an error to the package.
        
        Args:
            stage: The processing stage where the error occurred
            error_type: Type of error (e.g., 'minor', 'critical')
            description: Description of the error
            handled: Whether the error was handled
            recovery_action: Optional description of recovery action taken
        """
        self._data["errors"].append({
            "stage": stage,
            "error_type": error_type,
            "description": description,
            "handled": handled,
            "recovery_action": recovery_action
        })
    
    def set_query_analysis(self, query_type: str, intent: str, required_data_points: List[str], 
                          required_tables: List[str], sql_queries: List[Dict[str, Any]], 
                          anticipated_followups: Optional[List[str]] = None) -> None:
        """
        Set the query analysis information.
        
        Args:
            query_type: Type of the query (e.g., 'combat_analysis')
            intent: Intent of the query (e.g., 'find_top_damage_dealer')
            required_data_points: List of required data points
            required_tables: List of required database tables
            sql_queries: List of SQL queries with metadata
            anticipated_followups: Optional list of anticipated follow-up questions
        """
        self._data["query_analysis"] = {
            "query_type": query_type,
            "intent": intent,
            "required_data_points": required_data_points,
            "required_tables": required_tables,
            "sql_queries": sql_queries,
            "anticipated_followups": anticipated_followups or []
        }
    
    def add_query_result(self, query_id: str, sql: str, data: List[Dict[str, Any]], 
                        result_format: str = "dataframe", column_types: Optional[Dict[str, str]] = None,
                        raw_result: Optional[Dict[str, Any]] = None, execution_time_ms: Optional[float] = None) -> None:
        """
        Add a query result to the package.
        
        Args:
            query_id: Identifier for the query
            sql: The SQL query executed
            data: The query results as a list of dictionaries
            result_format: Format of the result (e.g., 'dataframe')
            column_types: Optional mapping of column names to types
            raw_result: Optional raw query result for validation
            execution_time_ms: Optional execution time in milliseconds
        """
        self._data["data"]["query_results"][query_id] = {
            "status": "completed",
            "sql": sql,
            "result_format": result_format,
            "column_types": column_types or {},
            "result_summary": {
                "row_count": len(data),
                "top_row": data[0] if data else {}
            },
            "data": data,
            "execution_time_ms": execution_time_ms
        }
        
        # Store raw query result for validation if provided
        if raw_result:
            self._data["data"]["raw_query_results"][query_id] = raw_result
    
    def add_transformed_data(self, key: str, description: str, data: List[Dict[str, Any]]) -> None:
        """
        Add transformed data to the package.
        
        Args:
            key: Identifier for the transformed dataset
            description: Description of the dataset
            data: The transformed data
        """
        self._data["data"]["transformed_data"][key] = {
            "description": description,
            "data": data
        }
    
    def add_key_finding(self, description: str, significance: str, supporting_data: str) -> None:
        """
        Add a key finding to the package.
        
        Args:
            description: Description of the finding
            significance: Significance level (e.g., 'high', 'medium', 'low')
            supporting_data: Reference to supporting data
        """
        finding_id = f"f{len(self._data['analysis']['key_findings']) + 1}"
        self._data["analysis"]["key_findings"].append({
            "finding_id": finding_id,
            "description": description,
            "significance": significance,
            "supporting_data": supporting_data
        })
    
    def add_pattern(self, description: str, significance: str, supporting_data: str) -> None:
        """
        Add a pattern to the package.
        
        Args:
            description: Description of the pattern
            significance: Significance level (e.g., 'high', 'medium', 'low')
            supporting_data: Reference to supporting data
        """
        pattern_id = f"p{len(self._data['analysis']['patterns']) + 1}"
        self._data["analysis"]["patterns"].append({
            "pattern_id": pattern_id,
            "description": description,
            "significance": significance,
            "supporting_data": supporting_data
        })
    
    def add_comparison(self, description: str, significance: str, supporting_data: str) -> None:
        """
        Add a comparison to the package.
        
        Args:
            description: Description of the comparison
            significance: Significance level (e.g., 'high', 'medium', 'low')
            supporting_data: Reference to supporting data
        """
        comparison_id = f"c{len(self._data['analysis']['comparisons']) + 1}"
        self._data["analysis"]["comparisons"].append({
            "comparison_id": comparison_id,
            "description": description,
            "significance": significance,
            "supporting_data": supporting_data
        })
    
    def add_visualization_recommendation(self, viz_type: str, title: str, data_source: str,
                                        x_column: Optional[str] = None, y_column: Optional[str] = None,
                                        importance: str = "medium") -> str:
        """
        Add a visualization recommendation to the package.
        
        Args:
            viz_type: Type of visualization (e.g., 'bar_chart')
            title: Title for the visualization
            data_source: Reference to the data source
            x_column: Optional x-axis column
            y_column: Optional y-axis column
            importance: Importance level (e.g., 'high', 'medium', 'low')
            
        Returns:
            The visualization ID
        """
        viz_id = f"v{len(self._data['analysis']['recommended_visualizations']) + 1}"
        self._data["analysis"]["recommended_visualizations"].append({
            "viz_id": viz_id,
            "type": viz_type,
            "title": title,
            "data_source": data_source,
            "x_column": x_column,
            "y_column": y_column,
            "importance": importance
        })
        return viz_id
    
    def add_visualization(self, viz_id: str, viz_type: str, title: str, file_path: str,
                         alt_text: str, embedded_data: Optional[str] = None) -> None:
        """
        Add a visualization to the package.
        
        Args:
            viz_id: Identifier for the visualization
            viz_type: Type of visualization (e.g., 'bar_chart')
            title: Title of the visualization
            file_path: Path to the visualization file
            alt_text: Alternative text for accessibility
            embedded_data: Optional base64-encoded image data
        """
        self._data["visualizations"][viz_id] = {
            "type": viz_type,
            "title": title,
            "file_path": file_path,
            "alt_text": alt_text,
            "embedded_data": embedded_data
        }
    
    def set_response(self, direct_answer: str, key_insights: List[str], visualizations: List[str],
                    supporting_data: str, additional_context: str, followup_answers: Dict[str, str]) -> None:
        """
        Set the response information.
        
        Args:
            direct_answer: Direct answer to the question
            key_insights: List of key insights
            visualizations: List of visualization IDs
            supporting_data: Supporting data text
            additional_context: Additional context text
            followup_answers: Dictionary of follow-up questions and answers
        """
        self._data["response"] = {
            "direct_answer": direct_answer,
            "key_insights": key_insights,
            "visualizations": visualizations,
            "supporting_data": supporting_data,
            "additional_context": additional_context,
            "followup_answers": followup_answers
        }
    
    def set_final_output(self, formatted_response: str) -> None:
        """
        Set the final formatted output.
        
        Args:
            formatted_response: The fully formatted response text
        """
        self._data["final_output"] = {
            "formatted_response": formatted_response
        }
    
    def add_validation_result(self, stage: str, guardrail_name: str, 
                           success: bool, discrepancies: List[str],
                           context: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a validation result to the package.
        
        Args:
            stage: The processing stage where validation occurred
            guardrail_name: Name of the guardrail
            success: Whether validation was successful
            discrepancies: List of discrepancies found
            context: Optional context information
        """
        timestamp = datetime.now().isoformat()
        self._data["validation"]["validation_history"].append({
            "stage": stage,
            "guardrail_name": guardrail_name,
            "timestamp": timestamp,
            "success": success,
            "discrepancies": discrepancies,
            "context": context or {}
        })
        
        # Update overall validation status
        self._data["validation"]["validated"] = all(
            entry["success"] for entry in self._data["validation"]["validation_history"]
        )
        
        # If validation failed, add to validation errors
        if not success:
            self._data["validation"]["validation_errors"].append({
                "stage": stage,
                "guardrail_name": guardrail_name,
                "timestamp": timestamp,
                "discrepancies": discrepancies
            })
    
    def add_raw_data_for_validation(self, key: str, data: Any, category: str = "database") -> None:
        """
        Add raw data to the package for validation purposes.
        
        This provides guardrails with access to the original data for validation.
        
        Args:
            key: Identifier for the data
            data: The raw data
            category: Category of data (e.g., 'database', 'entity', 'numerical')
        """
        # Ensure raw_data exists in the package
        if "raw_data" not in self._data["data"]:
            self._data["data"]["raw_data"] = {}
            
        # Ensure the category exists
        if category not in self._data["data"]["raw_data"]:
            self._data["data"]["raw_data"][category] = {}
            
        # Store the data
        self._data["data"]["raw_data"][category][key] = data
    
    def get_raw_data_for_validation(self, key: str, category: str = "database") -> Optional[Any]:
        """
        Get raw data from the package for validation purposes.
        
        Args:
            key: Identifier for the data
            category: Category of data (e.g., 'database', 'entity', 'numerical')
            
        Returns:
            The raw data or None if not found
        """
        try:
            return self._data["data"]["raw_data"][category][key]
        except (KeyError, TypeError):
            return None
    
    def is_validated(self) -> bool:
        """
        Check if the package has been validated.
        
        Returns:
            True if all validations have passed, False otherwise
        """
        return self._data["validation"]["validated"]
    
    def get_validation_errors(self) -> List[Dict[str, Any]]:
        """
        Get all validation errors.
        
        Returns:
            List of validation error dictionaries
        """
        return self._data["validation"]["validation_errors"]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the package to a dictionary.
        
        Returns:
            The package data as a dictionary
        """
        return self._data
    
    def to_json(self) -> str:
        """
        Convert the package to a JSON string.
        
        Returns:
            The package data as a JSON string
        """
        return json.dumps(self._data, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataPackage':
        """
        Create a DataPackage from a dictionary.
        
        Args:
            data: The dictionary containing package data
            
        Returns:
            A new DataPackage instance
        """
        package = cls(query=data["input"]["raw_query"])
        package._data = data
        return package
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DataPackage':
        """
        Create a DataPackage from a JSON string.
        
        Args:
            json_str: The JSON string containing package data
            
        Returns:
            A new DataPackage instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    async def validate_with_guardrail(self, guardrail, agent, output, stage: str) -> bool:
        """
        Validate the package using a guardrail.
        
        Args:
            guardrail: The guardrail to use
            agent: The agent that produced the output
            output: The output to validate
            stage: The processing stage
            
        Returns:
            True if validation passed, False otherwise
        """
        try:
            # Create a mock context wrapper
            class MockContextWrapper:
                def __init__(self, context):
                    self.context = context
            
            ctx = MockContextWrapper(self._data)
            
            # Run the guardrail validation
            result = await guardrail.validate(ctx, agent, output)
            
            # Add the validation result to the package
            self.add_validation_result(
                stage=stage,
                guardrail_name=guardrail.name,
                success=not result.tripwire_triggered,
                discrepancies=result.output_info.get("discrepancies", []),
                context=result.output_info
            )
            
            return not result.tripwire_triggered
        except Exception as e:
            # Add an error if validation fails
            self.add_error(
                stage=stage,
                error_type="guardrail_error",
                description=f"Guardrail validation failed: {str(e)}",
                handled=True,
                recovery_action="Continuing without validation"
            )
            return False

    def get_user_query(self) -> str:
        """
        Get the user's raw query.
        
        Returns:
            The user's original query
        """
        return self._data["input"]["raw_query"]
    
    def set_db_path(self, db_path: Union[str, Path]) -> None:
        """
        Set the database path.
        
        Args:
            db_path: Path to the database
        """
        self._data["input"]["db_path"] = str(db_path)
    
    def get_db_path(self) -> Optional[str]:
        """
        Get the database path.
        
        Returns:
            The database path or None if not set
        """
        return self._data["input"].get("db_path")
    
    def has_errors(self) -> bool:
        """
        Check if the package has any errors.
        
        Returns:
            True if the package has errors, False otherwise
        """
        return len(self._data["errors"]) > 0
    
    def get_first_error(self) -> Optional[Dict[str, Any]]:
        """
        Get the first error from the package.
        
        Returns:
            The first error or None if there are no errors
        """
        if self._data["errors"]:
            return self._data["errors"][0]
        return None
    
    def get_all_errors(self) -> List[Dict[str, Any]]:
        """
        Get all errors from the package.
        
        Returns:
            List of error dictionaries
        """
        return self._data["errors"]
    
    def get_response(self) -> str:
        """
        Get the final response.
        
        Returns:
            The formatted response string or None if not set
        """
        if "final_output" in self._data and "formatted_response" in self._data["final_output"]:
            return self._data["final_output"]["formatted_response"]
        return None
    
    def add_error(self, error: Dict[str, Any]) -> None:
        """
        Add an error to the package.
        
        Args:
            error: Error dictionary with agent, error, and error_type keys
        """
        self._data["errors"].append(error)
    
    def add_analysis_results(self, results: Dict[str, Any]) -> None:
        """
        Add analysis results to the package.
        
        Args:
            results: Dictionary containing analysis results
        """
        self._data["analysis"]["results"] = results

    def get_analysis_results(self) -> Optional[Dict[str, Any]]:
        """
        Get the analysis results from the package.
        
        Returns:
            Analysis results dictionary or None if not available
        """
        return self._data["analysis"].get("results")

    def get_query_results(self) -> Dict[str, Any]:
        """
        Get the query results from the package.
        
        Returns:
            Dictionary of query results
        """
        return self._data["data"]["query_results"]

    def add_domain_analysis(self, analysis: Dict[str, Any]) -> None:
        """
        Add domain concept analysis to the data package.
        
        Args:
            analysis: Dictionary containing domain concept analysis
        """
        if "domain_analysis" not in self._data:
            self._data["domain_analysis"] = {}
            
        self._data["domain_analysis"] = analysis
        
    def get_domain_analysis(self) -> Optional[Dict[str, Any]]:
        """
        Get the domain concept analysis from the data package.
        
        Returns:
            Domain analysis dictionary or None if not available
        """
        return self._data.get("domain_analysis")

    def to_debug_json(self) -> str:
        """
        Convert the package to a detailed debug JSON string for UI consumption.
        
        This format provides a structured view of the final response along with
        all the SQL queries executed and their raw results - intended for use
        in web UIs that need to show both the answer and debugging details.
        
        Returns:
            Detailed debug JSON string with end-user response and debugging details
        """
        # Start with the formatted response for end users
        debug_data = {
            "user_response": {
                "formatted_answer": self._data["final_output"].get("formatted_response", ""),
                "suggested_followups": self._data.get("enhancement", {}).get("suggested_questions", [])
            },
            "pipeline_details": {
                "queries": [],
                "analysis": {
                    "key_findings": self._data["analysis"].get("key_findings", []),
                    "patterns": self._data["analysis"].get("patterns", []),
                    "raw_results": self._data["analysis"].get("results", {})
                },
                "process_flow": self._data["metadata"].get("processing_history", [])
            },
            "metadata": {
                "query_id": self._data["metadata"].get("query_id", ""),
                "timestamp": self._data["metadata"].get("timestamp", ""),
                "pipeline_type": self._data["metadata"].get("pipeline_type", ""),
                "errors": self._data.get("errors", [])
            },
            "performance_metrics": {
                "total_processing_time_ms": 0,
                "stage_breakdown": [],
                "slowest_stage": {"stage": "", "time_ms": 0},
                "query_execution_time_ms": 0
            }
        }
        
        # Add detailed query information
        total_query_time = 0
        for query_id, query_data in self._data["data"].get("query_results", {}).items():
            # Try to extract query purpose from metadata if available
            purpose = f"Query {query_id}"
            for sql_query in self._data.get("query_analysis", {}).get("sql_queries", []):
                if sql_query.get("query_id") == query_id:
                    purpose = sql_query.get("purpose", purpose)
            
            # Safely handle execution time
            try:
                execution_time = float(query_data.get("execution_time_ms", 0))
                if execution_time is None:
                    execution_time = 0
            except (TypeError, ValueError):
                execution_time = 0
            
            # Add the query info to the debug data
            query_info = {
                "query_id": query_id,
                "purpose": purpose,
                "sql": query_data.get("sql", ""),
                "row_count": len(query_data.get("data", [])),
                "execution_time_ms": execution_time,
                "results": query_data.get("data", [])[:25]  # Limit to first 25 rows for efficiency
            }
            debug_data["pipeline_details"]["queries"].append(query_info)
            
            # Add to total query time
            total_query_time += execution_time
        
        # Add performance metrics
        history = self._data["metadata"].get("processing_history", [])
        
        # Calculate total processing time and stage breakdown
        total_time = 0
        slowest_stage = {"stage": "", "time_ms": 0}
        
        for entry in history:
            # Skip entries without duration
            if entry.get("duration_ms") is None:
                continue
                
            # Safely handle the stage time, ensuring it's a number
            try:
                stage_time = float(entry.get("duration_ms", 0))
                if stage_time is None:
                    stage_time = 0
            except (TypeError, ValueError):
                stage_time = 0
                
            total_time += stage_time
            
            # Track the slowest stage (safely compare values)
            if stage_time > slowest_stage.get("time_ms", 0):
                slowest_stage = {
                    "stage": entry.get("stage", ""),
                    "time_ms": stage_time
                }
            
            # Add to stage breakdown
            debug_data["performance_metrics"]["stage_breakdown"].append({
                "stage": entry.get("stage", ""),
                "time_ms": stage_time,
                "percentage": 0  # Will calculate after total is known
            })
        
        # Update total processing time
        debug_data["performance_metrics"]["total_processing_time_ms"] = total_time
        debug_data["performance_metrics"]["query_execution_time_ms"] = total_query_time
        debug_data["performance_metrics"]["slowest_stage"] = slowest_stage
        
        # Calculate percentages for each stage (with safe division)
        if total_time > 0:
            for stage in debug_data["performance_metrics"]["stage_breakdown"]:
                try:
                    stage_time_ms = float(stage.get("time_ms", 0))
                    if stage_time_ms is None:
                        stage_time_ms = 0
                    stage["percentage"] = round((stage_time_ms / total_time) * 100, 2)
                except (TypeError, ValueError, ZeroDivisionError):
                    stage["percentage"] = 0
        
        return json.dumps(debug_data, indent=2) 