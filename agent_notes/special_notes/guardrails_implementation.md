# Data Fidelity Guardrails Implementation

This document provides detailed guidance on implementing data fidelity guardrails for the SMITE 2 Combat Log Agent's multi-agent architecture.

## Overview

Data fidelity guardrails are a critical component of our architecture that prevent Large Language Models (LLMs) from hallucinating or fabricating data, particularly when accessing real database information. They serve as a verification layer that ensures agents respect actual data rather than generating plausible but incorrect information.

## Guardrail Types

### 1. Output Guardrails

These run on the final agent output and validate its accuracy before delivering to the next agent or the user:

```python
@output_guardrail
async def data_fidelity_guardrail(ctx: RunContextWrapper, agent: Agent, output: OutputType) -> GuardrailFunctionOutput:
    """Validation logic here"""
    # Implementation
    return GuardrailFunctionOutput(
        output_info={"discrepancies": discrepancies},
        tripwire_triggered=len(discrepancies) > 0
    )
```

### 2. Input Guardrails

These run on the initial user input to an agent, useful for validating queries before processing:

```python
@input_guardrail
async def query_validation_guardrail(ctx: RunContextWrapper, agent: Agent, input: str) -> GuardrailFunctionOutput:
    """Validation logic here"""
    # Implementation
    return GuardrailFunctionOutput(
        output_info={"issues": issues},
        tripwire_triggered=len(issues) > 0
    )
```

## Core Validation Components

Our data fidelity guardrails perform several types of validation:

### 1. Entity Validation

Ensures correct entities (players, items, abilities) are mentioned and no fabricated entities are introduced:

```python
# Check for player name accuracy
for player_name in db_query_results["players"]:
    if player_name not in response:
        discrepancies.append(f"Player '{player_name}' from database not found in response")
    
    # Check for made-up player names
    known_players = set(db_query_results["players"].keys())
    for name_match in re.finditer(r'\b([A-Z][a-z]+)\b', response):
        name = name_match.group(1)
        if name not in known_players and name in ["Zephyr", "Ares", "Apollo"]:
            discrepancies.append(f"Made-up player name '{name}' found in response")
```

### 2. Numerical Validation

Validates numerical values like damage, healing, or other metrics:

```python
# Check for damage value accuracy
damage_patterns = [
    r"Total Damage:?\s+(\d{1,3}(?:,\d{3})*|\d+)",
    r"(\d{1,3}(?:,\d{3})*|\d+)\s+damage"
]

for pattern in damage_patterns:
    matches = re.finditer(pattern, response, re.IGNORECASE)
    for match in matches:
        damage_str = match.group(1).replace(",", "")
        try:
            damage_value = int(damage_str)
            
            # Check if this is a made-up value
            real_values = db_query_results["damage_values"]
            
            # Allow for some approximation (within 5%)
            is_real = any(abs(damage_value - real_value) / real_value < 0.05 
                          for real_value in real_values if real_value > 0)
            
            if not is_real:
                discrepancies.append(f"Made-up damage value '{damage_value}' found in response")
        except ValueError:
            pass
```

### 3. Statistical Validation

Ensures statistical claims are accurate:

```python
# Check for statistical claims
stat_patterns = [
    r"increased by (\d+(?:\.\d+)?)%",
    r"(\d+(?:\.\d+)?)% (higher|lower|more|less)"
]

# Similar validation logic
```

## Specialized Guardrails

Each agent type should have specialized guardrails focused on their particular data handling:

### 1. DataEngineerGuardrail

Validates SQL queries, database schema understanding, and resulting datasets:

```python
@output_guardrail
async def data_engineer_guardrail(ctx: RunContextWrapper, agent: Agent, output: DataEngineerOutput) -> GuardrailFunctionOutput:
    discrepancies = []
    
    # Validate SQL query correctness
    if "sql_query" in output and output.sql_query:
        if "DELETE" in output.sql_query.upper() or "UPDATE" in output.sql_query.upper():
            discrepancies.append("SQL query contains forbidden DELETE/UPDATE operations")
    
    # Validate schema understanding
    if "table_references" in output and output.table_references:
        valid_tables = ["players", "combat_events", "matches", "abilities", "item_events"]
        for table in output.table_references:
            if table not in valid_tables:
                discrepancies.append(f"Referenced non-existent table: {table}")
    
    # Additional validation logic
    
    return GuardrailFunctionOutput(
        output_info={"discrepancies": discrepancies},
        tripwire_triggered=len(discrepancies) > 0
    )
```

### 2. DataAnalystGuardrail

Focuses on analytical accuracy, statistical correctness, and interpretation:

