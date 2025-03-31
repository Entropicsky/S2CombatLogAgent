"""
Tests for the OpenAI Agent implementation.
"""

import os
import unittest
import asyncio
import json
from unittest.mock import patch, MagicMock

import pytest

from smite2_agent.agents.base import BaseAgent, AgentError
from smite2_agent.agents.openai_agent import OpenAIAgent


class TestOpenAIAgent(unittest.TestCase):
    """Test suite for the OpenAI Agent."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.api_key = "test_api_key"
        self.mock_tool = MagicMock()
        self.mock_tool.__name__ = "mock_tool"
        self.mock_tool.__doc__ = "Mock tool for testing"
        self.mock_tool.parameters = {
            "type": "object",
            "properties": {
                "param": {
                    "type": "string",
                    "description": "Test parameter"
                }
            }
        }
        
        # Create an agent with our mock tool
        self.agent = OpenAIAgent(
            name="TestAgent",
            description="Test agent for unit tests",
            instructions="You are a test agent. Answer with 'test'.",
            tools=[self.mock_tool],
            model_name="gpt-4",
            api_key=self.api_key
        )
    
    def test_initialization(self):
        """Test that the agent initializes correctly."""
        # Check basic properties
        self.assertEqual(self.agent.name, "TestAgent")
        self.assertEqual(self.agent.description, "Test agent for unit tests")
        self.assertEqual(self.agent.instructions, "You are a test agent. Answer with 'test'.")
        self.assertEqual(self.agent.model_name, "gpt-4")
        self.assertEqual(self.agent.api_key, self.api_key)
        
        # Check tools
        self.assertEqual(len(self.agent.tools), 1)
        self.assertIs(self.agent.tools[0], self.mock_tool)
        
        # Check empty conversation history
        self.assertEqual(self.agent.messages, [])
    
    def test_message_management(self):
        """Test adding and clearing messages."""
        # Test adding messages
        self.agent.add_message("user", "Hello")
        self.agent.add_message("assistant", "Hi there")
        
        self.assertEqual(len(self.agent.messages), 2)
        self.assertEqual(self.agent.messages[0], {"role": "user", "content": "Hello"})
        self.assertEqual(self.agent.messages[1], {"role": "assistant", "content": "Hi there"})
        
        # Test clearing history
        self.agent.clear_history()
        self.assertEqual(len(self.agent.messages), 0)
    
    def test_prepare_messages(self):
        """Test preparation of messages for API call."""
        # Add some history
        self.agent.add_message("user", "Hello")
        self.agent.add_message("assistant", "Hi there")
        
        # Prepare messages with new input
        messages = self.agent._prepare_messages("How are you?")
        
        # Check result
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[0], {"role": "system", "content": self.agent.instructions})
        self.assertEqual(messages[1], {"role": "user", "content": "Hello"})
        self.assertEqual(messages[2], {"role": "assistant", "content": "Hi there"})
        self.assertEqual(messages[3], {"role": "user", "content": "How are you?"})
    
    def test_convert_tools_to_openai_format(self):
        """Test conversion of tool functions to OpenAI format."""
        tools = self.agent._convert_tools_to_openai_format()
        
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["type"], "function")
        self.assertEqual(tools[0]["function"]["name"], "mock_tool")
        self.assertEqual(tools[0]["function"]["description"], "Mock tool for testing")
        self.assertEqual(tools[0]["function"]["parameters"], self.mock_tool.parameters)
    
    @patch('openai.OpenAI')
    async def test_run_simple_query(self, mock_openai_client):
        """Test running a simple query that doesn't use tools."""
        # Set up mock response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        mock_message.content = "This is a test response"
        mock_message.tool_calls = None
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_response.id = "test_response_id"
        
        # Set up the mock client to return our response
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_client.return_value = mock_client
        
        # Run the agent
        result = await self.agent.run("Hello, test agent!")
        
        # Check that the client was called correctly
        mock_client.chat.completions.create.assert_called_once()
        args, kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(kwargs["model"], "gpt-4")
        self.assertIsNotNone(kwargs["messages"])
        self.assertEqual(kwargs["tools"][0]["function"]["name"], "mock_tool")
        
        # Check result
        self.assertEqual(result["content"], "This is a test response")
        self.assertEqual(result["role"], "assistant")
        self.assertEqual(result["id"], "test_response_id")
        self.assertEqual(result["finish_reason"], "stop")
        self.assertEqual(result["tools_used"], [])
        
        # Check that message was added to history
        self.assertEqual(len(self.agent.messages), 2)
        self.assertEqual(self.agent.messages[0], {"role": "user", "content": "Hello, test agent!"})
        self.assertEqual(self.agent.messages[1], {"role": "assistant", "content": "This is a test response"})
    
    @patch('openai.OpenAI')
    async def test_run_with_tool_calls(self, mock_openai_client):
        """Test running a query that uses tools."""
        # Set up mock response with tool calls
        first_response = MagicMock()
        first_choice = MagicMock()
        first_message = MagicMock()
        first_tool_call = MagicMock()
        
        first_tool_call.id = "tool_call_1"
        first_tool_call.function.name = "mock_tool"
        first_tool_call.function.arguments = json.dumps({"param": "test_value"})
        
        first_message.content = "I'll help you with that."
        first_message.tool_calls = [first_tool_call]
        first_choice.message = first_message
        first_choice.finish_reason = "tool_calls"
        first_response.choices = [first_choice]
        first_response.id = "first_response_id"
        
        # Set up mock response after tool call
        second_response = MagicMock()
        second_choice = MagicMock()
        second_message = MagicMock()
        
        second_message.content = "Here's the result of the tool call."
        second_message.tool_calls = None
        second_choice.message = second_message
        second_choice.finish_reason = "stop"
        second_response.choices = [second_choice]
        second_response.id = "second_response_id"
        
        # Set up the mock client to return our responses in sequence
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [first_response, second_response]
        mock_openai_client.return_value = mock_client
        
        # Set up the mock tool to return a result
        self.mock_tool.return_value = "mock_tool_result"
        
        # Run the agent
        result = await self.agent.run("Use the tool please.")
        
        # Check that the client was called twice
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)
        
        # Check that the tool was called with the right arguments
        self.mock_tool.assert_called_once_with(param="test_value")
        
        # Check result is from the second response
        self.assertEqual(result["content"], "Here's the result of the tool call.")
        self.assertEqual(result["role"], "assistant")
        self.assertEqual(result["id"], "second_response_id")
        self.assertEqual(result["finish_reason"], "stop")
        self.assertEqual(result["tools_used"], ["mock_tool"])
        
        # Check that all messages were added to history
        self.assertEqual(len(self.agent.messages), 4)
        self.assertEqual(self.agent.messages[0], {"role": "user", "content": "Use the tool please."})
        self.assertEqual(self.agent.messages[1], {"role": "assistant", "content": "I'll help you with that."})
        # The third message should be the tool response
        self.assertEqual(self.agent.messages[2]["role"], "tool")
        tool_message = json.loads(self.agent.messages[2]["content"])
        self.assertEqual(tool_message["tool_call_id"], "tool_call_1")
        self.assertEqual(tool_message["name"], "mock_tool")
        self.assertEqual(tool_message["result"], "mock_tool_result")
        # The fourth message should be the final assistant response
        self.assertEqual(self.agent.messages[3], {"role": "assistant", "content": "Here's the result of the tool call."})
    
    @patch('openai.OpenAI')
    async def test_run_with_error_handling(self, mock_openai_client):
        """Test error handling during agent execution."""
        # Set up the mock client to raise an exception
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_openai_client.return_value = mock_client
        
        # Run the agent
        result = await self.agent.run("This should fail.")
        
        # Check error response
        self.assertEqual(result["role"], "error")
        self.assertEqual(result["error"], "API error")
        self.assertEqual(result["error_type"], "Exception")
        self.assertTrue(result["content"].startswith("Error:"))
    
    def test_add_remove_tools(self):
        """Test adding and removing tools from the agent."""
        # Create a new mock tool
        new_tool = MagicMock()
        new_tool.__name__ = "new_tool"
        
        # Test adding a tool
        self.agent.add_tool(new_tool)
        self.assertEqual(len(self.agent.tools), 2)
        self.assertIn(new_tool, self.agent.tools)
        
        # Test removing a tool
        self.agent.remove_tool(new_tool)
        self.assertEqual(len(self.agent.tools), 1)
        self.assertNotIn(new_tool, self.agent.tools)
        
        # Test removing a non-existent tool (should not raise an error)
        self.agent.remove_tool(new_tool)
        self.assertEqual(len(self.agent.tools), 1)


if __name__ == "__main__":
    unittest.main() 