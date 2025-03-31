#!/usr/bin/env python3
"""
SMITE 2 Combat Log Agent - Streamlit Interface

A web interface that allows users to:
1. Upload SMITE 2 Combat Log files
2. Process them into a SQLite database
3. Query the agent about the data
4. View the agent's responses and debug information
"""

import os
import sys
import json
import tempfile
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

import streamlit as st
from dotenv import load_dotenv

# Ensure parent directory is in the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the parser
from smite_parser.config.config import ParserConfig
from smite_parser.parser import CombatLogParser

# Import agent components
from smite2_agent.pipeline.base.data_package import DataPackage
from smite2_agent.agents.query_analyst import QueryAnalystAgent
from smite2_agent.agents.data_engineer import DataEngineerAgent
from smite2_agent.agents.data_analyst import DataAnalystAgent
from smite2_agent.agents.response_composer import ResponseComposerAgent
from smite2_agent.agents.followup_predictor import FollowUpPredictorAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("smite2_agent_streamlit")

# Load environment variables
load_dotenv()

# Constants
TEMP_DIR = Path(tempfile.gettempdir()) / "smite2_agent"
TEMP_DIR.mkdir(exist_ok=True)

# Make sure OpenAI API key is set
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    # We'll check this later in the UI and show a warning

    # For development, uncomment this to use a default key from .env
    # pass
    logger.warning("OPENAI_API_KEY environment variable not set")


def extract_match_id_from_file(file_path):
    """Extract match ID from the log file if present, otherwise use filename."""
    match_id = None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Try to parse as JSON
                try:
                    event = json.loads(line)
                    # Look for match ID in events
                    if event.get("eventType") == "start" and "matchID" in event:
                        match_id = event.get("matchID")
                        break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.warning(f"Could not extract match ID from file: {e}")
    
    # Use filename as fallback
    if not match_id:
        base_name = os.path.basename(file_path)
        match_id = f"match-{os.path.splitext(base_name)[0]}"
    
    return match_id


def process_log_file(file_path: Union[str, Path], progress_callback=None) -> Optional[Path]:
    """
    Process a combat log file and create a SQLite database.
    
    Args:
        file_path: Path to the combat log file
        progress_callback: Optional callback for reporting progress
        
    Returns:
        Path to the created database file or None if processing failed
    """
    try:
        # Convert to Path object if it's a string
        log_path = Path(file_path)
        
        # Generate output path in the temp directory
        db_path = TEMP_DIR / f"{log_path.stem}.db"
        
        logger.info(f"Processing log file: {log_path}")
        logger.info(f"Output database: {db_path}")
        
        # If database exists, delete it completely instead of trying to clear match data
        # This is more reliable since these databases are disposable for the session
        if db_path.exists():
            logger.info(f"Existing database found. Deleting {db_path}...")
            db_path.unlink()  # Delete the file
        
        # Configure parser
        config = ParserConfig(
            db_path=str(db_path),
            batch_size=1000,
            show_progress=True,
            skip_malformed=True,
        )
        
        # Create parser
        parser = CombatLogParser(config)
        
        # Parse the file
        # TODO: Implement progress reporting via callback
        success = parser.parse_file(str(log_path))
        
        if success:
            logger.info(f"Successfully processed log file: {log_path}")
            return db_path
        else:
            logger.error(f"Failed to process log file: {log_path}")
            return None
    except Exception as e:
        logger.exception(f"Error processing log file: {e}")
        return None


