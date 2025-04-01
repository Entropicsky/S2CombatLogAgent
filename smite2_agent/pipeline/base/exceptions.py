"""Exceptions used by the agent pipeline.

This module defines custom exceptions used by the agent pipeline architecture.
"""

class AgentExecutionError(Exception):
    """Exception raised when there is an error during agent execution."""
    pass


class ModelUnavailableError(Exception):
    """Exception raised when the specified model is not available."""
    pass