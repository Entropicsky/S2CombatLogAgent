# Agent Data Package Reference

## Overview

The Agent Data Package is the standardized data structure that flows through the multi-agent pipeline. It contains all information needed by each agent to perform its task and accumulates results as it moves through the pipeline.

## Package Structure

```python
{
    "metadata": {
        "query_id": "unique-query-identifier",
        "timestamp": "2025-04-01T14:30:00Z",
        "user_id": "user-identifier",
        "session_id": "session-identifier",
        "pipeline_type": "combat_analysis", # or "timeline_analysis" or "player_analysis"
        "processing_stage": "data_analyst", # current agent handling the package
        "processing_history": [
            {
                "stage": "orchestrator",
                "agent_id": "orchestrator-1",
                "start_time": "2025-04-01T14:30:00Z",
                "end_time": "2025-04-01T14:30:01Z",
                "status": "success"
            },
            # ... other processing steps
        ]
    },
    
    "input": {
        "raw_query": "Who dealt the most damage in the match?",
        "context": {
            "previous_queries": [
                {
                    "query": "Show me the match summary",
                    "timestamp": "2025-04-01T14:28:00Z"
                }
            ],
            "match_id": "match-CombatLogExample",
            "focus_entities": [] # entities of interest extracted from context
        }
    },
    
    "query_analysis": {
        "query_type": "combat_analysis",
        "intent": "find_top_damage_dealer",
        "required_data_points": ["player_damage_totals", "damage_types"],
        "required_tables": ["combat_events", "players", "entities"],
        "sql_queries": [
            {
                "query_id": "q1",
                "purpose": "get_player_damage_totals",
                "sql": "SELECT source_entity, SUM(damage_amount) as total_damage FROM combat_events WHERE event_type = 'Damage' GROUP BY source_entity ORDER BY total_damage DESC",
                "dependencies": []
            }
        ],
        "anticipated_followups": [
            "What damage types did they use?",
            "Who took the most damage?",
            "How does their damage compare to average?"
        ]
    },
    
    "data": {
        "query_results": {
            "q1": {
                "status": "completed",
                "sql": "SELECT source_entity, SUM(damage_amount) as total_damage FROM combat_events WHERE event_type = 'Damage' GROUP BY source_entity ORDER BY total_damage DESC",
                "result_format": "dataframe",
                "column_types": {
                    "source_entity": "string",
                    "total_damage": "integer"
                },
                "result_summary": {
                    "row_count": 10,
                    "top_row": {"source_entity": "MateoUwU", "total_damage": 114622}
                },
                "data": [
                    {"source_entity": "MateoUwU", "total_damage": 114622},
                    {"source_entity": "AMIRHISOKA", "total_damage": 98540},
                    # ... additional rows
                ]
            }
        },
        "transformed_data": {
            "player_damage_totals": {
                "description": "Total damage dealt by each player",
                "data": [
                    {"player_name": "MateoUwU", "total_damage": 114622, "percentage": 27.5},
                    {"player_name": "AMIRHISOKA", "total_damage": 98540, "percentage": 23.6},
                    # ... additional rows
                ]
            }
        }
    },
    
    "analysis": {
        "key_findings": [
            {
                "finding_id": "f1",
                "description": "MateoUwU dealt the most damage with 114,622 total damage",
                "significance": "high",
                "supporting_data": "q1"
            },
            {
                "finding_id": "f2",
                "description": "This represents 27.5% of the team's total damage",
                "significance": "medium",
                "supporting_data": "player_damage_totals"
            }
        ],
        "patterns": [
            {
                "pattern_id": "p1",
                "description": "Damage distribution is concentrated in top 3 players (65% of total)",
                "significance": "medium",
                "supporting_data": "player_damage_totals"
            }
        ],
        "comparisons": [
            {
                "comparison_id": "c1",
                "description": "MateoUwU's damage is 16% higher than the second-highest damage dealer",
                "significance": "medium",
                "supporting_data": "player_damage_totals"
            }
        ],
        "recommended_visualizations": [
            {
                "viz_id": "v1",
                "type": "bar_chart",
                "title": "Total Damage by Player",
                "data_source": "player_damage_totals",
                "x_column": "player_name",
                "y_column": "total_damage",
                "importance": "high"
            }
        ]
    },
    
    "visualizations": {
        "v1": {
            "type": "bar_chart",
            "title": "Total Damage by Player",
            "file_path": "temp_charts/damage_by_player.png",
            "alt_text": "Bar chart showing MateoUwU with highest damage at 114,622",
            "embedded_data": "base64-encoded-image-data"
        }
    },
    
    "response": {
        "direct_answer": "MateoUwU dealt the most damage in the match with 114,622 total damage.",
        "key_insights": [
            "MateoUwU's damage output was 16% higher than the second-highest damage dealer (AMIRHISOKA).",
            "The top 3 damage dealers accounted for 65% of all damage in the match.",
            "MateoUwU contributed 27.5% of their team's total damage output."
        ],
        "visualizations": ["v1"],
        "supporting_data": "Based on combat event data from the match, MateoUwU consistently outperformed other players in damage output throughout all phases of the game.",
        "additional_context": "While MateoUwU dealt the most raw damage, efficiency metrics show that AMIRHISOKA had better damage-per-minute stats during the early game phase.",
        "followup_answers": {
            "damage_types": "MateoUwU primarily dealt physical damage (78%) with ability damage accounting for most of their output.",
            "damage_taken": "Despite high damage output, MateoUwU was third in damage taken, showing good positioning.",
            "comparison_to_average": "MateoUwU's damage was 35% above the match average of 84,905."
        }
    },
    
    "final_output": {
        "formatted_response": "# Match Analysis: Damage Output\n\nMateoUwU dealt the most damage in the match with **114,622 total damage**.\n\n## Key Insights\n\n* MateoUwU's damage output was 16% higher than the second-highest damage dealer (AMIRHISOKA).\n* The top 3 damage dealers accounted for 65% of all damage in the match.\n* MateoUwU contributed 27.5% of their team's total damage output.\n\n## Damage Distribution\n\n![Total Damage by Player](temp_charts/damage_by_player.png)\n\n## Additional Context\n\nWhile MateoUwU dealt the most raw damage, efficiency metrics show that AMIRHISOKA had better damage-per-minute stats during the early game phase.\n\nMateoUwU primarily dealt physical damage (78%) with ability damage accounting for most of their output. Despite high damage output, MateoUwU was third in damage taken, showing good positioning.\n\n---\n\n*Analysis based on combat event data from match-CombatLogExample*"
    },
    
    "errors": [
        {
            "stage": "visualization_specialist",
            "error_type": "minor",
            "description": "Could not generate pie chart for damage types due to missing data",
            "handled": true,
            "recovery_action": "Continued without damage type visualization"
        }
    ]
}
```

