"""
Tools for using PandasAI to analyze data from the combat log database.

This implementation provides both:
1. A wrapper around PandasAI when available
2. A custom implementation that provides similar functionality using pandas and OpenAI directly
   when the PandasAI library is not available
"""

import os
import io
import json
import sqlite3
import logging
from typing import Dict, List, Any, Optional, Union
import traceback

import pandas as pd
import numpy as np

# Try to import PandasAI, but don't fail if it's not available
try:
    import pandasai
    from pandasai import PandasAI
    from pandasai.llm import OpenAI as PandasAI_OpenAI
    PANDASAI_AVAILABLE = True
except ImportError:
    PANDASAI_AVAILABLE = False

# Set up logging
logger = logging.getLogger(__name__)

class PandasAIError(Exception):
    """Exception raised for errors in the PandasAI tools."""
    pass

def load_dataframe_from_db(db_path: str, query: str) -> pd.DataFrame:
    """
    Load a dataframe from a SQLite database using a SQL query.
    
    Args:
        db_path: Path to the SQLite database file
        query: SQL query to execute
        
    Returns:
        DataFrame with the results of the query
        
    Raises:
        PandasAIError: If there's an error connecting to the database or executing the query
    """
    try:
        # Connect to the database in read-only mode
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        
        # Set the connection to read-only mode as an extra safety measure
        conn.execute("PRAGMA query_only = ON;")
        
        # Execute the query and load the results into a DataFrame
        df = pd.read_sql_query(query, conn)
        
        # Close the connection
        conn.close()
        
        return df
    except Exception as e:
        error_msg = f"Error loading dataframe from database: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise PandasAIError(error_msg)

def format_pandasai_result(result: Any) -> str:
    """
    Format the result from PandasAI into a string.
    
    Args:
        result: The result from PandasAI, which could be a DataFrame, string, dict, etc.
        
    Returns:
        Formatted string representation of the result
    """
    if isinstance(result, pd.DataFrame):
        # If it's a small DataFrame, return it as a formatted table
        if len(result) <= 20:
            return result.to_string()
        # Otherwise, return a summary
        else:
            buffer = io.StringIO()
            buffer.write(f"DataFrame with {len(result)} rows and {len(result.columns)} columns.\n")
            buffer.write("First 10 rows:\n")
            buffer.write(result.head(10).to_string())
            buffer.write("\n\nLast 10 rows:\n")
            buffer.write(result.tail(10).to_string())
            return buffer.getvalue()
    elif isinstance(result, dict):
        # Convert dict to JSON string with pretty formatting
        return json.dumps(result, indent=2)
    elif isinstance(result, (list, tuple)):
        # Handle lists
        if all(isinstance(item, dict) for item in result):
            # List of dicts, format as JSON
            return json.dumps(result, indent=2)
        else:
            # Regular list
            return "\n".join(str(item) for item in result)
    elif isinstance(result, (int, float, np.number)):
        # Format numbers nicely
        return str(result)
    else:
        # Other types (usually strings)
        return str(result)

def run_pandasai_prompt(df: pd.DataFrame, prompt: str, api_key: str) -> str:
    """
    Run a natural language prompt against a DataFrame using PandasAI or a custom implementation.
    
    Args:
        df: The DataFrame to analyze
        prompt: The natural language prompt
        api_key: OpenAI API key
        
    Returns:
        The result as a formatted string
        
    Raises:
        PandasAIError: If there's an error running the prompt
    """
    try:
        # If PandasAI is available, use it
        if PANDASAI_AVAILABLE:
            # Create the PandasAI instance with the OpenAI LLM
            llm = PandasAI_OpenAI(api_token=api_key)
            pandas_ai = PandasAI(llm)
            
            # Run the prompt
            result = pandas_ai.run(df, prompt=prompt)
            
            # Format and return the result
            return format_pandasai_result(result)
        else:
            # Use our custom implementation
            return run_custom_dataframe_analysis(df, prompt, api_key)
    except Exception as e:
        error_msg = f"Error running PandasAI prompt: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise PandasAIError(error_msg)

