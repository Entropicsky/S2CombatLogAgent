"""
Base Agent module for the multi-agent pipeline architecture.

This module defines the BaseAgent class that serves as the foundation for
all specialized agents in the pipeline. It provides common functionality
and standardized interfaces for agent interaction.
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable

from agents import Agent as OAIAgent, ModelSettings, Runner
from agents.tool import function_tool

from smite2_agent.pipeline.base.data_package import DataPackage

# Configure logging
logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents in the multi-agent pipeline architecture.
    
    This class serves as an abstraction layer over the OpenAI Agents SDK,
    providing a standardized interface for our pipeline architecture.
    """
    
    def __init__(
        self,
        name: str,
        instructions: str,
        model: str = "gpt-4o",
        tools: Optional[List[Callable]] = None,
        handoffs: Optional[List["BaseAgent"]] = None,
        handoff_description: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ):
        """
        Initialize a new BaseAgent.
        
        Args:
            name: Name of the agent
            instructions: Detailed instructions for the agent
            model: The model to use (default: "gpt-4o")
            tools: Optional list of tools available to the agent
            handoffs: Optional list of agents this agent can hand off to
            handoff_description: Optional description for handoff decisions
            temperature: Temperature setting for the model (default: 0.2)
            max_tokens: Maximum tokens for model responses (default: 4096)
        """
        self.name = name
        self.instructions = instructions
        self.model = model
        self.tools = tools or []
        self.handoffs = handoffs or []
        self.handoff_description = handoff_description
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.agent_id = f"{name.lower().replace(' ', '-')}-{str(uuid.uuid4())[:8]}"
        
        # Cache for the OAI agent instance
        self._oai_agent = None
    
    @property
    def oai_agent(self) -> OAIAgent:
        """
        Get the OpenAI Agents SDK agent instance.
        
        This is a cached property that creates the agent instance on first access.
        
        Returns:
            The OpenAI Agents SDK agent instance
        """
        if self._oai_agent is None:
            # Create model settings
            model_settings = ModelSettings(
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Convert our handoffs to OAI agents
            oai_handoffs = [handoff.oai_agent for handoff in self.handoffs]
            
            # Create the agent
            self._oai_agent = OAIAgent(
                name=self.name,
                instructions=self.instructions,
                model=self.model,
                model_settings=model_settings,
                tools=self.tools,
                handoffs=oai_handoffs,
                handoff_description=self.handoff_description
            )
        
        return self._oai_agent
    
    def as_tool(self, tool_name: str, tool_description: str) -> Callable:
        """
        Convert this agent to a tool that can be used by other agents.
        
        This implements the agents-as-tools pattern from the OpenAI examples.
        
        Args:
            tool_name: Name of the tool
            tool_description: Description of the tool
        
        Returns:
            A function that can be used as a tool
        """
        @function_tool(name_override=tool_name, description_override=tool_description)
        async def agent_tool(query: str) -> str:
            """
            Call this agent with a query.
            
            Args:
                query: The query to process
            
            Returns:
                The response from the agent
            """
            result = await self.process(query)
            return result.get_final_output()
        
        return agent_tool
    
    async def process(self, input_data: Union[str, DataPackage]) -> DataPackage:
        """
        Process input data and return a response package.
        
        This method can accept either a raw query string or a DataPackage.
        If a string is provided, it will be wrapped in a new DataPackage.
        
        Args:
            input_data: The input to process (string or DataPackage)
        
        Returns:
            The output DataPackage with the agent's response
        """
        # If input is a string, wrap it in a DataPackage
        if isinstance(input_data, str):
            data_package = DataPackage(query=input_data)
        else:
            data_package = input_data
        
        # Mark the start of processing
        data_package.start_processing(self.__class__.__name__, self.agent_id)
        
        try:
            # Call the implementation-specific process method
            output_package = await self._process(data_package)
            data_package.end_processing(success=True)
            return output_package
        
        except Exception as e:
            logger.exception(f"Error in agent {self.name}: {str(e)}")
            data_package.add_error(
                stage=self.__class__.__name__,
                error_type="agent_error",
                description=str(e),
                handled=False
            )
            data_package.end_processing(success=False)
            return data_package
    
    @abstractmethod
    async def _process(self, data_package: DataPackage) -> DataPackage:
        """
        Implementation-specific processing logic.
        
        This method must be implemented by subclasses to provide the
        agent-specific processing logic.
        
        Args:
            data_package: The input DataPackage
        
        Returns:
            The output DataPackage with the agent's response
        """
        pass


class OAIBaseAgent(BaseAgent):
    """
    Base agent implementation using the OpenAI Agents SDK.
    
    This class provides a concrete implementation of BaseAgent that uses
    the OpenAI Agents SDK to process inputs.
    """
    
    async def _process(self, data_package: DataPackage) -> DataPackage:
        """
        Process the input using the OpenAI Agents SDK.
        
        Args:
            data_package: The input DataPackage
        
        Returns:
            The output DataPackage with the agent's response
        """
        # Run the agent with the raw query
        query = data_package.to_dict()["input"]["raw_query"]
        result = await Runner.run(self.oai_agent, query)
        
        # Add the response to the data package
        if hasattr(result, 'final_output') and result.final_output:
            data_package.set_final_output(result.final_output)
        
        return data_package


class PipelineAgent(OAIBaseAgent):
    """
    Base class for specialized pipeline agents.
    
    This class provides additional functionality specific to agents that
    operate as part of the main analysis pipeline.
    """
    
    def __init__(
        self,
        name: str,
        instructions: str,
        model: str = "gpt-4o",
        tools: Optional[List[Callable]] = None,
        handoffs: Optional[List[BaseAgent]] = None,
        handoff_description: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        next_agent: Optional["PipelineAgent"] = None
    ):
        """
        Initialize a new PipelineAgent.
        
        Args:
            name: Name of the agent
            instructions: Detailed instructions for the agent
            model: The model to use (default: "gpt-4o")
            tools: Optional list of tools available to the agent
            handoffs: Optional list of agents this agent can hand off to
            handoff_description: Optional description for handoff decisions
            temperature: Temperature setting for the model (default: 0.2)
            max_tokens: Maximum tokens for model responses (default: 4096)
            next_agent: The next agent in the pipeline (default: None)
        """
        super().__init__(
            name=name,
            instructions=instructions,
            model=model,
            tools=tools,
            handoffs=handoffs,
            handoff_description=handoff_description,
            temperature=temperature,
            max_tokens=max_tokens
        )
        self.next_agent = next_agent
    
    async def _process(self, data_package: DataPackage) -> DataPackage:
        """
        Process the input and pass it to the next agent in the pipeline.
        
        Args:
            data_package: The input DataPackage
        
        Returns:
            The output DataPackage with the agent's response
        """
        # Process the input with this agent
        data_package = await super()._process(data_package)
        
        # Pass to the next agent if one exists
        if self.next_agent:
            return await self.next_agent.process(data_package)
        
        return data_package


def create_agent(
    agent_type: str,
    name: str,
    instructions: str,
    model: str = "gpt-4o",
    tools: Optional[List[Callable]] = None,
    handoffs: Optional[List[BaseAgent]] = None,
    handoff_description: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    next_agent: Optional[PipelineAgent] = None
) -> BaseAgent:
    """
    Factory function to create an agent of the specified type.
    
    Args:
        agent_type: Type of agent to create ("standard" or "pipeline")
        name: Name of the agent
        instructions: Detailed instructions for the agent
        model: The model to use (default: "gpt-4o")
        tools: Optional list of tools available to the agent
        handoffs: Optional list of agents this agent can hand off to
        handoff_description: Optional description for handoff decisions
        temperature: Temperature setting for the model (default: 0.2)
        max_tokens: Maximum tokens for model responses (default: 4096)
        next_agent: The next agent in the pipeline (for pipeline agents)
    
    Returns:
        The created agent
    """
    if agent_type == "pipeline":
        return PipelineAgent(
            name=name,
            instructions=instructions,
            model=model,
            tools=tools,
            handoffs=handoffs,
            handoff_description=handoff_description,
            temperature=temperature,
            max_tokens=max_tokens,
            next_agent=next_agent
        )
    else:
        return OAIBaseAgent(
            name=name,
            instructions=instructions,
            model=model,
            tools=tools,
            handoffs=handoffs,
            handoff_description=handoff_description,
            temperature=temperature,
            max_tokens=max_tokens
        ) 