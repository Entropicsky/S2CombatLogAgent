"""
Database schema utilities for extracting and providing schema information.
This is used to inform agents about the database structure.
"""

import sqlite3
from typing import Dict, List, Any, Optional
from pathlib import Path

from smite2_agent.db.connection import DatabaseConnection


class SchemaInfo:
    """
    Provides information about the database schema to inform agents.
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize the schema info provider.
        
        Args:
            db_connection: Database connection manager
        """
        self.db_connection = db_connection
        self._schema_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._tables_cache: Optional[List[str]] = None
    
    def get_all_tables(self) -> List[str]:
        """
        Get a list of all tables in the database.
        
        Returns:
            List of table names
        """
        if self._tables_cache is None:
            self._tables_cache = self.db_connection.get_all_tables()
        return self._tables_cache
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get schema information for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column information dictionaries
        """
        if table_name not in self._schema_cache:
            self._schema_cache[table_name] = self.db_connection.get_table_schema(table_name)
        return self._schema_cache[table_name]
    
    def get_column_names(self, table_name: str) -> List[str]:
        """
        Get a list of column names for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of column names
        """
        schema = self.get_table_schema(table_name)
        return [col["name"] for col in schema]
    
    def get_table_sample(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get a sample of rows from a table.
        
        Args:
            table_name: Name of the table
            limit: Maximum number of rows to return
            
        Returns:
            List of row dictionaries
        """
        query = f"SELECT * FROM {table_name} LIMIT {limit}"
        return self.db_connection.execute_query(query)
    
    def get_complete_schema_info(self) -> Dict[str, Any]:
        """
        Get complete schema information for all tables.
        
        Returns:
            Dictionary with schema information
        """
        tables = self.get_all_tables()
        result = {}
        
        for table_name in tables:
            # Get schema
            columns = self.get_table_schema(table_name)
            
            # Get row count
            try:
                count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                count_result = self.db_connection.execute_query(count_query)
                row_count = count_result[0]["count"] if count_result else 0
            except sqlite3.Error:
                row_count = "Error counting rows"
            
            # Get sample
            try:
                sample = self.get_table_sample(table_name, 3)
            except sqlite3.Error:
                sample = []
            
            # Build table info
            result[table_name] = {
                "columns": columns,
                "row_count": row_count,
                "sample": sample
            }
        
        return result
    
    def get_schema_description(self) -> str:
        """
        Get a textual description of the database schema.
        
        Returns:
            Markdown-formatted schema description
        """
        tables = self.get_all_tables()
        description = "# Database Schema\n\n"
        
        for table_name in tables:
            # Get schema
            columns = self.get_table_schema(table_name)
            
            # Get row count
            try:
                count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                count_result = self.db_connection.execute_query(count_query)
                row_count = count_result[0]["count"] if count_result else 0
            except sqlite3.Error:
                row_count = "Error counting rows"
            
            # Add table header
            description += f"## {table_name} ({row_count} rows)\n\n"
            
            # Add columns table
            description += "| Column | Type | Primary Key | Nullable |\n"
            description += "|--------|------|-------------|----------|\n"
            
            for col in columns:
                pk = "Yes" if col["pk"] == 1 else "No"
                nullable = "Yes" if col["notnull"] == 0 else "No"
                description += f"| {col['name']} | {col['type']} | {pk} | {nullable} |\n"
            
            description += "\n"
        
        return description
    
    def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get foreign key information for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of foreign key information dictionaries
        """
        query = f"PRAGMA foreign_key_list({table_name})"
        return self.db_connection.execute_query(query)
    
    def get_relationships(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all foreign key relationships in the database.
        
        Returns:
            Dictionary mapping table names to lists of foreign key relationships
        """
        tables = self.get_all_tables()
        relationships = {}
        
        for table_name in tables:
            foreign_keys = self.get_foreign_keys(table_name)
            if foreign_keys:
                relationships[table_name] = foreign_keys
        
        return relationships


def get_schema_info(db_path: Path) -> SchemaInfo:
    """
    Factory function to create a schema info provider.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        SchemaInfo instance
    """
    from smite2_agent.db.connection import get_connection
    db_connection = get_connection(db_path)
    return SchemaInfo(db_connection) 