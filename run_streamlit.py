#!/usr/bin/env python3
"""
Run the SMITE 2 Combat Log Agent Streamlit app.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path
parent_dir = Path(__file__).parent
sys.path.insert(0, str(parent_dir))

# Run the Streamlit app
if __name__ == "__main__":
    try:
        import streamlit.web.cli as stcli
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv()
        
        # Construct the path to the Streamlit app
        streamlit_app_path = os.path.join(
            parent_dir, "smite2_agent", "ui", "streamlit_app.py"
        )
        
        # Check if file exists
        if not os.path.exists(streamlit_app_path):
            print(f"Error: Streamlit app not found at {streamlit_app_path}")
            sys.exit(1)
        
        print(f"Starting Streamlit app: {streamlit_app_path}")
        
        # Use Streamlit CLI to run the app
        sys.argv = ["streamlit", "run", streamlit_app_path]
        stcli.main()
        
    except ImportError as e:
        print(f"Error: Required packages not installed. {e}")
        print("Please install the required packages with:")
        print("pip install streamlit python-dotenv")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting Streamlit app: {e}")
        sys.exit(1) 