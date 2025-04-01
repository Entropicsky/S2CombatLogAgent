#!/usr/bin/env python3
"""
Run the SMITE 2 Combat Log Agent Streamlit app.
"""

import os
import sys
from pathlib import Path

def log(msg):
    print(msg, flush=True)

log("🐍 Starting run_streamlit.py")

log("📂 Imports loaded")

parent_dir = Path(__file__).parent
sys.path.insert(0, str(parent_dir))

log(f"🔍 Parent dir set: {parent_dir}")

if __name__ == "__main__":
    try:
        import streamlit.web.cli as stcli
        from dotenv import load_dotenv

        load_dotenv()

        streamlit_app_path = os.path.join(
            parent_dir, "smite2_agent", "ui", "streamlit_app.py"
        )

        if not os.path.exists(streamlit_app_path):
            log(f"❌ Error: Streamlit app not found at {streamlit_app_path}")
            sys.exit(1)

        log(f"🚀 Starting Streamlit app: {streamlit_app_path}")

        sys.argv = ["streamlit", "run", streamlit_app_path]
        sys.exit(stcli.main())

    except ImportError as e:
        log(f"❌ ImportError: {e}")
        log("👉 Please install required packages with:")
        log("   pip install streamlit python-dotenv")
        sys.exit(1)

    except Exception as e:
        log(f"❌ Unexpected error: {e}")
        sys.exit(1)