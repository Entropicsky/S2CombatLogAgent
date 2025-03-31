#!/usr/bin/env python3
"""
Streamlit app for the SMITE 2 Combat Log Agent.

This script provides a web interface for interacting with the agent
and querying the combat log database.
"""

import os
import sys
import asyncio
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

import streamlit as st
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("smite2_app")

# Load environment variables from .env file
load_dotenv()

# Check if API key is set
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("OPENAI_API_KEY not found in environment. Please set it in a .env file.")
    st.error("OPENAI_API_KEY not found. Please set it in a .env file.")

# Add helper to run async functions in Streamlit
async def run_async(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await func(*args, **kwargs)

# Import the orchestrator
try:
    from smite2_agent.agents.orchestrator import Orchestrator
except ImportError:
    logger.error("Failed to import Orchestrator. Make sure the package is installed.")
    st.error("Failed to import Orchestrator. Make sure the package is installed.")

# Page configuration
st.set_page_config(
    page_title="SMITE 2 Combat Log Agent",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("SMITE 2 Combat Log Agent")
st.markdown("""
This app allows you to query the SMITE 2 combat log database using natural language.
Ask questions about players, damage, abilities, and more!
""")

# Sidebar configuration
st.sidebar.title("Settings")

# Database selection
db_options = {
    "Example DB": "data/CombatLogExample.db"
}
selected_db = st.sidebar.selectbox(
    "Database",
    options=list(db_options.keys()),
    index=0
)
db_path = db_options[selected_db]

# Model selection
model_options = ["gpt-4o", "gpt-3.5-turbo"]
selected_model = st.sidebar.selectbox(
    "Model",
    options=model_options,
    index=0
)

# Advanced options
with st.sidebar.expander("Advanced options"):
    strict_mode = st.checkbox("Strict mode", value=False)
    show_debug = st.checkbox("Show debug info", value=False)

# Example queries
st.sidebar.markdown("## Example queries")
example_queries = [
    "Who dealt the most damage in the match?",
    "What abilities did MateoUwU use?",
    "Show me the top 5 players by healing done.",
    "Which ability caused the most damage?",
    "How many deaths were recorded in the match?"
]

for query in example_queries:
    if st.sidebar.button(query):
        st.session_state.query = query

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "orchestrator" not in st.session_state:
    try:
        # Display loading message
        with st.spinner("Initializing orchestrator..."):
            # Run in a separate thread to avoid blocking Streamlit
            @st.cache_resource
            def get_orchestrator(db_path, model, strict_mode):
                return Orchestrator(
                    db_path=Path(db_path),
                    model=model,
                    strict_mode=strict_mode
                )
            
            st.session_state.orchestrator = get_orchestrator(
                db_path=db_path,
                model=selected_model,
                strict_mode=strict_mode
            )
    except Exception as e:
        logger.error(f"Error initializing orchestrator: {str(e)}")
        st.error(f"Error initializing orchestrator: {str(e)}")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Query input
query = st.chat_input("Ask a question about the combat log data...")

# Set query from example if clicked
if "query" in st.session_state:
    query = st.session_state.query
    del st.session_state.query

# Process the query
if query:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    
    # Process the query with the agent
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Process the query
                result = asyncio.run(
                    st.session_state.orchestrator.process_query(query)
                )
                
                # Display the result
                if result["success"]:
                    st.markdown(result["response"])
                    # Add to chat history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": result["response"]
                    })
                else:
                    st.error(result["response"])
                    # Add to chat history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": "❌ " + result["response"]
                    })
                
                # Show debug info if requested
                if show_debug and "data_package" in result:
                    with st.expander("Debug information"):
                        st.json(result["data_package"])
                
            except Exception as e:
                logger.error(f"Error processing query: {str(e)}")
                st.error(f"Error: {str(e)}")
                # Add to chat history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"❌ Error: {str(e)}"
                })

# Footer
st.markdown("---")
st.markdown("SMITE 2 Combat Log Agent | Powered by OpenAI Agents SDK") 