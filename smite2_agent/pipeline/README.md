# SMITE 2 Combat Log Agent - Pipeline Architecture

This directory contains the implementation of the multi-agent pipeline architecture for the SMITE 2 Combat Log Agent.

## Directory Structure

- **base/**: Contains base classes for the pipeline architecture
  - `agent.py`: Base Agent class with common functionality
  - `data_package.py`: Data Package implementation for inter-agent communication
  - `pipeline.py`: Pipeline manager for orchestrating agent workflow

- **agents/**: Contains implementations of specialized agents
  - `orchestrator.py`: Orchestrator Agent that routes queries
  - `query_analyst.py`: Query Analyst Agent that formulates SQL queries
  - `data_engineer.py`: Data Engineer Agent that executes queries
  - `data_analyst.py`: Data Analyst Agent that analyzes results
  - `visualization.py`: Visualization Specialist Agent that creates charts
  - `response_composer.py`: Response Composer Agent that formats output
  - `quality_reviewer.py`: Quality Reviewer Agent that polishes responses

- **tools/**: Contains tools used by the agents
  - `database_tools.py`: Tools for database interaction
  - `analysis_tools.py`: Tools for data analysis
  - `visualization_tools.py`: Tools for creating visualizations
  - `formatting_tools.py`: Tools for response formatting
  - `review_tools.py`: Tools for content review and polishing

- **utils/**: Contains utility functions and helpers
  - `serialization.py`: Utilities for serializing/deserializing data packages
  - `validation.py`: Validation utilities for input/output
  - `caching.py`: Caching utilities for improved performance
  - `error_handling.py`: Error handling and recovery utilities

## Implementation Notes

The implementation follows the architecture specified in `agent_notes/agent_techspec.md`, using the OpenAI Agents SDK for agent creation and orchestration.

Key aspects of the implementation:
- Standardized data packages for communication between agents
- Specialized agent roles with focused instructions
- Domain-specific knowledge embedded in each agent
- Robust error handling and fallback mechanisms
- Caching for improved performance

## Usage

```python
from smite2_agent.pipeline import create_pipeline

# Create the pipeline with all specialized agents
pipeline = create_pipeline()

# Process a user query
result = pipeline.process("Who dealt the most damage in the match?")

# Display the formatted response
print(result.formatted_response)
```

## Development Status

Refer to `agent_notes/project_checklist.md` for the current development status of each component. 