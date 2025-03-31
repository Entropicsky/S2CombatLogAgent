"""
Pipeline module for managing agent workflows.

This module defines the Pipeline class that orchestrates the flow of data
between specialized agents in the analysis pipeline.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Type, Union

from smite2_agent.pipeline.base.agent import BaseAgent, PipelineAgent
from smite2_agent.pipeline.base.data_package import DataPackage

# Configure logging
logger = logging.getLogger(__name__)


class Pipeline:
    """
    Orchestrates the flow of data between agents in the analysis pipeline.
    
    The Pipeline manages the execution of specialized agents in sequence,
    with error handling and performance monitoring.
    """
    
    def __init__(
        self,
        orchestrator: BaseAgent,
        domain_pipelines: Optional[Dict[str, List[BaseAgent]]] = None,
        max_retries: int = 1,
        timeout: float = 60.0,
    ):
        """
        Initialize a new Pipeline.
        
        Args:
            orchestrator: The orchestrator agent that routes queries
            domain_pipelines: Optional mapping of domain names to lists of domain-specific agents
            max_retries: Maximum number of retries for failed agent steps (default: 1)
            timeout: Maximum time in seconds to wait for a response (default: 60.0)
        """
        self.orchestrator = orchestrator
        self.domain_pipelines = domain_pipelines or {}
        self.max_retries = max_retries
        self.timeout = timeout
    
    async def process(self, query: str) -> DataPackage:
        """
        Process a query through the pipeline.
        
        Args:
            query: The user's query string
        
        Returns:
            The final DataPackage with the complete response
        """
        start_time = time.time()
        logger.info(f"Processing query: {query}")
        
        # Create initial data package
        data_package = DataPackage(query=query)
        
        try:
            # Start with the orchestrator
            result_package = await self._run_with_timeout(
                self.orchestrator.process(data_package),
                self.timeout
            )
            
            # Check processing time
            elapsed = time.time() - start_time
            logger.info(f"Pipeline completed in {elapsed:.2f} seconds")
            
            return result_package
        
        except asyncio.TimeoutError:
            logger.error(f"Pipeline timed out after {self.timeout} seconds")
            data_package.add_error(
                stage="pipeline",
                error_type="timeout",
                description=f"Pipeline execution timed out after {self.timeout} seconds",
                handled=True,
                recovery_action="Returning partial results"
            )
            return data_package
        
        except Exception as e:
            logger.exception(f"Pipeline error: {str(e)}")
            data_package.add_error(
                stage="pipeline",
                error_type="pipeline_error",
                description=str(e),
                handled=True,
                recovery_action="Failed to process query"
            )
            return data_package
    
    async def _run_with_timeout(self, coro, timeout: float):
        """
        Run a coroutine with a timeout.
        
        Args:
            coro: The coroutine to run
            timeout: Maximum time in seconds to wait
        
        Returns:
            The result of the coroutine
        
        Raises:
            asyncio.TimeoutError: If the coroutine times out
        """
        return await asyncio.wait_for(coro, timeout=timeout)
    
    async def _run_with_retry(self, agent: BaseAgent, data_package: DataPackage) -> DataPackage:
        """
        Run an agent with retry logic.
        
        Args:
            agent: The agent to run
            data_package: The input DataPackage
        
        Returns:
            The output DataPackage
        """
        retries = 0
        while retries <= self.max_retries:
            try:
                return await agent.process(data_package)
            except Exception as e:
                retries += 1
                if retries > self.max_retries:
                    raise e
                logger.warning(f"Agent {agent.name} failed, retry {retries}/{self.max_retries}: {str(e)}")
                # Short delay before retry
                await asyncio.sleep(0.5)
    
    @classmethod
    def create_sequential_pipeline(
        cls,
        agents: List[PipelineAgent],
        max_retries: int = 1,
        timeout: float = 60.0,
    ) -> "Pipeline":
        """
        Create a sequential pipeline from a list of agents.
        
        This creates a simple pipeline where each agent passes its output
        to the next agent in sequence.
        
        Args:
            agents: List of agents in processing order
            max_retries: Maximum number of retries for failed agent steps
            timeout: Maximum time in seconds to wait for a response
        
        Returns:
            A new Pipeline instance
        """
        if not agents:
            raise ValueError("At least one agent is required")
        
        # Set up next_agent references for sequential flow
        for i in range(len(agents) - 1):
            agents[i].next_agent = agents[i + 1]
        
        # The first agent is the orchestrator in this simple case
        return cls(
            orchestrator=agents[0],
            max_retries=max_retries,
            timeout=timeout
        )


def create_pipeline(
    query_analyst: Optional[BaseAgent] = None,
    data_engineer: Optional[BaseAgent] = None,
    data_analyst: Optional[BaseAgent] = None,
    visualization_specialist: Optional[BaseAgent] = None,
    response_composer: Optional[BaseAgent] = None,
    quality_reviewer: Optional[BaseAgent] = None,
    orchestrator: Optional[BaseAgent] = None,
    domain_pipelines: Optional[Dict[str, List[BaseAgent]]] = None,
    max_retries: int = 1,
    timeout: float = 60.0,
) -> Pipeline:
    """
    Create a complete analysis pipeline.
    
    This factory function creates a pipeline with all the specialized agents
    for the SMITE 2 Combat Log Agent.
    
    Args:
        query_analyst: The Query Analyst agent
        data_engineer: The Data Engineer agent
        data_analyst: The Data Analyst agent
        visualization_specialist: The Visualization Specialist agent
        response_composer: The Response Composer agent
        quality_reviewer: The Quality Reviewer agent
        orchestrator: The Orchestrator agent
        domain_pipelines: Optional mapping of domain names to lists of domain-specific agents
        max_retries: Maximum number of retries for failed agent steps
        timeout: Maximum time in seconds to wait for a response
    
    Returns:
        A new Pipeline instance
    """
    # Create default agents if not provided
    # (These would be implemented in specialized agent modules)
    
    # For now, if all agents are None, raise an error
    if all(agent is None for agent in [
        query_analyst, data_engineer, data_analyst,
        visualization_specialist, response_composer, quality_reviewer, orchestrator
    ]):
        raise ValueError("At least one agent must be provided")
    
    # If orchestrator is not provided but others are, use a sequential pipeline
    if orchestrator is None and any(agent is not None for agent in [
        query_analyst, data_engineer, data_analyst,
        visualization_specialist, response_composer, quality_reviewer
    ]):
        # Collect all non-None agents in order
        agents = []
        for agent in [
            query_analyst, data_engineer, data_analyst,
            visualization_specialist, response_composer, quality_reviewer
        ]:
            if agent is not None:
                agents.append(agent)
        
        return Pipeline.create_sequential_pipeline(
            agents=agents,
            max_retries=max_retries,
            timeout=timeout
        )
    
    # Otherwise, use the provided orchestrator
    return Pipeline(
        orchestrator=orchestrator,
        domain_pipelines=domain_pipelines,
        max_retries=max_retries,
        timeout=timeout
    ) 