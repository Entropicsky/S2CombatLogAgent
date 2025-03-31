# SMITE 2 Combat Log Agent

An advanced AI-powered analysis tool for SMITE 2 combat logs. This agent uses natural language processing to analyze game data, answer questions, and provide insights about player performance, combat statistics, and match events.

## Overview

The SMITE 2 Combat Log Agent is a multi-agent AI system that allows players to analyze their combat logs using natural language queries. Instead of writing complex SQL queries or manually analyzing data, users can simply ask questions like:

- "Who dealt the most damage in the match?"
- "What abilities did psychotic8BALL use to achieve the highest damage output?"
- "How did MateoUwU's damage compare to Taco's throughout the match?"

The system processes these questions, extracts relevant data from the combat log database, and provides comprehensive answers with exact numerical values, comparisons, and insights.

## Features

- **Natural Language Query Processing**: Ask questions in plain English about your SMITE 2 matches
- **Data-Driven Answers**: Get precise, factual responses based on actual game data
- **Intelligent Follow-up Questions**: The system automatically suggests and answers follow-up questions
- **Interactive Web Interface**: Easy-to-use Streamlit application for uploading logs and asking questions
- **Comprehensive Analysis**: Detailed breakdowns of damage, abilities, player performance, and more

## Architecture

The SMITE 2 Combat Log Agent uses a sophisticated multi-agent pipeline architecture:

### Core Pipeline

1. **Query Analyst**: Interprets the user's natural language question, extracts entities and metrics of interest, and plans SQL queries
2. **Data Engineer**: Translates the query plan into actual SQL, executes database queries, and validates results
3. **Data Analyst**: Analyzes query results to identify patterns, calculate statistics, and extract insights
4. **Response Composer**: Creates a comprehensive, human-readable response with all the relevant data points
5. **FollowUp Predictor**: Generates and proactively answers likely follow-up questions

### Data Flow

```
User Query → Query Analyst → Data Engineer → Data Analyst → Response Composer → FollowUp Predictor → Final Response
```

### Data Fidelity Guardrails

The system employs specialized guardrails to ensure accurate, data-driven responses:

- **DataEngineerGuardrail**: Ensures SQL queries are safe and properly structured
- **DataAnalystGuardrail**: Validates that analytical claims match the actual data
- **ResponseComposerGuardrail**: Checks factual accuracy and consistency of the final response

These guardrails prevent "hallucinations" or fabricated data, ensuring all responses are backed by actual database values.

## Installation

### Prerequisites

- Python 3.10+
- SQLite3
- OpenAI API key

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Entropicsky/S2CombatLogAgent.git
   cd S2CombatLogAgent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```
   
   For Windows:
   ```cmd
   set OPENAI_API_KEY=your-api-key-here
   ```

## Usage

### Running the Streamlit App

1. Launch the Streamlit web interface:
   ```bash
   python run_streamlit.py
   ```

2. Open your browser and navigate to the URL displayed in the console (typically http://localhost:8506)

3. Upload a SMITE 2 combat log file using the upload button in the sidebar

4. Type your question in the input field and press Enter

5. Review the response and explore suggested follow-up questions

### Sample Questions

Here are some example questions you can ask:

- "Who dealt the most damage in the match?"
- "What was the total healing done by each player?"
- "Which player had the highest KDA ratio?"
- "What abilities did the top player use most frequently?"
- "Compare the damage output of the top 3 players"
- "How did damage distribution change throughout the match phases?"

## Technical Details

### Database Schema

The system works with SQLite databases containing SMITE 2 combat logs with these core tables:

- `matches`: Match metadata and settings
- `players`: Player information including names, gods, and teams
- `combat_events`: All combat interactions (damage, healing, kills)
- `reward_events`: Experience and gold rewards
- `item_events`: Item purchases and upgrades
- `timeline_events`: Chronological match events with timestamps

### Multi-Agent System

The agent uses OpenAI's GPT models in a specialized pipeline architecture:

- **QueryAnalystAgent**: Uses match context awareness for better query understanding
- **DataEngineerAgent**: Executes parallel SQL queries for complex data needs
- **DataAnalystAgent**: Performs statistical analysis and pattern recognition
- **ResponseComposerAgent**: Creates detailed, factually accurate responses
- **FollowUpPredictorAgent**: Generates contextually relevant follow-up questions

### Components

- `smite2_agent/`: Main application code
  - `agents/`: Agent implementations
  - `guardrails/`: Data fidelity guardrails
  - `pipeline/`: Data flow and pipeline implementation
  - `tools/`: SQL, chart, and utility tools
  - `ui/`: Streamlit interface

## Future Development

- Visualization capabilities for charts and graphs
- Support for more complex analytical questions
- Timeline analysis for match progression insights
- Team composition and strategy analysis
- Performance optimizations for larger logs

## Acknowledgments

This project uses:

- OpenAI's GPT models for natural language processing
- Streamlit for the web interface
- SQLite for database functionality

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 