# SMITE 2 Combat Log Agent - Agent Notes

## Latest Update (2025-04-03): Temperature Settings Optimization

We've optimized the temperature settings across all our agents to improve consistency and reduce variability in responses. The same query should now produce nearly identical results when run multiple times.

| Agent                 | Old Value | New Value | Rationale                                        |
|-----------------------|-----------|-----------|--------------------------------------------------|
| QueryAnalystAgent     | 0.3       | 0.2       | More consistent query interpretation             |
| DataEngineerAgent     | 0.2       | 0.2       | Already optimal for SQL generation (unchanged)   | 
| DataAnalystAgent      | 0.4       | 0.2       | More consistent statistical analysis             |
| ResponseComposerAgent | 0.7       | 0.2       | Significantly more consistent responses          |
| FollowUpPredictorAgent| 0.4       | 0.3       | Better consistency with some variety             |

For detailed analysis, see `agent_notes/notebook.md` entry from 2025-04-03.

## Latest Update (2025-04-03): Structured Response Format for Web UIs

We've implemented a comprehensive structured JSON response format that provides both user-friendly answers and detailed debugging information for web UIs. The format includes:

- User-facing content (formatted answer and follow-up questions)
- Complete SQL queries with execution time and results
- Detailed pipeline processing information and timing
- Performance metrics for the entire pipeline

**For full details**: See `agent_notes/special_notes/response_format.md` for comprehensive documentation.

To use the new format, run:
```bash
python simple_cli.py "Your question" --output debug_json
```

## Important Update (2025-04-03): Multi-Query Support for Complex Questions

We've enhanced the Agent pipeline to support multi-query processing for complex user questions:

### Multi-Query Implementation
The QueryAnalystAgent now has advanced capabilities to:

1. **Detect Complex Questions**:
   - Identify questions that require multiple SQL queries to answer completely
   - Detect comparative queries (e.g., "How does Player A compare to Player B?")
   - Identify time-based comparisons (e.g., "first 10 minutes vs. last 10 minutes")
   - Recognize multi-part questions with "and" conjunctions

2. **Generate Multiple SQL Queries**:
   - For each identified component of a complex question, generate a dedicated SQL query
   - Tag each query with its purpose and relationship to the overall question
   - Structure queries to enable comparative analysis downstream

3. **Enhance with Match Context**:
   - Pre-load match context (players, gods, stats) to improve query understanding
   - Use this context to identify entities and metrics in user questions
   - Map user references to exact database representations

### Pipeline Integration
The multi-query architecture integrates with our pipeline:

1. **DataPackage Structure**:
   - Enhanced to support multiple SQL queries under `data.query_results`
   - Each query is labeled with its purpose and relationship to the question
   - Results are stored with consistent structure for downstream processing

2. **Data Engineer Agent**:
   - Processes all SQL queries identified by the Query Analyst
   - Executes queries in parallel when possible
   - Stores all results in the DataPackage with appropriate metadata

3. **Data Analyst Agent**:
   - Processes all query results collectively
   - Performs cross-query analysis and comparisons
   - Generates insights that span multiple data sets

4. **Response Composer**:
   - Synthesizes information from all query results
   - Creates coherent responses addressing all parts of complex questions
   - Structures responses with appropriate sections for multi-part questions

### Implementation Status
- Multi-query detection is fully implemented in QueryAnalystAgent ✅
- Complex SQL generation for comparative questions is complete ✅
- DataPackage structure supports multiple query results ✅
- Tests for multi-query capabilities are passing ✅
- Next: Implement parallel query execution in Data Engineer Agent

This enhancement enables the agent to handle much more sophisticated questions such as:
- "Compare player X's performance in the first 10 minutes vs the last 10 minutes"
- "Show me which player had the highest healing and how it compares to their damage output"
- "What abilities did the top damage dealer use most effectively against the support players?"

## Important Update (2025-03-31): Enhanced Multi-Agent Architecture

### Current Status
We've implemented a basic agent pipeline with DataEngineer, DataAnalyst, and ResponseComposer agents that can answer queries about SMITE 2 combat logs. This system is functional but limited in providing rich, context-aware responses.

