"""
Chart generation tools for creating visualizations from data.
"""

import os
import uuid
import logging
import tempfile
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

# Set up logging
logger = logging.getLogger(__name__)


class ChartGenerationError(Exception):
    """Exception raised for chart generation errors."""
    pass


def generate_chart(
    data: Union[List[Dict[str, Any]], pd.DataFrame],
    chart_type: str,
    x_column: str,
    y_columns: Union[str, List[str]],
    title: Optional[str] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    color_column: Optional[str] = None,
    figsize: Tuple[int, int] = (10, 6),
    save_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a chart from data.
    
    Args:
        data: Data to visualize (list of dictionaries or pandas DataFrame)
        chart_type: Type of chart to generate ('line', 'bar', 'scatter', 'pie', 'area', 'histogram')
        x_column: Column to use for the x-axis
        y_columns: Column(s) to use for the y-axis
        title: Chart title (optional)
        xlabel: X-axis label (optional)
        ylabel: Y-axis label (optional)
        color_column: Column to use for color mapping (optional)
        figsize: Figure size (width, height) in inches (default: (10, 6))
        save_dir: Directory to save the chart (optional, default is a temp directory)
        
    Returns:
        Dictionary with chart metadata including file path
        
    Raises:
        ChartGenerationError: If the chart cannot be generated
    """
    try:
        # Convert data to DataFrame if it's a list of dictionaries
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()
        
        # Convert y_columns to list if it's a string
        if isinstance(y_columns, str):
            y_columns = [y_columns]
        
        # Create a unique filename
        chart_id = str(uuid.uuid4())
        if save_dir is None:
            save_dir = tempfile.mkdtemp()
        
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, f"chart_{chart_id}.png")
        
        # Create the figure
        plt.figure(figsize=figsize)
        
        # Generate the chart based on the chart type
        if chart_type == 'line':
            for y_column in y_columns:
                plt.plot(df[x_column], df[y_column], label=y_column)
            plt.legend()
            
        elif chart_type == 'bar':
            if len(y_columns) == 1:
                plt.bar(df[x_column], df[y_columns[0]])
            else:
                df.plot(kind='bar', x=x_column, y=y_columns, ax=plt.gca())
            plt.legend()
            
        elif chart_type == 'scatter':
            if color_column and color_column in df.columns:
                scatter = plt.scatter(df[x_column], df[y_columns[0]], 
                                   c=df[color_column], cmap='viridis', alpha=0.6)
                plt.colorbar(scatter, label=color_column)
            else:
                for y_column in y_columns:
                    plt.scatter(df[x_column], df[y_column], label=y_column, alpha=0.6)
                plt.legend()
                
        elif chart_type == 'pie':
            plt.pie(df[y_columns[0]], labels=df[x_column], autopct='%1.1f%%')
            
        elif chart_type == 'area':
            df.plot(kind='area', x=x_column, y=y_columns, ax=plt.gca())
            plt.legend()
            
        elif chart_type == 'histogram':
            for y_column in y_columns:
                plt.hist(df[y_column], bins=10, alpha=0.5, label=y_column)
            plt.legend()
            
        else:
            raise ChartGenerationError(f"Unsupported chart type: {chart_type}")
        
        # Set labels and title
        if title:
            plt.title(title)
        if xlabel:
            plt.xlabel(xlabel)
        else:
            plt.xlabel(x_column)
        if ylabel:
            plt.ylabel(ylabel)
        elif len(y_columns) == 1:
            plt.ylabel(y_columns[0])
        
        # Handle datetime x-axis if applicable
        if pd.api.types.is_datetime64_any_dtype(df[x_column]):
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
            plt.gcf().autofmt_xdate()
        
        # Adjust layout to prevent cutting off labels
        plt.tight_layout()
        
        # Save the chart
        plt.savefig(file_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        # Return chart metadata
        return {
            "success": True,
            "chart_path": file_path,
            "chart_id": chart_id,
            "chart_type": chart_type,
            "x_column": x_column,
            "y_columns": y_columns,
            "title": title
        }
    
    except Exception as e:
        logger.error(f"Chart generation error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "chart_generation_error"
        }


def generate_chart_from_sql(
    query_result: Dict[str, Any],
    chart_type: str,
    x_column: str,
    y_columns: Union[str, List[str]],
    title: Optional[str] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    color_column: Optional[str] = None,
    figsize: Tuple[int, int] = (10, 6),
    save_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a chart from SQL query results.
    
    Args:
        query_result: Result from run_sql_query function
        chart_type: Type of chart to generate
        x_column: Column to use for the x-axis
        y_columns: Column(s) to use for the y-axis
        title: Chart title (optional)
        xlabel: X-axis label (optional)
        ylabel: Y-axis label (optional)
        color_column: Column to use for color mapping (optional)
        figsize: Figure size (width, height) in inches (default: (10, 6))
        save_dir: Directory to save the chart (optional)
        
    Returns:
        Dictionary with chart metadata including file path
        
    Raises:
        ChartGenerationError: If the chart cannot be generated
    """
    try:
        # Check if the query was successful
        if not query_result.get("success", False):
            raise ChartGenerationError(f"SQL query failed: {query_result.get('error', 'Unknown error')}")
        
        # Get the data from the query result
        data = query_result.get("data", [])
        if not data:
            raise ChartGenerationError("No data returned from SQL query")
        
        # Generate the chart
        return generate_chart(
            data=data,
            chart_type=chart_type,
            x_column=x_column,
            y_columns=y_columns,
            title=title,
            xlabel=xlabel,
            ylabel=ylabel,
            color_column=color_column,
            figsize=figsize,
            save_dir=save_dir
        )
    
    except Exception as e:
        logger.error(f"Chart generation from SQL error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "chart_generation_error"
        }


def chart_type_from_data(data: Union[List[Dict[str, Any]], pd.DataFrame], x_column: str, y_column: str) -> str:
    """
    Determine the appropriate chart type based on data characteristics.
    
    Args:
        data: Data to visualize (list of dictionaries or pandas DataFrame)
        x_column: Name of the column to use for the x-axis
        y_column: Name of the column to use for the y-axis
        
    Returns:
        Recommended chart type ('line', 'bar', 'scatter', 'pie', etc.)
    """
    try:
        # Convert data to DataFrame if it's a list of dictionaries
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()
        
        # Check if columns exist
        if x_column not in df.columns or y_column not in df.columns:
            return "bar"  # Default to bar if columns don't exist
        
        # Check if x-axis is temporal (date/time)
        x_is_temporal = pd.api.types.is_datetime64_any_dtype(df[x_column])
        
        # Check if x-axis is categorical or numeric
        x_is_categorical = pd.api.types.is_categorical_dtype(df[x_column]) or pd.api.types.is_object_dtype(df[x_column])
        x_is_numeric = pd.api.types.is_numeric_dtype(df[x_column])
        
        # Check if y-axis is numeric
        y_is_numeric = pd.api.types.is_numeric_dtype(df[y_column])
        
        # Count unique values in x column
        unique_x_count = df[x_column].nunique()
        
        # Determine chart type based on data characteristics
        if x_is_temporal and y_is_numeric:
            return "line"  # Line chart for time series
        
        elif x_is_categorical and y_is_numeric:
            if unique_x_count <= 10:
                return "bar"  # Bar chart for categorical with few categories
            else:
                return "bar"  # Still bar, but might want to rotate labels
        
        elif x_is_numeric and y_is_numeric:
            return "scatter"  # Scatter plot for numeric vs numeric
        
        elif x_is_categorical and unique_x_count <= 8:
            return "pie"  # Pie chart for few categories
            
        else:
            return "bar"  # Default to bar chart
    
    except Exception as e:
        logger.warning(f"Error determining chart type: {str(e)}")
        return "bar"  # Default to bar chart on error 