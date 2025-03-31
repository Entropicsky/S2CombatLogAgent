# Technical Specification: SMITE 2 Combat Log Agent Implementation

## Overview
This document outlines the implementation of a multi-agent system for analyzing SMITE 2 combat log data using OpenAI's Agents API, Response API, and PandasAI within a Streamlit application.

## 1. System Architecture

### 1.1 High-Level Components
- **Streamlit Application**: Provides user interface and session management
- **Agent Framework**: Implements the multi-agent system using OpenAI Agents API
- **Tool System**: Provides functionality for agents to interact with data
- **Database Interface**: Manages access to the SQLite database
- **Visualization Engine**: Generates charts and data visualizations

### 1.2 Current Agent Implementation
- **Base Agent**: Provides common functionality for all agents
- **OpenAI Agent**: Implements the OpenAI Agents API integration
- **Specialized Agents** (planned):
  - **CombatEventsAgent**: Expert on combat interactions and damage events
  - **TimelineAgent**: Expert on match timeline and event sequences
  - **PlayerStatsAgent**: Expert on player performance metrics

### 1.3 Implemented Tools
- `run_sql_query`: Executes read-only SQL against the SQLite database
- `generate_chart`: Creates visualizations from data
- `run_pandasai_prompt`: Uses PandasAI to analyze data with natural language

## 2. Implementation Status

### 2.1 Completed: Database and Basic Tools
1. Database connection manager with read-only enforcement
   - URI-based connection with `mode=ro` flag
   - `PRAGMA query_only = ON` setting
   - Comprehensive error handling
2. SQL query validation
   - Regex-based pattern matching for unsafe operations
   - Whitelist of allowed query types (SELECT, WITH)
   - Table name validation to prevent SQL injection
3. Chart generation utilities
   - Support for line, bar, scatter, pie, and histogram charts
   - Safe file handling with unique IDs
   - Automatic parameter detection
4. PandasAI integration
   - OpenAI API integration for LLM
   - DataFrame loading from database tables
   - Error handling and retry logic
   - Result formatting based on data type

### 2.2 Completed: Agent Framework
1. Base agent implementation
   - Common functionality for all agents
   - Tool management (add, remove, list)
   - Configuration management
2. OpenAI agent implementation
   - OpenAI API integration
   - Function calling for tools
   - Conversation history management
   - Tool result processing
   - Error handling

### 2.3 Completed: User Interfaces
1. Command-line interface
   - Argument parsing with help messages
   - Interactive mode with conversation history
   - Database connection management
   - Agent instantiation with proper configuration
2. Streamlit web interface
   - File upload for database files
   - Chat interface with history display
   - Session state management
   - Asynchronous query processing
   - Tool usage transparency
   - Settings management

### 2.4 Pending: Multi-Agent System
1. Specialist agent implementation
2. Orchestrator implementation
3. Agent handoff mechanism
4. Conversation memory integration

## 3. Technical Implementation Details

### 3.1 Database Interface
The database interface is implemented with security as a top priority:

```python
# Connection with read-only enforcement
uri = f"file:{self.db_path}?mode=ro"
self._connection = sqlite3.connect(uri, uri=True)
self._connection.execute("PRAGMA query_only = ON;")
```

Query validation ensures only safe operations are permitted:

```python
# SQL validation pattern for disallowed operations
disallowed_patterns = [
    r'\bINSERT\b', r'\bUPDATE\b', r'\bDELETE\b', r'\bDROP\b',
    r'\bALTER\b', r'\bCREATE\b', r'\bATTACH\b', r'\bDETACH\b', 
    r'\bREINDEX\b', r'\bREPLACE\b', r'\bTRUNCATE\b',
    r'\bPRAGMA\b(?!.*\bquery_only\b)',
]
```

### 3.2 Tool Implementation

#### SQL Query Tool
The SQL query tool includes validation, execution, and result formatting:

