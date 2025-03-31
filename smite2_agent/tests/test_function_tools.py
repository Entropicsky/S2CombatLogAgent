"""
Tests for function tool decorator implementation.
"""

import unittest
from typing import List, Dict, Any, Optional
from unittest.mock import patch, MagicMock

import inspect

from smite2_agent.agents.openai_agent import OpenAIAgent


# Create a function tool decorator for testing
def function_tool(func):
    """
    Decorator to mark a function as a tool for agent usage.
    This is a simplified version for testing.
    """
    # Extract parameter information from the function
    signature = inspect.signature(func)
    parameters = {}
    
    for name, param in signature.parameters.items():
        param_info = {}
        annotation = param.annotation
        
        if annotation is inspect.Parameter.empty:
            # Default to string if no type annotation
            param_info["type"] = "string"
        elif annotation is str:
            param_info["type"] = "string"
        elif annotation is int:
            param_info["type"] = "integer"
        elif annotation is float:
            param_info["type"] = "number"
        elif annotation is bool:
            param_info["type"] = "boolean"
        elif annotation is List or getattr(annotation, "__origin__", None) is list:
            param_info["type"] = "array"
        elif annotation is Dict or getattr(annotation, "__origin__", None) is dict:
            param_info["type"] = "object"
        else:
            # Default to string for complex types
            param_info["type"] = "string"
        
        # Add description if docstring has parameter info
        if func.__doc__ and f":param {name}:" in func.__doc__:
            doc_lines = func.__doc__.split("\n")
            for line in doc_lines:
                if f":param {name}:" in line:
                    param_info["description"] = line.split(f":param {name}:")[1].strip()
                    break
        
        parameters[name] = param_info
    
    # Create parameters schema
    func.parameters = {
        "type": "object",
        "properties": parameters,
        "required": [name for name, param in signature.parameters.items() 
                    if param.default is inspect.Parameter.empty]
    }
    
    return func


class TestFunctionTools(unittest.TestCase):
    """Test suite for function tool implementation."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Define test tools
        @function_tool
        def simple_tool(param1: str, param2: int = 0) -> str:
            """
            A simple tool for testing.
            
            :param param1: The first parameter
            :param param2: The second parameter (optional)
            :return: A test result
            """
            return f"Result: {param1} - {param2}"
        
        @function_tool
        def complex_tool(data: Dict[str, Any], options: List[str] = None) -> Dict[str, Any]:
            """
            A complex tool with dictionary and list parameters.
            
            :param data: Input data dictionary
            :param options: Optional configuration options
            :return: Result dictionary
            """
            result = {"processed": True, "input": data}
            if options:
                result["options"] = options
            return result
        
        self.simple_tool = simple_tool
        self.complex_tool = complex_tool
        
        # Create agent with our tools
        self.agent = OpenAIAgent(
            name="ToolTestAgent",
            description="Agent for testing tools",
            instructions="Test the tools",
            tools=[simple_tool, complex_tool],
            model_name="gpt-4",
            api_key="test_key"
        )
    
    def test_tool_parameter_extraction(self):
        """Test that the decorator correctly extracts parameter information."""
        # Check simple tool parameters
        self.assertTrue(hasattr(self.simple_tool, "parameters"))
        
        simple_params = self.simple_tool.parameters
        self.assertEqual(simple_params["type"], "object")
        self.assertEqual(len(simple_params["properties"]), 2)
        self.assertEqual(simple_params["properties"]["param1"]["type"], "string")
        self.assertEqual(simple_params["properties"]["param2"]["type"], "integer")
        self.assertEqual(len(simple_params["required"]), 1)
        self.assertIn("param1", simple_params["required"])
        
        # Check complex tool parameters
        self.assertTrue(hasattr(self.complex_tool, "parameters"))
        
        complex_params = self.complex_tool.parameters
        self.assertEqual(complex_params["type"], "object")
        self.assertEqual(len(complex_params["properties"]), 2)
        self.assertEqual(complex_params["properties"]["data"]["type"], "object")
        self.assertEqual(complex_params["properties"]["options"]["type"], "array")
        self.assertEqual(len(complex_params["required"]), 1)
        self.assertIn("data", complex_params["required"])
    
    def test_tool_docstring_extraction(self):
        """Test that parameter descriptions are extracted from docstrings."""
        simple_params = self.simple_tool.parameters
        self.assertIn("description", simple_params["properties"]["param1"])
        self.assertEqual(simple_params["properties"]["param1"]["description"], "The first parameter")
        self.assertIn("description", simple_params["properties"]["param2"])
        self.assertEqual(simple_params["properties"]["param2"]["description"], "The second parameter (optional)")
        
        complex_params = self.complex_tool.parameters
        self.assertIn("description", complex_params["properties"]["data"])
        self.assertEqual(complex_params["properties"]["data"]["description"], "Input data dictionary")
        self.assertIn("description", complex_params["properties"]["options"])
        self.assertEqual(complex_params["properties"]["options"]["description"], "Optional configuration options")
    
    @patch('openai.OpenAI')
    async def test_tool_conversion_in_agent(self, mock_openai_client):
        """Test that the agent correctly converts the decorated tools."""
        # Set up mocks for the OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        mock_message.content = "Test response"
        mock_message.tool_calls = None
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_response.id = "response_id"
        
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_client.return_value = mock_client
        
        # Run the agent to trigger tool conversion
        await self.agent.run("Hello")
        
        # Check that the client was called with the correctly formatted tools
        _, kwargs = mock_client.chat.completions.create.call_args
        tools = kwargs["tools"]
        
        # Verify structure of the converted tools
        self.assertEqual(len(tools), 2)
        
        simple_tool = next(t for t in tools if t["function"]["name"] == "simple_tool")
        self.assertEqual(simple_tool["type"], "function")
        self.assertEqual(simple_tool["function"]["description"], "A simple tool for testing.")
        self.assertEqual(len(simple_tool["function"]["parameters"]["properties"]), 2)
        
        complex_tool = next(t for t in tools if t["function"]["name"] == "complex_tool")
        self.assertEqual(complex_tool["type"], "function")
        self.assertEqual(complex_tool["function"]["description"], "A complex tool with dictionary and list parameters.")
        self.assertEqual(len(complex_tool["function"]["parameters"]["properties"]), 2)
    
    def test_tool_execution(self):
        """Test that the decorated functions can still be executed normally."""
        # Test simple tool
        result = self.simple_tool("test", 42)
        self.assertEqual(result, "Result: test - 42")
        
        # Test with default parameter
        result = self.simple_tool("test")
        self.assertEqual(result, "Result: test - 0")
        
        # Test complex tool
        data = {"key": "value"}
        options = ["option1", "option2"]
        result = self.complex_tool(data, options)
        
        self.assertTrue(result["processed"])
        self.assertEqual(result["input"], data)
        self.assertEqual(result["options"], options)
        
        # Test with default parameter
        result = self.complex_tool(data)
        self.assertTrue(result["processed"])
        self.assertEqual(result["input"], data)
        self.assertNotIn("options", result)


if __name__ == "__main__":
    unittest.main() 