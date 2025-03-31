"""
Base agent implementations for the multi-agent system.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Exception raised for agent-related errors."""
    pass


class BaseAgent:
    """
    Base class for all agents in the system.
    
    This provides common functionality and interfaces for all agents.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        instructions: str,
        tools: List[Callable] = None,
        model_name: str = None,
        api_key: str = None,
    ):
        """
        Initialize a base agent.
        
        Args:
            name: Agent name
            description: Short description of the agent's role
            instructions: Detailed instructions for the agent
            tools: List of tools available to the agent
            model_name: LLM model name to use
            api_key: OpenAI API key (optional)
        """
        self.name = name
        self.description = description
        self.instructions = instructions
        self.tools = tools or []
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        # Validate required settings
        if not self.api_key:
            raise AgentError("No API key provided. Set the OPENAI_API_KEY environment variable.")
    
    def add_tool(self, tool: Callable):
        """
        Add a tool to the agent.
        
        Args:
            tool: Tool function to add
        """
        if tool not in self.tools:
            self.tools.append(tool)
    
    def remove_tool(self, tool: Callable):
        """
        Remove a tool from the agent.
        
        Args:
            tool: Tool function to remove
        """
        if tool in self.tools:
            self.tools.remove(tool)
    
    def get_tools(self) -> List[Callable]:
        """
        Get the list of tools available to the agent.
        
        Returns:
            List of tool functions
        """
        return self.tools
    
    def create_agent_config(self) -> Dict[str, Any]:
        """
        Create configuration dictionary for OpenAI Agents API.
        
        Returns:
            Dictionary with agent configuration
        """
        return {
            "name": self.name,
            "description": self.description,
            "instructions": self.instructions,
            "model": self.model_name,
            "tools": self.tools,
        }
    
    async def run(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run the agent with user input.
        
        This method should be implemented by subclasses.
        
        Args:
            user_input: User's query or message
            context: Additional context for the agent (optional)
            
        Returns:
            Dictionary with agent response and metadata
            
        Raises:
            NotImplementedError: If not implemented by a subclass
        """
        raise NotImplementedError("Subclasses must implement run method") 