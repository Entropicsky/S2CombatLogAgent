"""
SQLite connection manager for SMITE 2 combat log databases.
Enforces read-only access to prevent any modifications.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional, Union


class DatabaseConnectionError(Exception):
    """Exception raised for database connection errors."""
    pass


class DatabaseConnection:
    """
    Manages SQLite database connections with read-only enforcement.
    Ensures that no write operations can be performed on the database.
    """
    
    def __init__(self, db_path: Union[str, Path]):
        """
        Initialize the database connection manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self._connection: Optional[sqlite3.Connection] = None
        
    def __enter__(self) -> sqlite3.Connection:
        """
        Context manager entry point - opens the database connection.
        
        Returns:
            SQLite connection object with read-only access
        
        Raises:
            DatabaseConnectionError: If the database cannot be opened
        """
        return self.get_connection()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point - closes the database connection."""
        self.close()
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Get a read-only connection to the SQLite database.
        
        Returns:
            SQLite connection object with read-only access
        
        Raises:
            DatabaseConnectionError: If the database cannot be opened
        """
        if self._connection is not None:
            return self._connection
        
        if not self.db_path.exists():
            raise DatabaseConnectionError(f"Database file not found: {self.db_path}")
        
        try:
            # Open the database in read-only mode using URI
            uri = f"file:{self.db_path}?mode=ro"
            self._connection = sqlite3.connect(uri, uri=True)
            
            # Configure connection for better performance and safety
            self._connection.execute("PRAGMA query_only = ON;")  # Enforce read-only at pragma level
            self._connection.execute("PRAGMA foreign_keys = ON;")
            
            # Return dictionary-like rows for easier access
            self._connection.row_factory = sqlite3.Row
            
            return self._connection
        except sqlite3.Error as e:
            raise DatabaseConnectionError(f"Failed to connect to database: {str(e)}")
    
    def close(self):
        """Close the database connection if it's open."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
    
    def execute_query(self, query: str, params: tuple = ()) -> list:
        """
        Execute a read-only SQL query on the database.
        
        Args:
            query: SQL query to execute
            params: Parameters to bind to the query
            
        Returns:
            List of rows as dictionaries
            
        Raises:
            ValueError: If the query is not a SELECT statement
            sqlite3.Error: If there's an error executing the query
        """
        # Basic check to ensure only SELECT statements are allowed
        query_upper = query.strip().upper()
        if not query_upper.startswith(("SELECT", "WITH")):
            raise ValueError("Only SELECT queries are allowed")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        # Convert rows to dictionaries
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        return rows
    
    def get_table_schema(self, table_name: str) -> list:
        """
        Get the schema information for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
            
        Raises:
            sqlite3.Error: If there's an error executing the query
        """
        query = f"PRAGMA table_info({table_name})"
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        
        # Convert rows to dictionaries
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        return rows
    
    def get_all_tables(self) -> list:
        """
        Get a list of all tables in the database.
        
        Returns:
            List of table names
            
        Raises:
            sqlite3.Error: If there's an error executing the query
        """
        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        
        return [row[0] for row in cursor.fetchall()]


def get_connection(db_path: Union[str, Path]) -> DatabaseConnection:
    """
    Factory function to create a database connection.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        DatabaseConnection instance
    """
    return DatabaseConnection(db_path) 