# Structured Response Format Documentation

## Overview

The SMITE 2 Combat Log Agent now supports a structured JSON response format that provides both user-friendly answers and detailed debugging information. This format is designed to facilitate integration with web UIs while providing comprehensive transparency into the agent's processing.

## Response Format Structure

The response format consists of four main sections:

```json
{
  "user_response": {
    "formatted_answer": "The natural language answer for the user",
    "suggested_followups": ["Question 1", "Question 2", "Question 3"]
  },
  "pipeline_details": {
    "queries": [
      {
        "query_id": "query1",
        "purpose": "Find player with highest damage",
        "sql": "SELECT c.source_entity...",
        "execution_time_ms": 13.21,
        "results": [{"PlayerName": "psychotic8BALL", "TotalDamage": 193585}, ...]
      }
    ],
    "analysis": {
      "key_findings": [...],
      "patterns": [...],
      "raw_results": {...}
    },
    "process_flow": [
      {
        "stage": "data_engineer",
        "agent_id": "DataEngineerAgent",
        "start_time": "2025-03-31T11:47:09.077547",
        "end_time": "2025-03-31T11:47:09.091514",
        "duration_ms": 13.97,
        "status": "success"
      }
    ]
  },
  "metadata": {
    "query_id": "f5b2ea1f-86b4-4c76-8f6d-c645f562d3ed",
    "timestamp": "2025-03-31T11:47:09.077489",
    "pipeline_type": null,
    "errors": []
  },
  "performance_metrics": {
    "total_processing_time_ms": 13.97,
    "stage_breakdown": [
      {
        "stage": "data_engineer",
        "time_ms": 13.97,
        "percentage": 100.0
      }
    ],
    "slowest_stage": {
      "stage": "data_engineer",
      "time_ms": 13.97
    },
    "query_execution_time_ms": 13.21
  }
}
```

## Section Details

### 1. user_response

Contains the information that should be presented to the end user:

- `formatted_answer`: The complete, formatted response to the user's question
- `suggested_followups`: A list of suggested follow-up questions

### 2. pipeline_details

Contains detailed information about the pipeline processing:

- `queries`: List of all SQL queries executed, including:
  - `query_id`: Unique identifier for the query
  - `purpose`: Description of the query's purpose
  - `sql`: The actual SQL query executed
  - `execution_time_ms`: How long the query took to execute
  - `results`: Limited set of results (first 25 rows)
  - `row_count`: Total number of rows returned

- `analysis`: Results from the data analysis stage:
  - `key_findings`: List of important findings identified
  - `patterns`: List of patterns detected in the data
  - `raw_results`: Raw analysis results

- `process_flow`: Detailed trace of pipeline stages:
  - `stage`: Name of the pipeline stage
  - `agent_id`: ID of the agent that handled this stage
  - `start_time`: When processing started (ISO format)
  - `end_time`: When processing ended (ISO format)
  - `duration_ms`: Duration in milliseconds
  - `status`: "success" or "failed"

### 3. metadata

Contains information about the query execution:

- `query_id`: Unique identifier for this query
- `timestamp`: When the query was executed
- `pipeline_type`: Type of pipeline used (if specialized)
- `errors`: List of any errors encountered

### 4. performance_metrics

Contains detailed timing information:

- `total_processing_time_ms`: Total time for the entire pipeline
- `stage_breakdown`: Breakdown of time spent in each stage:
  - `stage`: Name of the stage
  - `time_ms`: Time in milliseconds
  - `percentage`: Percentage of total time
- `slowest_stage`: Information about the slowest stage
- `query_execution_time_ms`: Total time spent executing SQL queries

## Usage in CLI

The CLI supports three output formats:

```bash
# Default text output
python simple_cli.py "Who dealt the most damage?"

# Simple JSON with just the answer and followups
python simple_cli.py "Who dealt the most damage?" --output json

# Complete debug JSON with all metadata
python simple_cli.py "Who dealt the most damage?" --output debug_json
```

## Web UI Integration

This format is specifically designed for web UIs:

### Main View
- Display `user_response.formatted_answer` prominently
- Present `user_response.suggested_followups` as clickable suggestions

### Debug Panel
- Show SQL queries in a collapsible "Queries" section
- Display performance metrics in a "Performance" tab
- Show raw database results in a "Results" tab
- Visualize the process flow in a "Pipeline" tab

### Other Features
- Enable highlighting of slow queries or stages
- Provide export functionality for the debug information
- Add a toggle to show/hide the debug panel

## Implementation

The format is generated using the `to_debug_json()` method in the `DataPackage` class:

```python
# Get debug JSON from DataPackage
data_package = await process_query(db_path, query, model, include_followups)
debug_json = data_package.to_debug_json()
```

See `smite2_agent/pipeline/base/data_package.py` for the complete implementation.

## Error Handling

Errors are included in the `metadata.errors` array, with each error containing:

- `agent`: Name of the agent that encountered the error
- `error`: Error message
- `error_type`: Type of error (e.g., "sql_execution_error", "validation_error")

Even when errors occur, the system attempts to provide a meaningful response. 