async def process_query(db_path: Path, query: str, model: str = "gpt-4o", include_followups: bool = True) -> DataPackage:
    """
    Process a query using the full agent pipeline.
    
    Args:
        db_path: Path to the database
        query: Query to process
        model: Model to use
        include_followups: Whether to include follow-up predictions
        
    Returns:
        Complete DataPackage with results
    """
    logger.info(f"Processing query: {query}")
    
    # Create the agents
    query_analyst = QueryAnalystAgent(
        db_path=str(db_path),
        model=model,
        temperature=0.2
    )
    
    data_engineer = DataEngineerAgent(
        db_path=db_path,
        model=model,
        temperature=0.2
    )
    
    data_analyst = DataAnalystAgent(
        model=model,
        temperature=0.2
    )
    
    response_composer = ResponseComposerAgent(
        model=model,
        temperature=0.2
    )
    
    followup_predictor = None
    if include_followups:
        followup_predictor = FollowUpPredictorAgent(
            model=model,
            temperature=0.3,
            db_path=db_path
        )
    
    # Create a new data package
    data_package = DataPackage(query=query)
    if db_path:
        data_package.set_db_path(str(db_path))
    
    # Process query analysis
    logger.info("Query Analysis...")
    data_package = await query_analyst._process(data_package)
    
    # Process data engineering
    logger.info("Data Engineering...")
    data_package = await data_engineer.process_question(data_package)
    
    # Process data analysis
    logger.info("Data Analysis...")
    data_package = await data_analyst.process_data(data_package)
    
    # Process response composition
    logger.info("Response Composition...")
    data_package = await response_composer.generate_response(data_package)
    
    # Process follow-up prediction if enabled
    if include_followups and followup_predictor:
        logger.info("Follow-up Prediction...")
        data_package = await followup_predictor._process(data_package)
    
    return data_package


def format_output(data_package: DataPackage, output_format: str = "text") -> str:
    """
    Format the data package output according to the specified format.
    
    Args:
        data_package: The data package to format
        output_format: Output format ('text', 'json', or 'debug_json')
        
    Returns:
        Formatted output string
    """
    # Extract the response
    response = data_package.get_response()
    if not response:
        response = "I was unable to process your query. Please try again."
    
    # Return formatted output based on format
    if output_format == "text":
        return response
    
    elif output_format == "json":
        # Simple JSON with just the answer and followups
        package_dict = data_package.to_dict()
        simple_json = {
            "answer": response,
            "suggested_followups": package_dict.get("enhancement", {}).get("suggested_questions", [])
        }
        return json.dumps(simple_json, indent=2)
    
    elif output_format == "debug_json":
        # Detailed JSON with query debug information
        return data_package.to_debug_json()
    
    else:
        # Default to text if invalid format
        return response


def parse_debug_json(debug_json_str: str) -> Dict[str, Any]:
    """
    Parse the debug JSON string into a structured dictionary.
    
    Args:
        debug_json_str: The debug JSON string from data_package.to_debug_json()
        
    Returns:
        Parsed dictionary with user_response, pipeline_details, etc.
    """
    try:
        return json.loads(debug_json_str)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing debug JSON: {e}")
        return {"error": f"Error parsing debug JSON: {e}"}


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "uploaded_file" not in st.session_state:
        st.session_state.uploaded_file = None
    
    if "processing_status" not in st.session_state:
        st.session_state.processing_status = None
    
    if "db_path" not in st.session_state:
        st.session_state.db_path = None
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "debug_info" not in st.session_state:
        st.session_state.debug_info = {}
    
    if "query_history" not in st.session_state:
        st.session_state.query_history = []
    
    if "pending_question" not in st.session_state:
        st.session_state.pending_question = None
        
    if "active_page" not in st.session_state:
        st.session_state.active_page = "Chat"


def upload_and_process_file():
    """Upload and process a log file."""
    st.title("SMITE 2 Combat Log Agent")
    
    # File upload section
    st.header("Upload Combat Log File")
    
    uploaded_file = st.file_uploader("Choose a SMITE 2 combat log file", type=["log"])
    
    if uploaded_file is not None and uploaded_file != st.session_state.uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        st.session_state.processing_status = "pending"
    
    if st.session_state.processing_status == "pending":
        # Show a button to start processing
        if st.button("Process Combat Log File"):
            # Save uploaded file to a temporary location
            temp_file_path = TEMP_DIR / uploaded_file.name
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # Create a placeholder for status updates
            status_placeholder = st.empty()
            status_placeholder.info("Saving file and preparing to process...")
            
            # Create a progress bar
            progress_bar = st.progress(0)
            
            try:
                # Update status
                status_placeholder.info("Processing combat log file... (this may take a minute)")
                progress_bar.progress(25)
                
                # Process the file
                db_path = process_log_file(temp_file_path)
                progress_bar.progress(75)
                
                if db_path and db_path.exists():
                    # Update status
                    status_placeholder.success("Combat log processed successfully!")
                    progress_bar.progress(100)
                    
                    # Set session state
                    st.session_state.db_path = db_path
                    st.session_state.processing_status = "completed"
                    st.session_state.messages = []  # Reset messages for new file
                    
                    # Success message
                    st.success(f"Database created at {db_path}. Ready to query this data!")
                    
                    # Force Streamlit to rerun the app to show the chat interface
                    st.rerun()
                else:
                    progress_bar.empty()
                    status_placeholder.error("Failed to process combat log file.")
                    st.session_state.processing_status = "failed"
                    st.error("Check logs for details or try uploading again.")
            except Exception as e:
                progress_bar.empty()
                status_placeholder.error(f"Error: {str(e)}")
                st.session_state.processing_status = "failed"
                st.error("An unexpected error occurred. Check logs for details.")
                logger.exception("Error processing file")
    
    return st.session_state.processing_status == "completed"


