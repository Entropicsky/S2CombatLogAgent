"""
SQL query function tools for agents to interact with the database.
"""

import sqlite3
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from smite2_agent.db.connection import DatabaseConnection, get_connection
from smite2_agent.db.validators import validate_query, SQLValidationError

# Set up logging
logger = logging.getLogger(__name__)


class SQLQueryError(Exception):
    """Exception raised for SQL query errors."""
    pass


def run_sql_query(
    query: str,
    db_path: Union[str, Path],
    params: tuple = (),
    max_rows: int = 1000,
    format_as: str = "dict"
) -> Dict[str, Any]:
    """
    Execute a read-only SQL query on the SMITE combat log database.
    
    Args:
        query: SQL SELECT query to run on the database
        db_path: Path to the SQLite database file
        params: Parameters to bind to the query (optional)
        max_rows: Maximum number of rows to return (default: 1000)
        format_as: Output format - 'dict', 'markdown', or 'csv' (default: 'dict')
        
    Returns:
        Dictionary with query results and metadata
        
    Raises:
        SQLQueryError: If the query is invalid or fails to execute
    """
    logger.info(f"Running SQL query: {query}")
    
    try:
        # Validate the query
        is_valid, error = validate_query(query)
        if not is_valid:
            raise SQLValidationError(f"Invalid SQL query: {error}")
        
        # Connect to the database
        db_conn = get_connection(db_path)
        
        # Execute the query
        with db_conn:
            rows = db_conn.execute_query(query, params)
            
            # Limit the number of rows returned
            limited_rows = rows[:max_rows] if max_rows > 0 else rows
            has_more = len(rows) > max_rows if max_rows > 0 else False
            
            # Format the results
            if format_as == "markdown":
                result = format_as_markdown(limited_rows)
            elif format_as == "csv":
                result = format_as_csv(limited_rows)
            else:  # Default to dict
                result = limited_rows
            
            # Prepare the response
            response = {
                "success": True,
                "data": result,
                "row_count": len(rows),
                "returned_rows": len(limited_rows),
                "has_more": has_more,
                "format": format_as,
                "query": query
            }
            
            return response
            
    except SQLValidationError as e:
        logger.error(f"SQL validation error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "error_type": "validation_error"
        }
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {str(e)}")
        return {
            "success": False,
            "error": f"Database error: {str(e)}",
            "query": query,
            "error_type": "database_error"
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "query": query,
            "error_type": "unexpected_error"
        }


def format_as_markdown(rows: List[Dict[str, Any]]) -> str:
    """
    Format query results as a Markdown table.
    
    Args:
        rows: List of row dictionaries
        
    Returns:
        Markdown-formatted table
    """
    if not rows:
        return "No data returned"
    
    # Get column names
    columns = list(rows[0].keys())
    
    # Build the header row
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    
    # Build the data rows
    data_rows = []
    for row in rows:
        values = []
        for col in columns:
            # Handle None values and format all values as strings
            value = row.get(col, "")
            if value is None:
                value = "NULL"
            else:
                value = str(value).replace("|", "\\|")  # Escape pipe characters
            values.append(value)
        data_rows.append("| " + " | ".join(values) + " |")
    
    # Combine all parts
    return "\n".join([header, separator] + data_rows)


def format_as_csv(rows: List[Dict[str, Any]]) -> str:
    """
    Format query results as a CSV string.
    
    Args:
        rows: List of row dictionaries
        
    Returns:
        CSV-formatted string
    """
    if not rows:
        return ""
    
    # Get column names
    columns = list(rows[0].keys())
    
    # Build the header row
    header = ",".join([f'"{col}"' for col in columns])
    
    # Build the data rows
    data_rows = []
    for row in rows:
        values = []
        for col in columns:
            # Handle None values and format all values as strings
            value = row.get(col, "")
            if value is None:
                value = ""
            else:
                # Escape quotes in the value
                value = f'"{str(value).replace("\"", "\\\"")}"'
            values.append(value)
        data_rows.append(",".join(values))
    
    # Combine all parts
    return "\n".join([header] + data_rows)


def get_table_schema(db_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get the schema information for all tables in the database.
    
    This includes column names, types, constraints, foreign keys, and sample data.
    
    Args:
        db_path: Path to the SQLite database
        
    Returns:
        Dictionary with schema information
        
    Raises:
        Exception: If the schema cannot be retrieved
    """
    logger.info(f"Getting schema for database: {db_path}")
    
    try:
        # Convert Path to string if needed
        if isinstance(db_path, Path):
            db_path = str(db_path)
            
        # Connect directly to SQLite for schema operations
        import sqlite3
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        
        # Get list of tables using direct SQLite query
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Get schema for each table
        schema = {}
        for table in tables:
            # Get table info using PRAGMA
            cursor.execute(f"PRAGMA table_info({table});")
            columns_data = cursor.fetchall()
            
            # Format column information
            table_schema = []
            for col in columns_data:
                table_schema.append({
                    'name': col['name'],
                    'type': col['type'],
                    'notnull': bool(col['notnull']),
                    'pk': bool(col['pk']),
                    'default': col['dflt_value']
                })
            
            # Get foreign keys if available
            try:
                cursor.execute(f"PRAGMA foreign_key_list({table});")
                foreign_keys_data = cursor.fetchall()
                
                # Format foreign key information
                fk_schema = []
                for fk in foreign_keys_data:
                    fk_schema.append({
                        'from': fk['from'],
                        'to': fk['to'],
                        'table': fk['table']
                    })
                
                schema[table] = {
                    'columns': table_schema,
                    'foreign_keys': fk_schema
                }
            except Exception as e:
                # If foreign key query fails, continue without foreign keys
                logger.warning(f"Could not get foreign keys for table {table}: {str(e)}")
                schema[table] = {
                    'columns': table_schema,
                    'foreign_keys': []
                }
        
        # Get sample data for each table (first 5 rows)
        for table in tables:
            try:
                cursor.execute(f"SELECT * FROM {table} LIMIT 5;")
                sample_data = [dict(row) for row in cursor.fetchall()]
                schema[table]['sample_data'] = sample_data
            except Exception as e:
                logger.warning(f"Could not get sample data for table {table}: {str(e)}")
                schema[table]['sample_data'] = []
        
        # Close the connection
        conn.close()
        
        return schema
        
    except Exception as e:
        logger.error(f"Error getting schema: {str(e)}")
        raise Exception(f"Failed to get database schema: {str(e)}") 