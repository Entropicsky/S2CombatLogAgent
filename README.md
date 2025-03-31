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
- **SQL Query Tool**: Write and execute custom SQL queries directly against the combat log database
- **Excel Export**: Export the entire database to Excel for further analysis in spreadsheet software
- **CSV Download**: Download SQL query results as CSV files for external processing

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
- SQLite3 (built into Python)
- OpenAI API key

### Step-by-Step Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Entropicsky/S2CombatLogAgent.git
   cd S2CombatLogAgent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. For better performance, install Watchdog:
   ```bash
   # On macOS
   xcode-select --install
   pip install watchdog
   
   # On Linux
   pip install watchdog
   
   # On Windows
   pip install watchdog
   ```

4. Set your OpenAI API key:
   ```bash
   # Linux/macOS
   export OPENAI_API_KEY="your-api-key-here"
   
   # Windows (Command Prompt)
   set OPENAI_API_KEY=your-api-key-here
   
   # Windows (PowerShell)
   $env:OPENAI_API_KEY="your-api-key-here"
   ```

   Alternatively, create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your-api-key-here
   ```

## Usage

### Launching the Streamlit App

Run the following command from the project root directory:

```bash
python run_streamlit.py
```

This will start the Streamlit web interface. You should see output similar to:

```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
Network URL: http://192.168.x.x:8501
```

Open your browser and navigate to http://localhost:8501 to access the application.

### Uploading Combat Log Files

1. Once the app is running, look for the **Upload Combat Log File** option in the sidebar
2. Click the "Browse files" button to select a SMITE 2 combat log file (`.log` or `.txt` format)
3. After selecting the file, click the "Process Log File" button
4. Wait for the processing to complete - you'll see a success message when done

### Asking Questions

1. After processing a log file, use the chat interface at the bottom of the page
2. Type your question (e.g., "Who dealt the most damage?") and press Enter
3. The system will process your question and display the answer
4. You can click on suggested follow-up questions or ask new questions

### Using the SQL Query Tool

1. After uploading and processing a combat log file, switch to the "SQL Query Tool" tab

2. Enter your SQL query in the text area
   - Reference the provided database schema and example queries
   - Write any valid SQL SELECT statement

3. Click "Execute Query" to run your query

4. View the results in the table format

5. Download the results as a CSV file using the "Download Results as CSV" button

### Exporting to Excel

1. After uploading and processing a combat log file, locate the "Export to Excel" button in the sidebar under "Database Tools"

2. Click the button to generate a comprehensive Excel file with multiple sheets:
   - Match Info: Basic match metadata
   - Players: Player information including gods and teams
   - Timeline Events: Chronological match events
   - Combat Events: Sample of combat interactions
   - Item Events: Item purchases and upgrades
   - Reward Events: Sample of experience and gold rewards
   - Player Stats: Aggregated player statistics

3. Download the Excel file using the provided download button

### Sample Questions

Here are some example questions you can ask:

- "Who dealt the most damage in the match?"
- "What was the total healing done by each player?"
- "Which player had the highest KDA ratio?"
- "What abilities did the top player use most frequently?"
- "Compare the damage output of the top 3 players"
- "How did damage distribution change throughout the match phases?"

## Deployment

The SMITE 2 Combat Log Agent can be deployed in various environments:

### Local Development

Follow the installation and usage instructions above for local development and testing.

### Server Deployment

For deploying to a server environment:

1. Clone the repository on your server
2. Install dependencies with `pip install -r requirements.txt`
3. Set up your OpenAI API key as an environment variable
4. Run the app with:
   ```bash
   python run_streamlit.py
   ```

5. For production deployments, consider running behind a reverse proxy like Nginx

### Docker Deployment

A Dockerfile is provided for containerized deployment:

```bash
# Build the Docker image
docker build -t smite2-agent .

# Run the container
docker run -p 8501:8501 -e OPENAI_API_KEY="your-api-key-here" smite2-agent
```

### Environment Variables

The following environment variables can be configured:

- `OPENAI_API_KEY`: Required for OpenAI API access
- `PORT`: Optional, to customize the port (default: 8501)
- `DEBUG`: Optional, set to "1" to enable debug mode

## Technical Details

### Database Schema

The system works with SQLite databases containing SMITE 2 combat logs with these core tables:

- `matches`: Match metadata and settings
- `players`: Player information including names, gods, and teams
- `combat_events`: All combat interactions (damage, healing, kills)
- `reward_events`: Experience and gold rewards
- `item_events`: Item purchases and upgrades
- `timeline_events`: Chronological match events with timestamps
- `player_stats`: Aggregated player statistics

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
- `scripts/`: Utility scripts
  - `export_to_excel.py`: Database export functionality
- `smite_parser/`: Combat log parsing module

## Troubleshooting

### Streamlit Version Compatibility

The application requires Streamlit version 1.27.0 or higher. If you encounter errors like:

```
AttributeError: module 'streamlit' has no attribute 'experimental_rerun'
```

Update your Streamlit installation:

```bash
pip install --upgrade streamlit
```

Note: In newer Streamlit versions, `st.experimental_rerun()` has been replaced with `st.rerun()`.

### OpenAI API Key Issues

If you see authentication errors:

1. Verify your API key is correctly set as an environment variable
2. Check that your OpenAI account has sufficient credits
3. Ensure your API key has the appropriate permissions

### Excel Export Issues

If you encounter errors when exporting to Excel:

```bash
pip install pandas openpyxl xlsxwriter
```

### Database Path Issues

If the application cannot find the database:

1. Check the console log for the actual database path
2. Verify the combat log file was processed successfully
3. Try uploading and processing the file again

### Watchdog Installation

For optimal performance, install the Watchdog module:

```bash
# On macOS
xcode-select --install
pip install watchdog

# On other platforms
pip install watchdog
```

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
- Pandas, openpyxl and xlsxwriter for data export capabilities

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 