### New Direction
We're enhancing the architecture to a multi-agent system with:

1. **Parallel Agent Processing**:
   - Multiple specialized agents analyzing data simultaneously
   - Rich, layered responses with statistics, visualizations, patterns, etc.
   - Domain-specific context and validation

2. **New Specialized Agents**:
   - **SMITE Expert Agent**: Domain validation, context addition, "bullshit detector"
   - **Visualization Agent**: Charts, graphs, and visual representations
   - **Context Agent**: Historical and comparative context
   - **Pattern Agent**: Gameplay strategies and patterns
   - **Timeline Agent**: Chronological event mapping

3. **Enhanced Orchestration**:
   - Parallel execution of compatible agents
   - Dynamic agent selection based on query type
   - Aggregation of multi-agent outputs

### Implementation Strategy
We're taking a staged approach:
1. First implement SMITE Expert for validation
2. Add Visualization Agent for enhanced responses
3. Enhance orchestration for parallel processing
4. Add remaining specialized agents incrementally

### Documentation
- See `agent_notes/agent_techspec.md` for detailed architecture spec
- See `agent_notes/project_checklist.md` for implementation tasks
- See `agent_notes/notebook.md` for discussion notes (2025-03-31 entry)

## Project Overview
The SMITE 2 Combat Log Agent is a specialized tool designed to analyze combat log data from SMITE 2 matches. It uses a combination of database queries, natural language processing, and AI-powered analysis to answer complex questions about match data.

## Key Architecture Components

### Core Components
- **Database Module**: Provides secure, read-only access to SQLite database containing match data
- **SQL Tools**: Validates and executes SQL queries with robust security checks
- **Chart Generation**: Creates visualizations from query results
- **Agent System**: Uses OpenAI's Agents SDK (March 2025) to implement a multi-agent architecture with handoffs
- **PandasAI Integration**: Custom implementation for data analysis using pandas and OpenAI

### Agent Structure
- **Orchestrator Agent**: Main entry point that classifies queries and routes to specialists using the Agents SDK handoff mechanism
- **Specialist Agents**: Domain-specific experts for different aspects of the data
  - Combat Data Specialist: Analyzes damage, kills, and combat events
  - Timeline Specialist: Focuses on chronological events and match progression
  - Player Specialist: Analyzes player performance and statistics

## Implementation Details

### Database Security
- Read-only SQLite connection using URI mode (`file:{path}?mode=ro`)
- Additional PRAGMA settings to enforce read-only access
- Comprehensive SQL validation to prevent unsafe operations
- Regex-based pattern matching to allow only safe query types

### OpenAI Integration
- Using the OpenAI Agents SDK (March 2025) for advanced agent orchestration
- Implements proper handoff mechanisms between agents
- Better tracing and monitoring of agent activities
- Support for guardrails to validate inputs and outputs
- Configurable model settings with temperature, top_p, etc.
- Uses the `@function_tool` decorator for registered tools

### Custom PandasAI Implementation
- Built our own PandasAI-like functionality using pandas and OpenAI directly
- Handles compatibility issues with Python 3.13
- Same interface as original PandasAI but with improved error handling
- Gracefully falls back to the original PandasAI if available

### Data Visualization
- Supports multiple chart types: bar, line, pie, scatter
- Dynamic chart generation based on query results
- Support for single and multi-series data

## Developer Guide for Agents SDK

### Creating Agents
```python
from agents import Agent, ModelSettings, Runner
from agents.tools import function_tool

# Define a tool using the function_tool decorator
@function_tool
def query_database(query: str) -> str:
    """Execute a SQL query on the combat log database."""
    # Implementation...

# Create model settings
model_settings = ModelSettings(
    temperature=0.2,
    max_tokens=4096,
    top_p=0.95
)

# Create an agent
agent = Agent(
    name="CombatAgent",
    description="Analyzes combat data",
    instructions="Detailed instructions...",
    model="gpt-4o",
    model_settings=model_settings,
    tools=[query_database]
)

# Create a runner
runner = Runner()

# Run the agent
response = await runner.run_async(agent, "Which player dealt the most damage?")
```