## Key Components

### Metadata
Contains information about the processing state, timing, and pipeline type. Useful for tracking, logging, and debugging.

### Input
The original query and contextual information from the conversation history.

### Query Analysis
Results from the Query Analyst including query classification, required data, SQL queries, and anticipated follow-up questions.

### Data
Raw and transformed data from the Data Engineer, including query results and processed datasets ready for analysis.

### Analysis
Insights and findings from the Data Analyst, including patterns, comparisons, and suggestions for visualization.

### Visualizations
Charts and other visualizations created by the Visualization Specialist.

### Response
Structured components of the response created by the Response Composer, including direct answer, key insights, and supporting information.

### Final Output
The fully formatted response that will be presented to the user.

### Errors
Any errors encountered during processing, including how they were handled.

## Usage Guidelines

1. **Adding Information**: Agents should add information to their respective sections without modifying sections created by previous agents unless necessary for correction.

2. **Data References**: When referring to data, use query_ids or other identifiers rather than duplicating large datasets.

3. **Error Handling**: If an agent encounters an error, it should add an entry to the errors array and attempt to continue processing if possible.

4. **Validation**: Each agent should validate that its required input fields are present before processing.

5. **Extensibility**: The package structure may be extended with additional fields as needed, but core fields should not be removed.

## Implementation Notes

- This package structure is designed to be JSON-serializable for easy storage and transmission.
- For large datasets, consider storing only summary statistics in the package and referencing external storage.
- The package should be immutable from the perspective of agents - they receive a copy, modify it, and pass a new copy forward.
- Sensitive information should be flagged appropriately for proper handling. 