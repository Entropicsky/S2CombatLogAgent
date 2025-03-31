#!/usr/bin/env python3
"""
Simple script to run the CLI directly, bypassing any argument parsing issues.
"""

import asyncio
import os
import sys
from pathlib import Path

from smite2_agent.app import main as cli_main

# Directly set sys.argv with the correct arguments
sys.argv = [
    "run_cli.py",  # Script name
    "data/CombatLogExample.db",  # Database path
    "--interactive"  # Interactive mode
]

# Run the CLI
if __name__ == "__main__":
    asyncio.run(cli_main()) 