### Implementing Handoffs
```python
# Create specialist agents
combat_agent = Agent(name="CombatAgent", ...)
timeline_agent = Agent(name="TimelineAgent", ...)

# Create orchestrator with handoff capabilities
orchestrator = Agent(
    name="OrchestratorAgent",
    instructions="You coordinate specialist agents...",
    handoff_agents=[combat_agent, timeline_agent],
    tools=[...]
)

# When run, the orchestrator can now hand off to specialists
```

### Adding Guardrails
```python
from agents import Guardrail

# Create a simple guardrail
input_validator = Guardrail(
    validate_func=lambda query: "delete" not in query.lower(),
    error_message="Cannot process queries with DELETE operations"
)

# Use guardrails when running agents
response = await runner.run_async(agent, query, guardrails=[input_validator])
```

### Dependency Requirements
- Install the Agents SDK: `pip install openai-agents agents-tracing`
- Ensure compatible OpenAI API version: `pip install openai>=1.23.0`
- See requirements-agents.txt for full dependencies

## Testing Status
All test suites are passing with our custom PandasAI implementation. We have:
- Database connection and security tests
- SQL validation and execution tests 
- Schema extraction tests
- Chart generation tests
- Agent infrastructure tests
- PandasAI integration tests

## Next Steps
1. Add integration tests with real OpenAI API
2. Implement specialist agents with domain-specific knowledge
3. Create the Streamlit UI for user interaction
4. Add performance optimizations for larger datasets
5. Implement conversation memory for follow-up questions

## Important Files
- `smite2_agent/db/connection.py`: Database connection handling
- `smite2_agent/tools/sql_tools.py`: SQL query execution and validation
- `smite2_agent/tools/chart_tools.py`: Chart generation
- `smite2_agent/tools/pandasai_tools.py`: Custom PandasAI implementation
- `smite2_agent/agents/openai_agent.py`: OpenAI agent implementation
- `smite2_agent/agents/specialist_agents.py`: Specialist agent implementations

## User Preferences
- Prefer detailed technical analysis over basic summaries
- Focus on statistical anomalies and interesting patterns
- Include visualizations when they add value
- Explain methodology in technical terms

## Project Structure
- `smite2_agent/` - Main package directory
  - `db/` - Database utilities 
  - `tools/` - Analysis tools (SQL, charts)
  - `llm/` - LLM integration
  - `cli/` - Command-line interface
  - `streamlit_app/` - Streamlit web application
  - `tests/` - Test suite

## Key Files
- `smite2_agent/db/connection.py` - Database connection manager with read-only enforcement
- `smite2_agent/db/schema.py` - Schema information extraction
- `smite2_agent/db/validators.py` - SQL query validation
- `smite2_agent/tools/sql_tools.py` - SQL query execution
- `smite2_agent/tools/chart_tools.py` - Chart generation
- `smite2_agent/llm/client.py` - OpenAI API integration
- `smite2_agent/llm/prompts.py` - Prompt templates
- `smite2_agent/cli/agent.py` - Command-line interface
- `smite2_agent/streamlit_app/app.py` - Streamlit web application

## Technical Decisions
1. **Read-only Database**: All database access is strictly read-only to prevent accidental data corruption.
2. **SQL Validation**: All user queries are validated to prevent SQL injection and unsafe operations.
3. **Chart Generation**: Various chart types are supported (bar, line, pie, scatter, etc.) for data visualization.
4. **Test Suite**: Comprehensive tests for all components to ensure reliability.

## Testing Progress (2025-03-31)
We've successfully implemented a comprehensive test suite that verifies the core functionality of the system:

1. **Database Tests**:
   - Connection management with read-only enforcement ✅
   - Query execution and error handling ✅

2. **SQL Validation Tests**:
   - Safe and unsafe query detection ✅
   - SQL injection prevention ✅
   - Edge case handling ✅

3. **Schema Tests**:
   - Table and column discovery ✅
   - Sample data retrieval ✅
   - Schema description generation ✅

4. **Chart Generation Tests**:
   - Various chart types (bar, line, pie, scatter) ✅
   - Real data handling ✅
   - Error handling ✅