def chat_interface():
    """Display the chat interface for querying the agent."""
    st.header("Ask Questions About The Combat Log")
    
    # Add a clearer explanation
    if not st.session_state.messages:
        st.info("Enter your question in the text box below to analyze the combat log data. You can ask about players, damage, healing, and more.")
    
    # Display messages
    for i, message in enumerate(st.session_state.messages):
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        elif role == "assistant":
            with st.chat_message("assistant"):
                st.markdown(content)
                
                # Show suggested follow-up questions if available
                if "suggested_questions" in message:
                    suggested_questions = message["suggested_questions"]
                    if suggested_questions:
                        st.write("Suggested questions:")
                        cols = st.columns(min(3, len(suggested_questions)))
                        for i, question in enumerate(suggested_questions):
                            if cols[i % len(cols)].button(question, key=f"suggest_{i}_{hash(question)}"):
                                # Instead of directly handling input, set pending_question and rerun
                                st.session_state.pending_question = question
                                st.rerun()
        elif role == "error":
            with st.chat_message("assistant"):
                st.error(content)
    
    # Add a visual separator
    st.divider()
    
    # Create a container with a border for the question input
    with st.container(border=True):
        st.write("**Enter your question:**")
        # Query input with a better placeholder
        st.text_input(
            "Your question:",
            key="user_query",
            on_change=handle_user_input,
            placeholder="Examples: Who dealt the most damage? Which player had the highest kill count?"
        )
        
        # Add some example questions as buttons for first-time users
        if not st.session_state.messages:
            st.write("Or try one of these questions:")
            example_cols = st.columns(3)
            example_questions = [
                "Who dealt the most damage?",
                "Which player had the highest healing?",
                "What were the top 3 abilities by damage?"
            ]
            for i, question in enumerate(example_questions):
                if example_cols[i].button(question, key=f"example_{i}"):
                    handle_user_input(question)


def handle_user_input(suggested_question=None):
    """Handle user input from the chat interface."""
    # Get the query from either the suggested question or the input field
    query = suggested_question if suggested_question else st.session_state.user_query
    
    if not query:
        return
    
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": query})
    
    # Clear the input field if not using a suggested question
    if not suggested_question:
        st.session_state.user_query = ""
    
    # Process the query using our detailed status function
    process_question_with_status(query)


