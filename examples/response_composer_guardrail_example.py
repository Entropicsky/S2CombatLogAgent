async def main():
    """Run the example."""
    print("Starting ResponseComposerGuardrail Example...")
    print("ResponseComposerGuardrail Example - Testing with real database data")
    print("=" * 80)
    
    # First, test with accurate response composer (should pass)
    await run_example_with_agent(
        agent_name="AccurateResponseComposer",
        instructions=accurate_composer_instructions,
        should_pass=True
    )
    
    # ... existing code ... 