5. **Test Runner**:
   - Created a script to run all tests in one command ✅

## Important Findings
1. The SQL validator has some limitations:
   - UNION queries with proper column matching are allowed (this might be acceptable)
   - The 'load_extension' function is not detected as unsafe
   - PRAGMA commands are blocked, which prevents some schema analysis functions

2. The chart generator handles various chart types well but could use better error handling.

3. Real database data is used for testing, which ensures compatibility with the actual schema.

## Next Steps
1. **Create LLM Integration Tests**:
   - Test prompt templates
   - Test response parsing
   - Test error handling

2. **Create CLI Tests**:
   - Test command parsing
   - Test interactive mode
   - Test error handling

3. **Create Streamlit App Tests**:
   - Test UI components
   - Test data flow
   - Test error handling

4. **Security Enhancements**:
   - Improve SQL validator to detect more attack vectors
   - Add rate limiting for LLM API calls

5. **Performance Optimization**:
   - Optimize chart generation for large datasets
   - Implement caching for frequent queries

## Tips for the Next Agent Session
1. Review the test suite to understand the system's capabilities and limitations.
2. Focus on implementing the remaining tests for LLM integration, CLI, and Streamlit app.
3. Address the limitations identified in the SQL validator.
4. The database schema is in CombatLogExample.db - use this for all testing.
5. See the project_checklist.md for a detailed list of tasks and progress.

## References
1. **Core Database Module**
   - Read-only SQLite connection manager for secure database access
   - SQL validation to prevent any destructive operations
   - Schema information extraction utilities for agent context

2. **Tool Implementation**
   - SQL query tool with security validation
   - Chart generation using Matplotlib
   - PandasAI integration for natural language data analysis

3. **Agent Framework**
   - Base agent class with common functionality
   - OpenAI Agent implementation with tool integration
   - Function tool decorator for easy tool definition

4. **User Interfaces**
   - Command-line interface for testing and direct use
   - Streamlit web application for interactive analysis

## Architecture
- **Orchestrator Agent**: Central coordinator that delegates to specialist agents
- **Specialist Agents**: CombatEventsAgent, TimelineAgent, PlayerStatsAgent
- **Tools**: SQL queries, PandasAI analysis, chart generation
- **Database**: SQLite with combat log data
- **UI**: Streamlit chat interface

## Implementation Strategy
1. Start with core database and tool functionality ✓
2. Implement single agent prototype before multi-agent system ✓
3. Add Streamlit UI incrementally ✓
4. Test thoroughly at each step

## Technical Challenges
- Agent handoff mechanism implementation
- PandasAI integration and error handling
- Visualizing complex data effectively
- Database security and performance

## Development Notes
- OpenAI Agents API implementation follows the function calling pattern
- PandasAI is integrated using the OpenAI API key (not a separate key)
- SQL validation is strictly enforced to prevent database modifications
- Chart generation uses Matplotlib with a non-interactive backend
- Streamlit session state manages conversation history and database connections

## Next Steps
1. Test the implementation with real SMITE 2 combat log database files
2. Implement specialist agents with domain-specific tools and prompts
3. Enhance the chart generation capabilities with more visualization types
4. Implement the agent handoff mechanism for cross-agent communication
5. Add more comprehensive error handling and recovery mechanisms

## References
- See `agent_notes/special_notes/combatlog_agent.md` for full spec
- See `agent_notes/special_notes/agentsapi.md` for Agents API information
- See `agent_notes/special_notes/pandasinfo.md` for PandasAI docs
- Project checklist in `agent_notes/project_checklist.md`

## Multi-Agent Pipeline Architecture (2025-04-01)

We've developed a sophisticated multi-agent pipeline architecture using the OpenAI Agents SDK. This architecture represents the core of the SMITE 2 Combat Log Agent and is documented extensively across several files.

### Key Documents

If restarting a session, review these files in this order:

1. **Technical Specification**: `agent_notes/agent_techspec.md`
   - Contains the comprehensive architecture design
   - Outlines all agent roles and responsibilities 
   - Details data flow and communication protocols
   - Includes implementation details and considerations

