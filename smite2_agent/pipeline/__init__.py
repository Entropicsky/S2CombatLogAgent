"""
SMITE 2 Combat Log Agent - Pipeline Architecture

This package implements the multi-agent pipeline architecture for analyzing
SMITE 2 combat logs through natural language queries.
"""

__version__ = "0.1.0"

# Import base components
from smite2_agent.pipeline.base.data_package import DataPackage
from smite2_agent.pipeline.base.agent import (
    BaseAgent,
    OAIBaseAgent,
    PipelineAgent,
    create_agent,
)
from smite2_agent.pipeline.base.pipeline import Pipeline, create_pipeline

