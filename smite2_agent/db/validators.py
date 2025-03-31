"""
SQL validation utilities to ensure queries are safe and read-only.
Prevents any destructive operations on the database.
"""

import re
import sqlparse
from typing import Tuple, List, Optional


class SQLValidationError(Exception):
    """Exception raised for SQL validation errors."""
    pass


def is_read_only_query(query: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a SQL query is read-only.
    
    Args:
        query: SQL query to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if the query is read-only, False otherwise
        - error_message: Error message if the query is not read-only, None otherwise
    """
    # Normalize query by removing comments and whitespace
    query = query.strip()
    
    # Parse the SQL statement
    try:
        parsed = sqlparse.parse(query)
        if not parsed:
            return False, "Empty query"
        
        statement = parsed[0]
        
        # Get the statement type (SELECT, INSERT, etc.)
        statement_type = statement.get_type().upper() if statement.get_type() else ""
        
        # Check for allowed statement types
        allowed_types = ("SELECT", "WITH", "")
        if statement_type not in allowed_types:
            return False, f"Query type '{statement_type}' is not allowed. Only SELECT and WITH queries are permitted."
        
        # Look for disallowed keywords that might indicate a non-read-only query
        disallowed_patterns = [
            r'\bINSERT\b',
            r'\bUPDATE\b',
            r'\bDELETE\b',
            r'\bDROP\b',
            r'\bALTER\b',
            r'\bCREATE\b',
            r'\bATTACH\b',
            r'\bDETACH\b',
            r'\bREINDEX\b',
            r'\bREPLACE\b',
            r'\bTRUNCATE\b',
            r'\bPRAGMA\b(?!.*\bquery_only\b)',  # PRAGMA allowed only for query_only
        ]
        
        # Join patterns with OR operator
        combined_pattern = '|'.join(disallowed_patterns)
        
        # Check for any disallowed patterns
        matches = re.finditer(combined_pattern, query, re.IGNORECASE)
        for match in matches:
            keyword = match.group(0)
            return False, f"Query contains disallowed keyword: {keyword}"
        
        # Additional check for statements after semicolons
        statements = query.split(';')
        if len(statements) > 2 or (len(statements) == 2 and statements[1].strip()):
            return False, "Multiple statements are not allowed"
        
        # Additional validation for WITH queries
        if statement_type == "WITH":
            # Ensure the WITH clause is followed by a SELECT
            with_parts = re.split(r'\bWITH\b', query, flags=re.IGNORECASE, maxsplit=1)
            if len(with_parts) > 1:
                after_with = with_parts[1]
                # Check if there's a SELECT after any CTE definitions
                # This regex checks for a SELECT that's not part of a CTE definition
                if not re.search(r'(?<!\bAS\s*\(\s*)\bSELECT\b', after_with, re.IGNORECASE):
                    return False, "WITH clause must be followed by a SELECT statement"
        
        return True, None
        
    except Exception as e:
        return False, f"SQL validation error: {str(e)}"


def validate_table_name(table_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a table name to prevent SQL injection.
    
    Args:
        table_name: Table name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if the table name is valid, False otherwise
        - error_message: Error message if the table name is invalid, None otherwise
    """
    # Table names should only contain alphanumeric characters, underscores, or periods (for schema qualification)
    if not re.match(r'^[a-zA-Z0-9_\.]+$', table_name):
        return False, f"Invalid table name: {table_name}"
    
    # Check for any SQL injection attempts
    risky_patterns = [
        r'--|#',           # SQL comments
        r'\/\*|\*\/',      # C-style comments
        r';',              # Statement terminator
        r'@',              # Variable indicator in some SQL dialects
        r'xp_',            # Common prefix for extended stored procedures
        r'sp_',            # Common prefix for stored procedures
    ]
    
    combined_pattern = '|'.join(risky_patterns)
    if re.search(combined_pattern, table_name):
        return False, f"Table name contains disallowed characters: {table_name}"
    
    return True, None


def get_tables_referenced(query: str) -> List[str]:
    """
    Extract table names referenced in a SQL query.
    This is a simplified version and may not catch all table references.
    
    Args:
        query: SQL query to analyze
        
    Returns:
        List of table names referenced in the query
    """
    # Parse the SQL statement
    try:
        parsed = sqlparse.parse(query)
        if not parsed:
            return []
        
        # Simple regex to extract table names from FROM and JOIN clauses
        # This is a basic implementation and might miss some complex cases
        from_pattern = r'\bFROM\s+([a-zA-Z0-9_\.]+)'
        join_pattern = r'\bJOIN\s+([a-zA-Z0-9_\.]+)'
        
        tables = []
        
        # Find FROM clauses
        from_matches = re.finditer(from_pattern, query, re.IGNORECASE)
        for match in from_matches:
            tables.append(match.group(1))
        
        # Find JOIN clauses
        join_matches = re.finditer(join_pattern, query, re.IGNORECASE)
        for match in join_matches:
            tables.append(match.group(1))
        
        return tables
        
    except Exception:
        return []


def validate_query(query: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a SQL query for safety and read-only operations.
    
    Args:
        query: SQL query to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if the query is valid and safe, False otherwise
        - error_message: Error message if the query is invalid, None otherwise
    """
    # Check if the query is read-only
    is_read_only, error = is_read_only_query(query)
    if not is_read_only:
        return False, error
    
    # Validate table names in the query
    tables = get_tables_referenced(query)
    for table in tables:
        is_valid, error = validate_table_name(table)
        if not is_valid:
            return False, error
    
    return True, None 