2. **Data Package Reference**: `agent_notes/special_notes/agent_data_package.md`
   - Defines the standardized JSON structure passed between agents
   - Shows example data for each pipeline stage
   - Provides usage guidelines and implementation notes

3. **Agent Templates**: `agent_notes/special_notes/agent_templates.md`
   - Contains detailed templates for implementing each specialized agent
   - Includes specific instructions to give each agent
   - Lists required tools for each agent type
   - Provides temperature settings and implementation guidance

4. **Project Checklist**: `agent_notes/project_checklist.md`
   - Shows overall project progress
   - Contains detailed tasks for implementing the multi-agent architecture
   - Tracks which components are completed vs. still pending

5. **Development Notebook**: `agent_notes/notebook.md`
   - Contains ongoing development notes and findings
   - Includes results from testing the OpenAI Agents SDK
   - Documents architecture planning decisions
   - Has detailed entry on data fidelity guardrails implementation (2025-03-30)

### Architecture Overview

Our pipeline follows this sequence:
```
User Query → [Orchestrator] → [Query Analyst] → [Data Engineer] → [Data Analyst] → 
[Visualization Specialist] → [Response Composer] → [Quality Reviewer] → Final Response
```

With domain-specific variants for:
- Combat Analysis Pipeline
- Timeline Analysis Pipeline
- Player Performance Pipeline

### Implementation Status

- Basic OpenAI Agents SDK integration is complete
- Simple example with handoffs works correctly
- Multi-agent pipeline is specified but implementation is pending
- Data fidelity guardrails proof-of-concept is implemented and tested
- Next tasks focus on implementing the base Agent class, data package utilities, and data fidelity guardrails

### Data Fidelity Guardrails

We've discovered that LLMs tend to hallucinate or fabricate data even when accessing real database information. To address this critical issue, we've implemented data fidelity guardrails that:

1. **Validate player names** - Ensure the correct players from database are mentioned
2. **Check damage values** - Verify that reported numbers match actual database values
3. **Confirm ability usage** - Ensure top abilities by damage are correctly mentioned

The guardrails detect discrepancies like:
- Made-up player names (e.g., "Zephyr" instead of "MateoUwU")
- Fabricated damage values that don't match database records
- Missing key abilities that were significant in the actual data

We've successfully tested this approach and plan to create specialized guardrails for each agent type in our pipeline.

### Getting Started

When restarting work on this project:

1. Run `examples/simple_agent_handoff.py` to verify the OpenAI Agents SDK is working
2. Run `examples/pipeline_example.py` to see the data fidelity guardrail implementation
3. Review the project checklist to determine next implementation steps
4. Start implementing the specialized agent roles following the templates
5. Use the data package format for standardizing agent communication

The most immediate tasks are:
1. Implementing the base Agent class with standardized input/output handling
2. Developing the data package serialization/deserialization utilities
3. Creating the agent pipeline workflow manager
4. Building a comprehensive data fidelity guardrail system for all agents

### OpenAI Examples for Reference

We've identified several OpenAI Agents SDK examples that align with our design:

