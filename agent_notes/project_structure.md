# SMITE 2 Combat Log Agent - Project Structure

This document outlines the recommended project structure for implementing the SMITE 2 Combat Log Agent.

```
smite2_agent/
├── agents/                # Agent definitions and orchestration
│   ├── __init__.py
│   ├── base.py            # Base agent functionality
│   ├── orchestrator.py    # Orchestrator agent
│   ├── combat_agent.py    # Combat events specialist
│   ├── timeline_agent.py  # Timeline events specialist 
│   └── player_agent.py    # Player stats specialist
├── tools/                 # Shared function tools
│   ├── __init__.py
│   ├── sql_tools.py       # SQL query execution
│   ├── pandasai_tools.py  # PandasAI integration
│   └── chart_tools.py     # Visualization generation
├── db/                    # Database management
│   ├── __init__.py
│   ├── connection.py      # Connection management
│   ├── validators.py      # SQL validation
│   └── schema.py          # Schema definitions
├── ui/                    # Streamlit UI components
│   ├── __init__.py
│   ├── chat.py            # Chat interface
│   ├── file_upload.py     # Log file upload
│   └── visualizations.py  # Chart rendering
├── config/                # Configuration
│   ├── __init__.py
│   ├── settings.py        # Global settings
│   └── prompts.py         # Agent prompt templates
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── test_agents.py
│   ├── test_tools.py
│   ├── test_db.py
│   └── fixtures/          # Test data
├── utils/                 # Utility functions
│   ├── __init__.py
│   ├── logging.py         # Logging utilities
│   └── formatting.py      # Response formatting
├── app.py                 # Main Streamlit application
├── requirements.txt       # Dependencies
└── README.md              # Project documentation
```

## Directory Details

### agents/
Contains all agent definitions and orchestration logic. Each agent has its own module.

- **base.py**: Base classes and utilities for all agents
- **orchestrator.py**: Orchestrator agent that manages query planning and delegation
- **combat_agent.py**: Specialist for combat events and damage analysis
- **timeline_agent.py**: Specialist for timeline events and match progression
- **player_agent.py**: Specialist for player statistics and performance

### tools/
Function tools that agents can use to interact with data and generate outputs.

- **sql_tools.py**: SQL query execution with security validations
- **pandasai_tools.py**: PandasAI integration for natural language data analysis
- **chart_tools.py**: Visualization generation using Matplotlib/Plotly

### db/
Database connection and management utilities.

- **connection.py**: SQLite connection management with read-only enforcement
- **validators.py**: SQL query validation and sanitization
- **schema.py**: Database schema definitions and utilities

### ui/
Streamlit UI components separated by functionality.

- **chat.py**: Chat interface implementation
- **file_upload.py**: Combat log file upload and processing
- **visualizations.py**: Chart and data visualization rendering

### config/
Configuration settings and templates.

- **settings.py**: Global application settings
- **prompts.py**: Agent prompt templates and instructions

### tests/
Comprehensive test suite for all components.

- **test_agents.py**: Tests for agent functionality
- **test_tools.py**: Tests for function tools
- **test_db.py**: Tests for database operations
- **fixtures/**: Test data and fixtures

### utils/
Utility functions used across the application.

- **logging.py**: Logging utilities for agents and tools
- **formatting.py**: Response formatting utilities

## Key Files

- **app.py**: Main Streamlit application entry point
- **requirements.txt**: Project dependencies
- **README.md**: Project documentation 