def debug_panel():
    """Display the debug panel with detailed information about queries."""
    st.divider()
    st.subheader("Debug Information")
    st.markdown("Explore details about how the agent analyzed your query, including SQL queries, analysis, and performance metrics.")
    
    if not st.session_state.debug_info:
        st.info("No debug information available yet. Ask a question above to see detailed debug information here.")
        return
    
    # Display a selector for queries
    if st.session_state.query_history:
        selected_query = st.selectbox(
            "Select a query to debug",
            options=[q["query"] for q in st.session_state.query_history],
            index=len(st.session_state.query_history) - 1
        )
        
        # Get debug data for the selected query
        debug_data = st.session_state.debug_info.get(selected_query, {})
        
        if not debug_data:
            st.warning(f"No debug data found for query: {selected_query}")
            return
        
        # Display debug information in tabs
        tab1, tab2, tab3, tab4 = st.tabs(["SQL Queries", "Analysis", "Performance", "Raw Data"])
        
        with tab1:
            # SQL Queries
            st.subheader("SQL Queries")
            st.markdown("These are the SQL queries generated and executed by the agent to retrieve data from the database.")
            queries = debug_data.get("pipeline_details", {}).get("queries", [])
            if queries:
                for i, query in enumerate(queries):
                    with st.expander(f"Query {i+1}: {query.get('purpose', 'Unknown purpose')}"):
                        st.code(query.get("sql", ""), language="sql")
                        st.text(f"Execution time: {query.get('execution_time_ms', 0)} ms")
                        st.text(f"Rows returned: {query.get('row_count', 0)}")
                        
                        # Display results in a table
                        results = query.get("results", [])
                        if results:
                            st.subheader("Query Results")
                            st.dataframe(results)
                        else:
                            st.info("No results returned.")
            else:
                st.info("No SQL queries were executed for this question.")
        
        with tab2:
            # Analysis
            st.subheader("Analysis")
            st.markdown("This shows how the agent analyzed the data and what insights it found.")
            analysis = debug_data.get("pipeline_details", {}).get("analysis", {})
            
            # Key findings
            key_findings = analysis.get("key_findings", [])
            if key_findings:
                st.write("### Key Findings")
                for finding in key_findings:
                    st.write(f"- **{finding.get('description', '')}** _{finding.get('significance', '')}_ ")
            
            # Patterns
            patterns = analysis.get("patterns", [])
            if patterns:
                st.write("### Patterns")
                for pattern in patterns:
                    st.write(f"- **{pattern.get('description', '')}** _{pattern.get('significance', '')}_ ")
            
            # Raw results
            raw_results = analysis.get("raw_results", {})
            if raw_results:
                with st.expander("Raw Analysis Results"):
                    st.json(raw_results)
        
        with tab3:
            # Performance
            st.subheader("Performance Metrics")
            st.markdown("This shows how long each part of the query processing took.")
            metrics = debug_data.get("performance_metrics", {})
            
            # Total time
            total_time = metrics.get("total_processing_time_ms", 0)
            st.write(f"Total processing time: {total_time} ms")
            
            # Stage breakdown
            stages = metrics.get("stage_breakdown", [])
            if stages:
                st.write("### Stage Breakdown")
                
                # Create data for bar chart
                stage_names = [s.get("stage", "unknown") for s in stages]
                stage_times = [s.get("time_ms", 0) for s in stages]
                stage_percentages = [s.get("percentage", 0) for s in stages]
                
                # Display as a table
                stage_data = {
                    "Stage": stage_names,
                    "Time (ms)": stage_times,
                    "Percentage": [f"{p}%" for p in stage_percentages]
                }
                st.dataframe(stage_data)
            
            # Slowest stage
            slowest = metrics.get("slowest_stage", {})
            if slowest:
                st.write(f"Slowest stage: **{slowest.get('stage', '')}** ({slowest.get('time_ms', 0)} ms)")
            
            # Query execution time
            query_time = metrics.get("query_execution_time_ms", 0)
            st.write(f"SQL Query execution time: {query_time} ms")
        
        with tab4:
            # Raw Data
            st.subheader("Raw Debug Data")
            st.markdown("This is the complete debug information in JSON format.")
            with st.expander("View Complete Debug JSON"):
                st.json(debug_data)
    else:
        st.info("No queries have been processed yet.")