1. **Financial Research Agent**: A 5-stage pipeline (planner → search → analysts → writer → verifier)
   - Source: [openai-agents-python/examples/financial_research_agent](https://github.com/openai/openai-agents-python/tree/main/examples/financial_research_agent)
   - Similar to our analysis pipeline with specialized agents in sequence

2. **Agent Patterns**:
   - Source: [openai-agents-python/examples/agent_patterns](https://github.com/openai/openai-agents-python/tree/main/examples/agent_patterns)
   - Showcases deterministic flows, handoffs, and using agents as tools
   - The "agents as tools" pattern could be valuable for our specialists

3. **Research Bot**:
   - Source: [openai-agents-python/examples/research_bot](https://github.com/openai/openai-agents-python/tree/main/examples/research_bot)
   - Parallel execution model that could help with our Data Engineer stage

These examples provide concrete implementation guidance for our pipeline architecture.

## Parallel Query Execution Implementation (2025-04-03)

We've successfully enhanced the DataEngineerAgent with parallel query execution capabilities. This feature is crucial for efficient processing of complex questions that require multiple SQL queries to be run.

### Implementation Overview

The implementation consists of three main components:

1. **Parallel Execution Engine**: Uses asyncio to execute multiple SQL queries concurrently
2. **Metadata Management**: Tracks the purpose and relationships between queries
3. **Error Handling**: Robust handling of partial failures in multi-query scenarios

### Code Structure

The core implementation is in `smite2_agent/agents/data_engineer.py`:

```python
# Main process_question method checks for multi-query requirements
async def process_question(self, data_package: DataPackage) -> DataPackage:
    # ... existing code ...
    
    # Check if the data package already contains SQL query suggestions
    package_data = data_package.to_dict()
    query_analysis = package_data.get("query_analysis", {})
    has_sql_suggestions = query_analysis and "sql_suggestion" in query_analysis and query_analysis["sql_suggestion"]
    needs_multiple_queries = query_analysis.get("needs_multiple_queries", False)
    
    if has_sql_suggestions and needs_multiple_queries:
        # Execute multiple queries in parallel
        return await self._execute_multiple_queries(data_package, query_analysis["sql_suggestion"])
    
    # ... rest of the method ...

# Parallel execution method
async def _execute_multiple_queries(self, data_package: DataPackage, sql_suggestions: List[Dict[str, Any]]) -> DataPackage:
    # Create tasks for parallel execution
    tasks = []
    for i, suggestion in enumerate(sql_suggestions):
        query_id = f"query{i+1}"
        sql_query = suggestion["query"]
        purpose = suggestion["purpose"]
        
        task = asyncio.create_task(self._execute_query(query_id, sql_query, purpose))
        tasks.append(task)
    
    # Execute all queries in parallel
    query_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process the results
    # ... error handling and result processing ...
    
    return data_package

# Individual query execution helper
async def _execute_query(self, query_id: str, sql_query: str, purpose: str) -> Dict[str, Any]:
    # Execute a single SQL query
    # ... query execution and error handling ...
    
    return result
```

### Using the Parallel Query Execution

To trigger parallel query execution, the QueryAnalystAgent needs to:

1. Set `needs_multiple_queries = True` in the query analysis
2. Provide an array of SQL suggestions in the format:
   ```python
   "sql_suggestion": [
       {
           "purpose": "Purpose of first query",
           "query": "SQL for first query"
       },
       {
           "purpose": "Purpose of second query",
           "query": "SQL for second query"
       }
   ]
   ```

### SQL Compatibility Considerations

When writing SQL queries for parallel execution, avoid using window functions (like MIN/MAX OVER) in WHERE clauses as they have compatibility issues with SQLite. Instead, use Common Table Expressions (CTEs) for time-based queries:

```sql
WITH TimeInfo AS (
    SELECT MIN(event_time) as min_time FROM combat_events
)
SELECT 
    c.source_entity as PlayerName,
    p.god_name as GodName,
    SUM(c.damage_amount) as TotalDamage
FROM combat_events c
JOIN players p ON c.source_entity = p.player_name
CROSS JOIN TimeInfo t
WHERE c.damage_amount > 0
AND julianday(c.event_time) BETWEEN 
    julianday(t.min_time) 
    AND julianday(t.min_time) + 600/86400.0
GROUP BY c.source_entity
ORDER BY TotalDamage DESC
```

### Error Handling

The implementation includes comprehensive error handling:

1. Each query is executed independently with its own error handling
2. Exceptions from individual queries are caught but don't halt the entire process
3. The system maintains a count of successful and failed queries
4. If all queries fail, a special "all_queries_failed" error is added to the data package

### Performance Benefits

Tests show that parallel execution provides significant performance improvements, especially when running 3+ queries that each take several seconds to execute. Our tests showed up to 3x performance improvements for complex multi-query scenarios.

### Next Steps

Future enhancements planned for the parallel query execution:

1. Implement query result caching to avoid redundant database calls
2. Add automatic SQL correction for incompatible queries
3. Implement adaptive timeouts for long-running queries
4. Add a query prioritization mechanism 