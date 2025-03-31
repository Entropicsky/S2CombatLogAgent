"""
Utility functions for working with tools.
"""

import functools
import inspect
import json
from typing import Dict, Any, Callable, Optional, TypeVar, cast

# Type for function
F = TypeVar('F', bound=Callable)


def function_tool(
    func: Optional[F] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None
) -> F:
    """
    Decorator to mark a function as a tool for agents to use.
    
    This decorator adds metadata to the function that can be used by
    the agent to automatically generate OpenAI function calling specifications.
    
    Args:
        func: The function to decorate
        name: Custom name for the tool (defaults to function name)
        description: Custom description (defaults to function docstring)
        parameters: Custom parameters schema (defaults to generated from type hints)
        
    Returns:
        The decorated function with added metadata
    """
    def decorator(func: F) -> F:
        # Get function name, docstring and signature
        func_name = name or func.__name__
        func_doc = description or func.__doc__ or f"Function {func_name}"
        sig = inspect.signature(func)
        
        # Generate parameters schema if not provided
        if parameters is None:
            param_schema = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
            for param_name, param in sig.parameters.items():
                # Skip self, cls, and *args, **kwargs
                if param_name in ('self', 'cls') or param.kind in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD
                ):
                    continue
                
                # Get parameter type
                param_type = param.annotation
                type_str = str(param_type)
                
                # Create parameter schema
                param_info = {"description": f"Parameter {param_name}"}
                
                # Handle basic types
                if param_type == str or 'str' in type_str:
                    param_info["type"] = "string"
                elif param_type == int or 'int' in type_str:
                    param_info["type"] = "integer"
                elif param_type == float or 'float' in type_str:
                    param_info["type"] = "number"
                elif param_type == bool or 'bool' in type_str:
                    param_info["type"] = "boolean"
                elif param_type == list or 'list' in type_str or 'List' in type_str:
                    param_info["type"] = "array"
                    param_info["items"] = {"type": "string"}
                elif param_type == dict or 'dict' in type_str or 'Dict' in type_str:
                    param_info["type"] = "object"
                else:
                    param_info["type"] = "string"
                
                # Add parameter to schema
                param_schema["properties"][param_name] = param_info
                
                # Mark as required if no default value
                if param.default == inspect.Parameter.empty:
                    param_schema["required"].append(param_name)
        else:
            # Use provided parameters schema
            param_schema = parameters
        
        # Add metadata to function
        setattr(func, "is_tool", True)
        setattr(func, "tool_name", func_name)
        setattr(func, "tool_description", func_doc)
        setattr(func, "parameters", param_schema)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return cast(F, wrapper)
    
    # Allow both @function_tool and @function_tool() usage
    if func is None:
        return decorator
    return decorator(func)


def get_tool_schema(func: Callable) -> Dict[str, Any]:
    """
    Get the OpenAI function calling schema for a tool function.
    
    Args:
        func: The function to get the schema for
        
    Returns:
        Dictionary with function calling schema
    """
    if not hasattr(func, "is_tool") or not getattr(func, "is_tool", False):
        raise ValueError(f"Function {func.__name__} is not a tool")
    
    return {
        "type": "function",
        "function": {
            "name": getattr(func, "tool_name", func.__name__),
            "description": getattr(func, "tool_description", func.__doc__ or f"Function {func.__name__}"),
            "parameters": getattr(func, "parameters", {"type": "object", "properties": {}})
        }
    } 