def settings_sidebar():
    """Create the settings sidebar."""
    with st.sidebar:
        st.title("SMITE 2 Combat Log Agent")
        
        # Check for API key
        if not os.environ.get("OPENAI_API_KEY"):
            st.warning("⚠️ OpenAI API key not set. Please enter your API key below.")
            api_key = st.text_input("OpenAI API Key", type="password")
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
                st.success("✅ API key set successfully!")
        
        # File upload
        st.header("Combat Log File")
        uploaded_file = st.file_uploader(
            "Upload a SMITE 2 Combat Log file",
            type=["log", "txt"],
            help="Upload a .log or .txt file containing SMITE 2 combat log data",
            key="file_uploader"
        )
        
        if uploaded_file:
            if st.session_state.uploaded_file != uploaded_file.name:
                st.session_state.uploaded_file = uploaded_file.name
                st.session_state.processing_status = "ready"
                st.session_state.db_path = None
                st.session_state.messages = []
            
            if st.session_state.processing_status == "ready":
                if st.button("Process Log File"):
                    st.session_state.processing_status = "processing"
                    st.rerun()
        
        # If database is loaded, show export options
        if st.session_state.db_path:
            st.header("Database Tools")
            
            # Add Excel export option
            if st.button("Export to Excel"):
                try:
                    # Import the export_to_excel function
                    from scripts.export_to_excel import export_to_excel
                    
                    with st.spinner("Exporting to Excel..."):
                        # Generate export file
                        excel_path = export_to_excel(str(st.session_state.db_path))
                        
                        # Read the generated file
                        with open(excel_path, "rb") as f:
                            excel_data = f.read()
                        
                        # Offer download link
                        st.download_button(
                            label="Download Excel File",
                            data=excel_data,
                            file_name=os.path.basename(excel_path),
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        st.success(f"✅ Export successful!")
                except Exception as e:
                    st.error(f"❌ Error exporting to Excel: {str(e)}")
                    st.info("Make sure pandas and openpyxl are installed: pip install pandas openpyxl xlsxwriter")
            
            # Add database path display
            if st.session_state.db_path:
                st.info(f"Database: {os.path.basename(st.session_state.db_path)}")
            
        # Model selection
        st.header("Settings")
        model = st.selectbox(
            "Model",
            ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
            index=0,
        )
        
        # Follow-up questions toggle
        include_followups = st.checkbox(
            "Include follow-up questions",
            value=True,
        )
        
        # Debug mode
        show_debug = st.checkbox(
            "Show debug panel",
            value=False,
            key="show_debug"
        )
        
        # Store settings in session state
        st.session_state.model = model
        st.session_state.include_followups = include_followups


def process_question_with_status(query: str):
    """Process a query with status updates."""
    try:
        # Create a status placeholder for real-time updates
        status_placeholder = st.empty()
        status_placeholder.info("Initializing agents...")
        
        # Create a progress bar
        progress_bar = st.progress(0)
        
        # Create a container for detailed status updates
        details_container = st.container()
        
        # Define a callback to update processing status
        def update_status(stage, progress_percent, details=None):
            status_placeholder.info(f"Processing: {stage}")
            progress_bar.progress(progress_percent)
            if details:
                with details_container:
                    st.text(details)
        
        # Show initial status
        update_status("Starting pipeline", 5, "Initializing agent pipeline...")
        
        # Process each agent with status updates
        
        # Run the query asynchronously with status updates
        async def run_query_with_status():
            # Create all agents
            update_status("Preparing agents", 10, "Setting up specialized agents...")
            
            # Query Analysis stage (20%)
            update_status("Query Analysis", 15, "Analyzing your question...")
            data_package = DataPackage(query=query)
            data_package.set_db_path(str(st.session_state.db_path))
            
            query_analyst = QueryAnalystAgent(
                db_path=str(st.session_state.db_path),
                model=st.session_state.model,
                temperature=0.2
            )
            data_package = await query_analyst._process(data_package)
            update_status("Query Analysis", 20, "Question analyzed and categorized.")
            
            # Data Engineering stage (40%)
            update_status("Data Engineering", 25, "Generating SQL queries...")
            data_engineer = DataEngineerAgent(
                db_path=st.session_state.db_path,
                model=st.session_state.model,
                temperature=0.2
            )
            data_package = await data_engineer.process_question(data_package)
            
            # Get a sample of SQL executed for display
            package_dict = data_package.to_dict()
            query_results = package_dict.get("data", {}).get("query_results", {})
            if query_results:
                first_query = next(iter(query_results.values()))
                sql_sample = first_query.get("sql", "")
                rows_count = first_query.get("result_summary", {}).get("row_count", 0)
                update_status("Data Engineering", 40, f"Database queried, retrieved {rows_count} rows.")
                
                # Display SQL in a collapsible section for users who want to see it
                with details_container:
                    with st.expander("SQL query executed", expanded=False):
                        st.code(sql_sample, language="sql")
                        
                        # If there are more than one query, show a message
                        if len(query_results) > 1:
                            st.text(f"+ {len(query_results) - 1} additional queries executed")
            else:
                update_status("Data Engineering", 40, "Database queried.")
            
            # Data Analysis stage (60%)
            update_status("Data Analysis", 45, "Analyzing database results...")
            data_analyst = DataAnalystAgent(
                model=st.session_state.model,
                temperature=0.2
            )
            data_package = await data_analyst.process_data(data_package)
            
            # Show some insight details
            analysis_results = data_package.get_analysis_results()
            if analysis_results:
                with details_container:
                    with st.expander("Analysis in progress", expanded=False):
                        if "player_metrics" in analysis_results:
                            st.write("✓ Player metrics analyzed")
                        if "damage_distribution" in analysis_results:
                            st.write("✓ Damage distribution identified")
                        if "timeline_analysis" in analysis_results:
                            st.write("✓ Timeline patterns detected")
                        if "item_analysis" in analysis_results:
                            st.write("✓ Item build effectiveness evaluated")
            
            update_status("Data Analysis", 60, "Analysis complete, identifying insights...")
            
            # Response Composition stage (80%)
            update_status("Response Composition", 65, "Composing answer...")
            response_composer = ResponseComposerAgent(
                model=st.session_state.model,
                temperature=0.2
            )
            data_package = await response_composer.generate_response(data_package)
            update_status("Response Composition", 80, "Answer composed.")
            
            # Follow-up Prediction stage (100%)
            if st.session_state.include_followups:
                update_status("Generating follow-ups", 85, "Predicting potential follow-up questions...")
                followup_predictor = FollowUpPredictorAgent(
                    model=st.session_state.model,
                    temperature=0.3,
                    db_path=st.session_state.db_path
                )
                data_package = await followup_predictor._process(data_package)
                update_status("Complete", 100, "Response ready!")
            else:
                # Skip follow-up generation if disabled
                update_status("Complete", 100, "Response ready!")
            
            return data_package
        
        # Run the query with status updates
        data_package = asyncio.run(run_query_with_status())
        
        # Clear status elements when done
        progress_bar.empty()
        status_placeholder.empty()
        details_container.empty()
        
        # Format as debug JSON
        try:
            debug_json = data_package.to_debug_json()
            debug_data = parse_debug_json(debug_json)
            
            # Store debug info in session state
            st.session_state.debug_info[query] = debug_data
            
            # Get the formatted answer
            formatted_answer = debug_data.get("user_response", {}).get("formatted_answer", "")
            
            # Get suggested follow-up questions
            suggested_questions = debug_data.get("user_response", {}).get("suggested_followups", [])
            
            # Add assistant message to chat
            st.session_state.messages.append({
                "role": "assistant",
                "content": formatted_answer,
                "suggested_questions": suggested_questions,
                "debug_data": debug_data
            })
            
            # Add to query history
            st.session_state.query_history.append({
                "query": query,
                "timestamp": debug_data.get("metadata", {}).get("timestamp", ""),
                "query_id": debug_data.get("metadata", {}).get("query_id", "")
            })
        except Exception as e:
            logger.exception(f"Error processing debug JSON: {str(e)}")
            # Add error message to chat
            error_message = f"Error processing query results: {str(e)}"
            st.session_state.messages.append({
                "role": "error",
                "content": error_message
            })
        
        # Force a rerun to display the new messages
        st.rerun()
        
    except Exception as e:
        # Handle errors
        error_message = f"Error processing query: {str(e)}"
        logger.exception(error_message)
        
        # Add error message to chat
        st.session_state.messages.append({
            "role": "error",
            "content": error_message
        })
        
        # Force a rerun to display the error
        st.rerun()


def sql_query_page():
    """SQL Query page that allows users to write and execute SQL directly."""
    st.title("SQL Query Tool")
    
    if not st.session_state.db_path:
        st.warning("Please upload a combat log file first to use the SQL Query Tool.")
        return
    
    st.write("Execute SQL queries directly against the combat log database.")
    
    # SQL Query input
    query = st.text_area(
        "Enter your SQL query:", 
        height=150,
        placeholder="SELECT * FROM players LIMIT 10"
    )
    
    # Database schema helper
    with st.expander("Database Schema Reference"):
        st.markdown("""
        ### Main Tables
        - **matches**: Match metadata and settings
        - **players**: Player information including names, gods, and teams
        - **combat_events**: All combat interactions (damage, healing, kills)
        - **reward_events**: Experience and gold rewards
        - **item_events**: Item purchases and upgrades
        - **timeline_events**: Chronological match events with timestamps
        - **player_stats**: Aggregated player statistics
        
        ### Example Queries
        ```sql
        -- Get all players
        SELECT * FROM players
        
        -- Get top damage dealers
        SELECT 
            source_entity as Player, 
            SUM(damage_amount) as TotalDamage 
        FROM combat_events 
        WHERE damage_amount > 0 
        GROUP BY source_entity 
        ORDER BY TotalDamage DESC
        
        -- Get ability usage by player
        SELECT 
            source_entity as Player,
            ability_name as Ability,
            COUNT(*) as UseCount,
            SUM(damage_amount) as TotalDamage
        FROM combat_events
        WHERE ability_name IS NOT NULL
        GROUP BY source_entity, ability_name
        ORDER BY Player, TotalDamage DESC
        ```
        """)
    
    col1, col2 = st.columns([1, 1])
    execute_button = col1.button("Execute Query")
    clear_button = col2.button("Clear Results")
    
    if execute_button and query:
        try:
            import sqlite3
            import pandas as pd
            
            # Execute the query
            with sqlite3.connect(st.session_state.db_path) as conn:
                df = pd.read_sql_query(query, conn)
            
            # Display the results
            st.subheader("Query Results")
            st.dataframe(df)
            
            # Add download button for CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download Results as CSV",
                data=csv,
                file_name="query_results.csv",
                mime="text/csv",
            )
            
            # Show row count
            st.success(f"Query executed successfully. {len(df)} rows returned.")
            
        except Exception as e:
            st.error(f"Error executing query: {str(e)}")
    
    if clear_button:
        st.rerun()


