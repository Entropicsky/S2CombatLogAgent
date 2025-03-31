"""
OpenAI Agent implementation using the OpenAI Agents API.

This module implements an agent using the OpenAI Agents SDK released in March 2025.
It supports function calling, handoffs to specialized agents, and memory management.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Callable, Union

from agents import Agent, ModelSettings, Runner, guardrail
from agents import tools
import openai

logger = logging.getLogger(__name__)

class OpenAIAgent:
    """
    Agent implementation using OpenAI's Agents SDK.
    
    This class wraps the OpenAI Agents SDK to provide a simpler interface
    for creating and running agents with function calling and handoffs.
    """
    
    def __init__(
        self,
        name: str,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        instructions: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        handoff_agents: Optional[List[Any]] = None,
        guardrails: Optional[List[Any]] = None,
    ):
        """
        Initialize the OpenAI agent.
        
        Args:
            name: Name of the agent
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI model to use
            instructions: Detailed instructions for the agent
            tools: List of function tools to make available to the agent
            handoff_agents: List of agents this agent can hand off to
            guardrails: List of guardrails to apply to agent inputs/outputs
        """
        self.name = name
        self.model_name = model
        
        # Set up API key
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        # Configure tools and handoffs
        self.tools = tools or []
        self.handoff_agents = handoff_agents or []
        self.guardrails = guardrails or []
        
        # Set up the client
        self.client = openai.OpenAI(api_key=self.api_key)
        
        # Create the agent
        self.agent = self._create_agent()
        
        # Set up the runner
        self.runner = Runner()
    
    def _create_agent(self) -> Agent:
        """
        Create an Agent instance using the Agents SDK.
        
        Returns:
            Agent: The configured agent
        """
        # Configure model settings
        model_settings = ModelSettings(
            temperature=0.2,  # Lower temperature for more deterministic responses
            max_tokens=4096,  # Reasonable length for detailed responses
            top_p=0.95
        )
        
        # Create the Agent with the Agents SDK
        agent = Agent(
            name=self.name,
            model=self.model_name,
            model_settings=model_settings,
            tools=self.tools,
            handoff_agents=self.handoff_agents,
            openai_client=self.client
        )
        
        return agent
    
    async def run(self, query: str) -> Dict[str, Any]:
        """
        Run the agent with a query.
        
        Args:
            query: The user's question or request
            
        Returns:
            Dict containing agent response with content and used tools
        """
        logger.info(f"Running agent '{self.name}' with query: {query}")
        
        try:
            # Run the agent using the Runner
            response = await self.runner.run_async(
                self.agent,
                query,
                guardrails=self.guardrails
            )
            
            # Extract relevant information from the response
            result = {
                "role": "assistant",
                "content": response.content,
                "tools_used": [tool.name for tool in response.tools_used] if response.tools_used else [],
                "trace_id": response.trace_id
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error running agent: {str(e)}")
            return {
                "role": "assistant",
                "content": f"I encountered an error: {str(e)}",
                "tools_used": [],
                "error": str(e)
            }
    
    def add_tool(self, tool: Any) -> None:
        """
        Add a new tool to the agent.
        
        Args:
            tool: The tool to add
        """
        self.tools.append(tool)
        # Recreate the agent with the updated tools
        self.agent = self._create_agent()
    
    def remove_tool(self, tool_name: str) -> None:
        """
        Remove a tool from the agent by name.
        
        Args:
            tool_name: Name of the tool to remove
        """
        self.tools = [tool for tool in self.tools 
                     if getattr(tool, "name", None) != tool_name]
        # Recreate the agent with the updated tools
        self.agent = self._create_agent()
    
    def add_handoff_agent(self, agent: Any) -> None:
        """
        Add a new agent that this agent can hand off to.
        
        Args:
            agent: The agent to add for handoffs
        """
        self.handoff_agents.append(agent)
        # Recreate the agent with the updated handoff agents
        self.agent = self._create_agent()
    
    def clear_handoff_agents(self) -> None:
        """Clear all handoff agents."""
        self.handoff_agents = []
        # Recreate the agent with the updated handoff agents
        self.agent = self._create_agent()

    @staticmethod
    def wrap_function_as_tool(func: Callable) -> Any:
        """
        Wrap a Python function as an OpenAI function tool.
        
        Args:
            func: Function to wrap
            
        Returns:
            Wrapped function tool
        """
        # Check if already wrapped
        if hasattr(func, "_function_tool"):
            return func
            
        # Use the function_tool decorator from agents package
        return tools.function_tool(func)

# Specialist agent factory
def create_specialist_agent(
    name: str,
    domain: str,
    instructions: str,
    model_name: str = "gpt-4o",
    api_key: Optional[str] = None,
    tools: Optional[List[Any]] = None
) -> 'OpenAIAgent':
    """
    Create a specialist agent for a specific domain.
    
    Args:
        name: Name prefix for the agent
        domain: Domain of specialization
        instructions: Detailed instructions for the agent
        model_name: OpenAI model to use
        api_key: OpenAI API key
        tools: List of function tools
        
    Returns:
        Configured specialist agent
    """
    return OpenAIAgent(
        name=f"{name}Agent",
        api_key=api_key,
        model=model_name,
        instructions=instructions,
        tools=tools
    )

# Orchestrator agent factory
def create_orchestrator_agent(
    specialists: List['OpenAIAgent'],
    instructions: str,
    model_name: str = "gpt-4o",
    api_key: Optional[str] = None,
    tools: Optional[List[Any]] = None
) -> 'OpenAIAgent':
    """
    Create an orchestrator agent that can delegate to specialists.
    
    Args:
        specialists: List of specialist agents
        instructions: Detailed instructions for the orchestrator
        model_name: OpenAI model to use
        api_key: OpenAI API key
        tools: List of function tools
        
    Returns:
        Configured orchestrator agent
    """
    # Create instructions for the orchestrator
    specialist_names = "\n".join([
        f"- {agent.name}" 
        for agent in specialists
    ])
    
    full_instructions = f"""
    {instructions}
    
    You can delegate to these specialist agents:
    {specialist_names}
    """
    
    orchestrator = OpenAIAgent(
        name="OrchestratorAgent",
        api_key=api_key,
        model=model_name,
        instructions=full_instructions,
        tools=tools,
        handoff_agents=specialists
    )
    
    return orchestrator 