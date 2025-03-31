"""
Tests for agent handoff mechanism.
"""

import unittest
import json
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from smite2_agent.agents.openai_agent import OpenAIAgent


class TestAgentHandoff(unittest.TestCase):
    """Test suite for agent handoff mechanisms."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.api_key = "test_api_key"
        
        # Create orchestrator agent
        self.orchestrator = OpenAIAgent(
            name="OrchestratorAgent",
            description="Main agent that orchestrates specialized agents",
            instructions="You are the main agent. Hand off complex tasks to specialized agents.",
            model_name="gpt-4",
            api_key=self.api_key
        )
        
        # Create specialized agents
        self.combat_agent = OpenAIAgent(
            name="CombatEventsAgent",
            description="Specialized agent for combat data analysis",
            instructions="You analyze combat events data.",
            model_name="gpt-4",
            api_key=self.api_key
        )
        
        self.timeline_agent = OpenAIAgent(
            name="TimelineEventsAgent",
            description="Specialized agent for timeline analysis",
            instructions="You analyze match timeline data.",
            model_name="gpt-4",
            api_key=self.api_key
        )
        
        # Define a simple handoff tool
        def handoff_to_agent(agent_name: str, query: str):
            """
            Hand off the query to a specialized agent.
            
            Args:
                agent_name: Name of the agent to hand off to
                query: The query to hand off
                
            Returns:
                Dict with the specialized agent's response
            """
            if agent_name == "CombatEventsAgent":
                return self.combat_agent_response
            elif agent_name == "TimelineEventsAgent":
                return self.timeline_agent_response
            else:
                return {"content": f"Agent {agent_name} not found", "role": "error"}
        
        # Add parameter schema to the function
        handoff_to_agent.parameters = {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Name of the agent to hand off to"
                },
                "query": {
                    "type": "string",
                    "description": "The query to hand off"
                }
            },
            "required": ["agent_name", "query"]
        }
        
        # Add tool to orchestrator
        self.orchestrator.add_tool(handoff_to_agent)
        
        # Prepare mock responses
        self.combat_agent_response = {
            "content": "Combat analysis result: Player1 dealt 5000 damage in total.",
            "role": "assistant"
        }
        self.timeline_agent_response = {
            "content": "Timeline analysis: The match had 3 major teamfights at 5:30, 12:45, and 18:20.",
            "role": "assistant"
        }
    
    @patch('openai.OpenAI')
    async def test_orchestrator_direct_response(self, mock_openai_client):
        """Test the orchestrator responding directly to a simple query."""
        # Set up mock client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        mock_message.content = "This is a simple query that I can handle directly."
        mock_message.tool_calls = None
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_client.return_value = mock_client
        
        # Run the orchestrator with a simple query
        result = await self.orchestrator.run("What is the purpose of this application?")
        
        # Check result
        self.assertEqual(result["content"], "This is a simple query that I can handle directly.")
        self.assertEqual(result["role"], "assistant")
        self.assertEqual(result["tools_used"], [])
    
    @patch('openai.OpenAI')
    async def test_orchestrator_handoff_to_combat_agent(self, mock_openai_client):
        """Test the orchestrator handing off to the combat agent."""
        # Set up mock client with two responses:
        # 1. First call decides to hand off
        # 2. Second call processes the result of the handoff
        
        # First response - agent decides to hand off
        first_response = MagicMock()
        first_choice = MagicMock()
        first_message = MagicMock()
        first_tool_call = MagicMock()
        
        first_tool_call.id = "tool_call_1"
        first_tool_call.function.name = "handoff_to_agent"
        first_tool_call.function.arguments = json.dumps({
            "agent_name": "CombatEventsAgent",
            "query": "Who dealt the most damage in the match?"
        })
        
        first_message.content = "I'll hand this combat question to our specialist."
        first_message.tool_calls = [first_tool_call]
        first_choice.message = first_message
        first_choice.finish_reason = "tool_calls"
        first_response.choices = [first_choice]
        first_response.id = "first_response_id"
        
        # Second response - agent processes the result
        second_response = MagicMock()
        second_choice = MagicMock()
        second_message = MagicMock()
        
        second_message.content = "According to our combat specialist, Player1 dealt 5000 damage in total, which was the highest."
        second_message.tool_calls = None
        second_choice.message = second_message
        second_choice.finish_reason = "stop"
        second_response.choices = [second_choice]
        second_response.id = "second_response_id"
        
        # Set up mock client
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [first_response, second_response]
        mock_openai_client.return_value = mock_client
        
        # Run the orchestrator with a combat query
        result = await self.orchestrator.run("Who dealt the most damage in the match?")
        
        # Check result
        self.assertEqual(result["content"], "According to our combat specialist, Player1 dealt 5000 damage in total, which was the highest.")
        self.assertEqual(result["role"], "assistant")
        self.assertEqual(result["tools_used"], ["handoff_to_agent"])
        
        # Check conversation flow
        self.assertEqual(len(self.orchestrator.messages), 4)
        self.assertEqual(self.orchestrator.messages[0]["role"], "user")
        self.assertEqual(self.orchestrator.messages[1]["role"], "assistant")
        
        # The third message should be the tool response with the combat agent's response
        self.assertEqual(self.orchestrator.messages[2]["role"], "tool")
        tool_content = json.loads(self.orchestrator.messages[2]["content"])
        self.assertEqual(tool_content["name"], "handoff_to_agent")
        self.assertEqual(tool_content["result"]["content"], "Combat analysis result: Player1 dealt 5000 damage in total.")
        
        # The fourth message should be the final response
        self.assertEqual(self.orchestrator.messages[3]["role"], "assistant")
    
    @patch('openai.OpenAI')
    async def test_orchestrator_handoff_to_timeline_agent(self, mock_openai_client):
        """Test the orchestrator handing off to the timeline agent."""
        # Set up mock client similar to previous test
        first_response = MagicMock()
        first_choice = MagicMock()
        first_message = MagicMock()
        first_tool_call = MagicMock()
        
        first_tool_call.id = "tool_call_1"
        first_tool_call.function.name = "handoff_to_agent"
        first_tool_call.function.arguments = json.dumps({
            "agent_name": "TimelineEventsAgent",
            "query": "When did the major teamfights occur?"
        })
        
        first_message.content = "I'll hand this timeline question to our specialist."
        first_message.tool_calls = [first_tool_call]
        first_choice.message = first_message
        first_choice.finish_reason = "tool_calls"
        first_response.choices = [first_choice]
        first_response.id = "first_response_id"
        
        second_response = MagicMock()
        second_choice = MagicMock()
        second_message = MagicMock()
        
        second_message.content = "Based on our timeline analysis, there were 3 major teamfights at 5:30, 12:45, and 18:20."
        second_message.tool_calls = None
        second_choice.message = second_message
        second_choice.finish_reason = "stop"
        second_response.choices = [second_choice]
        second_response.id = "second_response_id"
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [first_response, second_response]
        mock_openai_client.return_value = mock_client
        
        # Run the orchestrator with a timeline query
        result = await self.orchestrator.run("When did the major teamfights occur?")
        
        # Check result
        self.assertEqual(result["content"], "Based on our timeline analysis, there were 3 major teamfights at 5:30, 12:45, and 18:20.")
        self.assertEqual(result["role"], "assistant")
        self.assertEqual(result["tools_used"], ["handoff_to_agent"])
        
        # Check the handoff was to the timeline agent
        tool_content = json.loads(self.orchestrator.messages[2]["content"])
        self.assertEqual(tool_content["result"]["content"], "Timeline analysis: The match had 3 major teamfights at 5:30, 12:45, and 18:20.")
    
    @patch('openai.OpenAI')
    async def test_orchestrator_multiple_handoffs(self, mock_openai_client):
        """Test the orchestrator making multiple handoffs for a complex query."""
        # Set up mock client with three responses:
        # 1. First call decides to hand off to combat agent
        # 2. Second call processes the result and decides to hand off to timeline agent
        # 3. Third call combines both results
        
        # First response - agent decides to hand off to combat agent
        first_response = MagicMock()
        first_choice = MagicMock()
        first_message = MagicMock()
        first_tool_call = MagicMock()
        
        first_tool_call.id = "tool_call_1"
        first_tool_call.function.name = "handoff_to_agent"
        first_tool_call.function.arguments = json.dumps({
            "agent_name": "CombatEventsAgent",
            "query": "Who dealt the most damage in the match?"
        })
        
        first_message.content = "Let me check damage stats first."
        first_message.tool_calls = [first_tool_call]
        first_choice.message = first_message
        first_choice.finish_reason = "tool_calls"
        first_response.choices = [first_choice]
        first_response.id = "first_response_id"
        
        # Second response - agent processes combat result and hands off to timeline agent
        second_response = MagicMock()
        second_choice = MagicMock()
        second_message = MagicMock()
        second_tool_call = MagicMock()
        
        second_tool_call.id = "tool_call_2"
        second_tool_call.function.name = "handoff_to_agent"
        second_tool_call.function.arguments = json.dumps({
            "agent_name": "TimelineEventsAgent",
            "query": "When did the major teamfights occur?"
        })
        
        second_message.content = "Now I need timeline information."
        second_message.tool_calls = [second_tool_call]
        second_choice.message = second_message
        second_choice.finish_reason = "tool_calls"
        second_response.choices = [second_choice]
        second_response.id = "second_response_id"
        
        # Third response - agent combines both results
        third_response = MagicMock()
        third_choice = MagicMock()
        third_message = MagicMock()
        
        third_message.content = "Player1 dealt the most damage (5000 points) across three major teamfights at 5:30, 12:45, and 18:20."
        third_message.tool_calls = None
        third_choice.message = third_message
        third_choice.finish_reason = "stop"
        third_response.choices = [third_choice]
        third_response.id = "third_response_id"
        
        # Set up mock client
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [first_response, second_response, third_response]
        mock_openai_client.return_value = mock_client
        
        # Run the orchestrator with a complex query
        result = await self.orchestrator.run("Who dealt the most damage and when did the major fights happen?")
        
        # Check result
        self.assertEqual(result["content"], "Player1 dealt the most damage (5000 points) across three major teamfights at 5:30, 12:45, and 18:20.")
        self.assertEqual(result["role"], "assistant")
        self.assertEqual(result["tools_used"], ["handoff_to_agent", "handoff_to_agent"])
        
        # Check conversation flow
        self.assertEqual(len(self.orchestrator.messages), 6)
        self.assertEqual(self.orchestrator.messages[0]["role"], "user")
        self.assertEqual(self.orchestrator.messages[1]["role"], "assistant")
        self.assertEqual(self.orchestrator.messages[2]["role"], "tool")
        self.assertEqual(self.orchestrator.messages[3]["role"], "assistant")
        self.assertEqual(self.orchestrator.messages[4]["role"], "tool")
        self.assertEqual(self.orchestrator.messages[5]["role"], "assistant")


if __name__ == "__main__":
    unittest.main() 