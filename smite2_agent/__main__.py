#!/usr/bin/env python3
"""
Entry point for SMITE 2 Combat Log Analyzer.
"""

import sys
import subprocess


def print_usage():
    """Print usage information."""
    print("SMITE 2 Combat Log Analyzer")
    print("Usage:")
    print("  python -m smite2_agent cli <db_path> [options]")
    print("  python -m smite2_agent streamlit")
    print("")
    print("Commands:")
    print("  cli        Run the command-line interface")
    print("  streamlit  Run the Streamlit web interface")
    print("")
    print("For CLI options:")
    print("  python -m smite2_agent cli --help")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "cli":
        # Run the CLI app
        from smite2_agent.app import main as cli_main
        import asyncio
        asyncio.run(cli_main())
    
    elif command == "streamlit":
        # Run the Streamlit app
        import streamlit.web.cli
        
        sys.argv = ["streamlit", "run", "smite2_agent/streamlit_app.py"]
        streamlit.web.cli.main()
    
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main() 