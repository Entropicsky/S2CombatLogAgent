#!/usr/bin/env python3
"""
SMITE 2 Combat Log Analyzer
Streamlit web application for analyzing SMITE 2 combat logs.
"""

import os
import sys
import logging
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

import streamlit as st

# Add parent directory to path when run directly
if __name__ == "__main__":
    # Add the parent directory to sys.path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
try:
    from openai import OpenAI
except ImportError:
    st.error("OpenAI package is not installed. Run: pip install openai>=1.0.0")
    raise

try:
    from smite2_agent.config.settings import get_settings
    from smite2_agent.config.prompts import get_prompt_for_agent
    from smite2_agent.db.connection import get_connection
    from smite2_agent.db.schema import get_schema_info
    from smite2_agent.agents.openai_agent import OpenAIAgent
    from smite2_agent.tools.sql_tools import run_sql_query
    from smite2_agent.utils.tools import function_tool
except ImportError:
    # Try relative imports if direct module imports fail
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from smite2_agent.config.settings import get_settings
    from smite2_agent.config.prompts import get_prompt_for_agent
    from smite2_agent.db.connection import get_connection
    from smite2_agent.db.schema import get_schema_info
    from smite2_agent.agents.openai_agent import OpenAIAgent
    from smite2_agent.tools.sql_tools import run_sql_query
    from smite2_agent.utils.tools import function_tool

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("smite2_agent")


# Initialize session state
def init_session_state():
    """Initialize Streamlit session state."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "db_path" not in st.session_state:
        st.session_state.db_path = None
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "schema_info" not in st.session_state:
        st.session_state.schema_info = None


@function_tool
def query_database(query: str) -> Dict[str, Any]:
    """
    Execute a SQL query on the SMITE 2 combat log database.
    
    Args:
        query: SQL SELECT query to run
        
    Returns:
        Dictionary with query results
    """
    return run_sql_query(query, st.session_state.db_path, format_as="markdown")


def create_agent(agent_type="orchestrator"):
    """Create an agent instance."""
    settings = get_settings()
    
    # Get schema description
    schema_description = st.session_state.schema_info.get_schema_description()
    
    # Get agent instructions
    agent_instructions = get_prompt_for_agent(agent_type)
    
    # Add schema info to agent instructions
    agent_instructions = agent_instructions.replace("{{SCHEMA_INFO}}", schema_description)
    
    # Create the agent
    agent = OpenAIAgent(
        name=agent_type,
        description=f"SMITE 2 Combat Log {agent_type.capitalize()} Agent",
        instructions=agent_instructions,
        tools=[query_database],
        model_name=settings.model_name
    )
    
    return agent


async def process_query(query: str):
    """Process a user query with the agent."""
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": query})
    
    try:
        # Get agent response
        response = await st.session_state.agent.run(query)
        
        # Add assistant message to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response.get("content", "No response"),
            "tools_used": response.get("tools_used", [])
        })
        
        return response
    except Exception as e:
        logger.exception(f"Error: {str(e)}")
        
        # Add error message to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Error: {str(e)}",
            "error": True
        })
        
        return {"content": f"Error: {str(e)}", "error": True}


def process_db_file(uploaded_file):
    """Process an uploaded database file."""
    try:
        # Create a temporary file to save the uploaded database
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
            temp_file.write(uploaded_file.getvalue())
            db_path = temp_file.name
        
        # Set the database path in session state
        st.session_state.db_path = db_path
        
        # Connect to the database
        db_conn = get_connection(db_path)
        
        # Get schema info
        schema_info = get_schema_info(db_path)
        st.session_state.schema_info = schema_info
        
        # Create the agent
        st.session_state.agent = create_agent()
        
        # Clear messages
        st.session_state.messages = []
        
        # Add system message
        tables = schema_info.get_all_tables()
        system_msg = f"Connected to database with {len(tables)} tables. You can now ask questions about the SMITE 2 match."
        st.session_state.messages.append({"role": "system", "content": system_msg})
        
        return True
    except Exception as e:
        logger.exception(f"Error processing database file: {str(e)}")
        st.error(f"Error processing database file: {str(e)}")
        return False


def display_messages():
    """Display chat messages."""
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        if role == "system":
            # Display system messages as info
            st.info(content)
        elif role == "user":
            # Display user messages
            with st.chat_message("user"):
                st.write(content)
        elif role == "assistant":
            # Display assistant messages
            with st.chat_message("assistant"):
                if message.get("error", False):
                    st.error(content)
                else:
                    st.write(content)
                    
                    # Show tools used
                    tools_used = message.get("tools_used", [])
                    if tools_used:
                        with st.expander("Tools used"):
                            for tool in tools_used:
                                st.write(f"- {tool}")


def main():
    """Main Streamlit app."""
    # Set page config
    st.set_page_config(
        page_title="SMITE 2 Combat Log Analyzer",
        page_icon="📊",
        layout="wide"
    )
    
    # Initialize session state
    init_session_state()
    
    # Page title
    st.title("SMITE 2 Combat Log Analyzer")
    
    # Sidebar for file upload and settings
    with st.sidebar:
        st.subheader("Database")
        
        # File uploader for database file
        uploaded_file = st.file_uploader("Upload SQLite database file", type=["db", "sqlite", "sqlite3"])
        
        if uploaded_file is not None:
            # Process the uploaded file
            if st.button("Load Database"):
                with st.spinner("Processing database..."):
                    success = process_db_file(uploaded_file)
                if success:
                    st.success("Database loaded successfully!")
        
        # Settings
        st.subheader("Settings")
        
        # Agent selection
        agent_type = st.selectbox(
            "Agent Type",
            ["orchestrator", "combat_events", "timeline", "player_stats"],
            index=0,
            disabled=st.session_state.db_path is None
        )
        
        # Change agent button
        if st.session_state.db_path and st.button("Change Agent"):
            st.session_state.agent = create_agent(agent_type)
            st.success(f"Agent changed to {agent_type}")
        
        # OpenAI API key input
        api_key = st.text_input("OpenAI API Key", type="password", value=os.environ.get("OPENAI_API_KEY", ""))
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        # Model selection
        model = st.selectbox(
            "Model",
            ["gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-3.5-turbo"],
            index=0
        )
        settings = get_settings()
        settings.model_name = model
    
    # Main area for chat
    if st.session_state.db_path is None:
        # Show instructions when no database is loaded
        st.info("Please upload a SMITE 2 combat log database file to begin.")
        st.markdown("""
        ## How to use
        1. Upload a SMITE 2 combat log database file (.db) using the sidebar
        2. Click "Load Database" to process the file
        3. Ask questions about the match data in natural language
        
        ## Example questions
        - "Which player dealt the most damage?"
        - "Show me the timeline of important events"
        - "What was the kill count for each team?"
        - "Analyze the performance of the support players"
        """)
    else:
        # Display chat messages
        display_messages()
        
        # Chat input
        if prompt := st.chat_input("Ask a question about the match data"):
            # Show user message immediately
            with st.chat_message("user"):
                st.write(prompt)
            
            # Process with agent and show response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    # Process query asynchronously
                    response = asyncio.run(process_query(prompt))
                
                # Display response
                if response.get("error", False):
                    st.error(response.get("content", "An error occurred"))
                else:
                    st.write(response.get("content", "No response"))
                    
                    # Show tools used
                    tools_used = response.get("tools_used", [])
                    if tools_used:
                        with st.expander("Tools used"):
                            for tool in tools_used:
                                st.write(f"- {tool}")


if __name__ == "__main__":
    main() 