```python
@output_guardrail
async def data_analyst_guardrail(ctx: RunContextWrapper, agent: Agent, output: DataAnalystOutput) -> GuardrailFunctionOutput:
    discrepancies = []
    
    # Validate statistical calculations
    # Validate trend identifications
    # Validate causal claims
    
    return GuardrailFunctionOutput(
        output_info={"discrepancies": discrepancies},
        tripwire_triggered=len(discrepancies) > 0
    )
```

### 3. VisualizationGuardrail

Ensures visualization data matches the actual query results:

```python
@output_guardrail
async def visualization_guardrail(ctx: RunContextWrapper, agent: Agent, output: VisualizationOutput) -> GuardrailFunctionOutput:
    discrepancies = []
    
    # Validate chart data matches query results
    # Validate axis labels are accurate
    # Validate legends reflect actual data
    
    return GuardrailFunctionOutput(
        output_info={"discrepancies": discrepancies},
        tripwire_triggered=len(discrepancies) > 0
    )
```

### 4. ResponseComposerGuardrail

Final verification that the response to the user contains accurate information:

```python
@output_guardrail
async def response_composer_guardrail(ctx: RunContextWrapper, agent: Agent, output: ResponseComposerOutput) -> GuardrailFunctionOutput:
    discrepancies = []
    
    # Comprehensive check of all data claims
    # Verify player stats, ability data, damage claims, etc.
    # Verify conclusions match the data
    
    return GuardrailFunctionOutput(
        output_info={"discrepancies": discrepancies},
        tripwire_triggered=len(discrepancies) > 0
    )
```

## Integration with DataPackage System

The guardrails should be tightly integrated with our DataPackage system:

```python
class DataPackage:
    # Existing fields...
    raw_query_results: Dict[str, Any] = {}  # Store raw query results for validation
    validated: bool = False  # Indicates if this package has passed guardrails
    
    def validate(self, guardrail) -> bool:
        # Run the guardrail check
        # Update validated status
        # Return validation result
```

## Error Handling Strategy

When a guardrail detects discrepancies, we need a graceful handling strategy:

1. **Logging**: Log detailed information about what discrepancies were found
2. **Retry**: For minor issues, retry with more explicit instructions
3. **Fallback**: For persistent issues, fall back to a more conservative response
4. **User Communication**: For critical issues, inform the user about limitations or problems

Example implementation:

```python
try:
    response = await runner.run(agent, query)
    # Process successful response
except OutputGuardrailTripwireTriggered as e:
    logger.warning(f"Guardrail triggered: {e.guardrail_result.output_info}")
    
    if retry_count < MAX_RETRIES:
        # Modify instructions to be more explicit based on discrepancies
        modified_instructions = enhance_instructions(agent.instructions, e.guardrail_result.output_info)
        retry_agent = Agent(
            name=agent.name,
            instructions=modified_instructions,
            # Other parameters...
        )
        return await process_with_retry(retry_agent, query, retry_count + 1)
    else:
        # Fall back to conservative response
        return generate_fallback_response(query, e.guardrail_result.output_info)
```

## Testing Framework

We need comprehensive tests for our guardrail system:

1. **Unit Tests**: Test individual guardrail validations
2. **Integration Tests**: Test how guardrails work with real agents
3. **Deliberate Error Tests**: Deliberately create responses with errors to test detection
4. **Performance Tests**: Ensure guardrails don't add excessive latency

Example test:

```python
def test_data_fidelity_guardrail_detects_fake_player():
    # Setup test data
    db_query_results = {"players": {"MateoUwU": 114622}}
    
    # Create fake response with wrong player
    fake_response = CombatAnalysisOutput(
        response="Player Zephyr dealt 35,000 damage..."
    )
    
    # Run guardrail
    result = asyncio.run(data_fidelity_guardrail(None, test_agent, fake_response))
    
    # Verify discrepancies were found
    assert result.tripwire_triggered
    assert any("Made-up player name 'Zephyr'" in d for d in result.output_info["discrepancies"])
```

## Implementation Roadmap

1. Create base `DataFidelityGuardrail` class with common validation functions
2. Implement specialized guardrails for each agent type
3. Add testing framework for guardrails
4. Integrate guardrails with the pipeline system
5. Implement retry and fallback mechanisms
6. Document guardrail implementation thoroughly

## Best Practices

1. **Balance Strictness**: Too strict guardrails might reject valid responses; too loose might allow errors
2. **Performance Consideration**: Keep guardrail validation efficient to minimize latency
3. **Maintenance**: Update guardrails as the database schema or agent functionality evolves
4. **Contextual Validation**: Consider the specific context of each query for validation
5. **Clear Error Messages**: Provide clear, actionable error messages when guardrails trigger 