def run_custom_dataframe_analysis(df: pd.DataFrame, prompt: str, api_key: str) -> str:
    """
    A custom implementation that provides similar functionality to PandasAI
    using pandas and OpenAI directly.
    
    Args:
        df: The DataFrame to analyze
        prompt: The natural language prompt
        api_key: OpenAI API key
        
    Returns:
        The result as a formatted string
    """
    import openai
    
    try:
        # Format DataFrame information
        df_info = {
            "shape": df.shape,
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "head": df.head(5).to_dict(orient="records"),
            "describe": {col: df[col].describe().to_dict() for col in df.select_dtypes(include=['number']).columns},
        }
        
        # Sample values for each column (up to 10 unique values)
        sample_values = {}
        for col in df.columns:
            unique_values = df[col].dropna().unique()
            if len(unique_values) > 10:
                unique_values = unique_values[:10]
            sample_values[col] = [str(val)[:100] for val in unique_values]
        
        df_info["sample_values"] = sample_values
        
        # Create the client
        client = openai.OpenAI(api_key=api_key)
        
        # Create the system prompt
        system_prompt = f"""
        You are an expert data analyst who specializes in analyzing pandas DataFrames.
        You will receive information about a DataFrame and a question about it.
        Your task is to generate Python code using pandas to answer the question.
        The code should be simple, efficient, and focused on answering the specific question asked.
        
        DataFrame Information:
        - Shape: {df_info['shape']}
        - Columns: {', '.join(df_info['columns'])}
        - Column Data Types: {json.dumps(df_info['dtypes'])}
        - Sample data (first 5 rows): {json.dumps(df_info['head'], indent=2)}
        - Statistical summary: {json.dumps(df_info['describe'], indent=2)}
        - Sample values for each column: {json.dumps(df_info['sample_values'], indent=2)}
        
        Respond in the following format:
        ```python
        # Your code to analyze the DataFrame and answer the question
        ```
        
        IMPORTANT: Make sure your code has no indentation at the beginning of lines.
        After the code block, briefly explain the result in plain language.
        """
        
        # Send the request to OpenAI
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
        )
        
        # Extract the generated code
        response_text = response.choices[0].message.content
        
        # Find the code block
        if "```python" in response_text and "```" in response_text:
            code_start = response_text.find("```python") + 9
            code_end = response_text.find("```", code_start)
            code = response_text[code_start:code_end].strip()
            
            # Fix indentation - remove any common leading whitespace
            code_lines = code.split('\n')
            # Find minimum indentation (excluding empty lines)
            non_empty_lines = [line for line in code_lines if line.strip()]
            if non_empty_lines:
                min_indent = min(len(line) - len(line.lstrip()) for line in non_empty_lines)
                # Remove this indentation from all lines
                code_lines = [line[min_indent:] if line.strip() else line for line in code_lines]
                code = '\n'.join(code_lines)
            
            # Execute the code
            locals_dict = {"df": df}
            
            # Safe execution
            exec(code, {"pd": pd, "np": np}, locals_dict)
            
            # Find the result variable (usually the last assignment)
            result_lines = code.strip().split("\n")
            result_var = None
            
            for line in reversed(result_lines):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    result_var = line.split("=")[0].strip()
                    break
            
            # If we couldn't find a result variable, look for the last expression
            if not result_var:
                for line in reversed(result_lines):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" not in line:
                        # Evaluate the expression
                        try:
                            result = eval(line, {"pd": pd, "np": np, "df": df})
                            return format_pandasai_result(result) + "\n\n" + response_text[code_end+3:].strip()
                        except:
                            pass
            
            # Get the result
            if result_var and result_var in locals_dict:
                result = locals_dict[result_var]
                return format_pandasai_result(result) + "\n\n" + response_text[code_end+3:].strip()
        
        # If we couldn't execute the code, return the full response
        return response_text
        
    except Exception as e:
        error_msg = f"Error running custom DataFrame analysis: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        # Attempt to provide a simpler analysis as a fallback
        try:
            # Create a markdown table of the first 10 rows
            table_result = f"Error running advanced analysis: {str(e)}\n\n"
            table_result += "Here's a sample of the data:\n\n"
            table_result += df.head(10).to_string()
            return table_result
        except:
            # Last resort - return the error with basic dataframe info
            return f"Error analyzing data: {str(e)}\n\nDataFrame shape: {df.shape}\nColumns: {', '.join(df.columns)}" 