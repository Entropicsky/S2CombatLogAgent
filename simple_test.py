#!/usr/bin/env python3
"""
Simple test for OpenAI Agents SDK imports.
"""

import sys
print(f"Python version: {sys.version}")

print("Importing agents module...")
import agents
print(f"Agents module version: {agents.version}")

print("Importing specific classes...")
from agents import Agent, ModelSettings, Runner
print("Successfully imported Agent, ModelSettings, Runner")

print("Done") 