def main():
    """Main function to run the Streamlit app."""
    # Set page config
    st.set_page_config(
        page_title="SMITE 2 Combat Log Agent",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Check for pending question from a previous button click
    if st.session_state.pending_question:
        # Get the question
        question = st.session_state.pending_question
        # Clear the pending question
        st.session_state.pending_question = None
        # Add the question to the messages
        st.session_state.messages.append({"role": "user", "content": question})
        # Process the question
        process_question_with_status(question)
        # Force a rerun to display the new messages
        st.rerun()
    
    # Create sidebar
    settings_sidebar()
    
    # Handle file processing if needed
    if st.session_state.processing_status == "processing":
        # Get the uploaded file from the session state file_uploader widget
        uploaded_file = st.session_state.file_uploader
        
        if uploaded_file:
            # Save the uploaded file to a temporary location
            temp_file = TEMP_DIR / uploaded_file.name
            with open(temp_file, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Process the log file with a progress bar
            with st.spinner(f"Processing {uploaded_file.name}..."):
                try:
                    db_path = process_log_file(temp_file)
                    if db_path:
                        st.session_state.db_path = db_path
                        st.session_state.processing_status = "complete"
                        st.success(f"✅ Log file processed successfully!")
                    else:
                        st.session_state.processing_status = "error"
                        st.error("❌ Failed to process log file. Please check the format.")
                except Exception as e:
                    st.session_state.processing_status = "error"
                    st.error(f"❌ Error processing log file: {str(e)}")
            
            # Force a rerun to update the UI
            st.rerun()
    
    # Create tabs for different pages
    tab1, tab2 = st.tabs(["Chat Interface", "SQL Query Tool"])
    
    with tab1:
        # If database exists, show the chat interface
        if st.session_state.db_path:
            chat_interface()
            
            # Add debug panel at the bottom if desired
            if st.session_state.get("show_debug", False):
                debug_panel()
        else:
            # Show instructions if no database is loaded yet
            st.info("👈 Please upload a SMITE 2 Combat Log file using the sidebar to begin.")
            
            st.markdown("""
            ### How to use the SMITE 2 Combat Log Agent:
            
            1. Upload your SMITE 2 Combat Log file (.log or .txt) using the sidebar
            2. Click "Process Log File" to analyze the data
            3. Once processing is complete, you can:
               - Ask questions about the match data in natural language
               - Run SQL queries directly against the database
               - Export the database to Excel for external analysis
            
            ### Example Questions:
            - "Who dealt the most damage in the match?"
            - "What abilities did the top player use most frequently?"
            - "Compare the damage output of the top 3 players"
            """)
    
    with tab2:
        sql_query_page()


if __name__ == "__main__":
    main() 