```python
@function_tool
def run_sql_query(query: str, db_path: Union[str, Path], ...) -> Dict[str, Any]:
    # Validate query
    is_valid, error = validate_query(query)
    if not is_valid:
        raise SQLValidationError(f"Invalid SQL query: {error}")
    
    # Execute query and return formatted results
    with db_conn:
        rows = db_conn.execute_query(query, params)
        # Format based on preference (markdown, csv, dict)
        return {"success": True, "data": result, ...}
```

#### Chart Generation Tool
The chart generation tool supports multiple visualization types:

```python
@function_tool
def generate_chart(data: Union[List[Dict[str, Any]], pd.DataFrame], 
                  chart_type: str, x_column: str, y_columns: Union[str, List[str]], 
                  ...) -> Dict[str, Any]:
    # Convert data to DataFrame if needed
    df = pd.DataFrame(data) if isinstance(data, list) else data.copy()
    
    # Generate chart based on type
    if chart_type == 'line':
        # Line chart code
    elif chart_type == 'bar':
        # Bar chart code
    # ... other chart types
    
    # Save chart to file and return path
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    return {"success": True, "chart_path": file_path, ...}
```

#### PandasAI Integration
The PandasAI tool provides natural language data analysis:

```python
@function_tool
def run_pandasai_prompt(prompt: str, tables: List[str], db_path: Union[str, Path], 
                        ...) -> Dict[str, Any]:
    # Initialize LLM with OpenAI
    llm = OpenAI(api_token=openai_api_key)
    
    # Load DataFrames from database
    dfs = [load_dataframe_from_db(db_path, table) for table in tables]
    named_dfs = [pandasai.DataFrame(df, name=name) for name, df in zip(tables, dfs)]
    
    # Run PandasAI with retry logic
    try:
        result = pandas_ai.chat(prompt, *named_dfs)
        # Format result based on type
        return {"success": True, "result": formatted_result, ...}
    except Exception as e:
        return {"success": False, "error": str(e), ...}
```

### 3.3 Agent Implementation

The OpenAI agent implementation follows the function calling pattern:

```python
class OpenAIAgent(BaseAgent):
    # ... initialization code ...

    async def run(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Prepare messages
        messages = self._prepare_messages(user_input)
        
        # Prepare tools
        tools = self._convert_tools_to_openai_format()
        
        # Make API call
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
        )
        
        # Handle tool calls if present
        message = response.choices[0].message
        if hasattr(message, "tool_calls") and message.tool_calls:
            # Process tool calls and make a second API call with results
            # ...
        
        # Return the final response
        return {
            "content": message.content,
            "role": "assistant",
            # ... other metadata
        }
```

### 3.4 Streamlit Integration

The Streamlit app is structured to handle session management and user interaction:

```python
def main():
    # Initialize session state
    init_session_state()
    
    # File uploader and database connection
    uploaded_file = st.file_uploader("Upload SQLite database file", type=["db", "sqlite", "sqlite3"])
    if uploaded_file and st.button("Load Database"):
        # Process database file...
    
    # Chat interface
    if st.session_state.db_path is not None:
        # Display chat history
        display_messages()
        
        # Process new queries
        if prompt := st.chat_input("Ask a question about the match data"):
            # Show user message immediately
            with st.chat_message("user"):
                st.write(prompt)
            
            # Process query asynchronously
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = asyncio.run(process_query(prompt))
                # Display response...
```

## 4. Testing Strategy

To ensure the system works correctly, we will:

1. Test database connection with different files
2. Verify SQL validation with various edge cases
3. Test tool functionality with known inputs
4. Test agent responses to different queries
5. Test UI with sample interactions
6. Verify error handling works correctly

## 5. Next Steps

The next phase of implementation will focus on:

1. Testing the current system with real SMITE 2 combat log files
2. Implementing the specialist agents with domain knowledge
3. Creating the Orchestrator with handoff capabilities
4. Adding more visualization options
5. Enhancing error handling and recovery

## 6. Conclusion

The foundation of the SMITE 2 Combat Log Agent has been successfully implemented, with core database functionality, tools, and a basic agent. The next phases will build on this foundation to create a complete multi-agent system for interactive data analysis. 