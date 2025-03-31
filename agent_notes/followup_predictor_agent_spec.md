# FollowUpPredictorAgent Technical Specification

## Overview
The FollowUpPredictorAgent is a specialized agent designed to enhance user experience by anticipating and addressing follow-up questions. It analyzes both the original query and the generated response to predict what the user might ask next, then proactively enriches the response with additional relevant information and suggested follow-up questions.

## Goals
1. Predict the most likely follow-up questions based on:
   - The original query and its context
   - The generated response content
   - Database schema and available data
   - Common query patterns and user exploration behaviors

2. Enhance responses by:
   - Proactively answering the single most likely follow-up question
   - Adding 3-4 suggested follow-up questions for the user to explore
   - Guiding the user toward valuable insights they might not discover otherwise

3. Create a more conversational, exploratory experience that:
   - Anticipates user needs
   - Reduces the number of back-and-forth interactions needed
   - Guides users toward richer data exploration

## Architecture

### Position in Pipeline
The FollowUpPredictorAgent will be positioned after the ResponseComposerAgent and before potential visualization steps:

```
QueryAnalyst → DataEngineer → DataAnalyst → ResponseComposer → FollowUpPredictor → [VisualizationSpecialist]
```

### Input and Output
- **Input**: A DataPackage containing:
  - Original user query
  - Completed response from ResponseComposerAgent
  - Query analysis
  - Query results
  - Analysis results

- **Output**: Enhanced DataPackage with:
  - Enhanced response that includes the top follow-up answer
  - List of suggested follow-up questions
  - Metadata about the predicted follow-up questions and their rationale

### Core Components
1. **FollowUpPredictorAgent**: Main agent class implementing BaseAgent interface
2. **FollowUpPredictor**: Core prediction logic to generate follow-up questions
3. **ResponseEnhancer**: Logic to enhance the response with follow-up answers
4. **FollowUpPredictorGuardrail**: Ensures quality and relevance of predictions

## Implementation Details

### FollowUpPredictionStrategy
The agent will use a multi-step approach to predict follow-up questions:

1. **Context Analysis**:
   - Parse the original query and response
   - Identify key entities, relationships, and metrics mentioned
   - Extract temporal context and comparisons

2. **Question Generation**:
   - Generate candidate follow-up questions using templates
   - Apply domain-specific rules for SMITE combat analysis
   - Consider common exploration patterns (zoom in, compare, explain, etc.)

3. **Question Ranking**:
   - Score and rank questions based on relevance, information value, and exploration potential
   - Apply heuristics for which questions are most valuable given the current context
   - Ensure diversity in the final set of suggestions

4. **Proactive Answering**:
   - For the top question, generate an answer using existing query results when possible
   - When necessary, execute additional SQL queries to answer the top follow-up
   - Integrate the answer seamlessly into the original response

### Integration Method
The FollowUpPredictorAgent will be implemented as a standalone agent in the pipeline that:

1. Receives a DataPackage from the ResponseComposerAgent
2. Generates follow-up questions and enhances the response
3. Passes the enhanced DataPackage to the next agent in the pipeline

### Response Format Enhancement
We'll modify the response format to include:

```
Original Response Content
...

Additional Insights
[Proactive answer to the top follow-up question]

Suggested Follow-up Questions:
1. [Question 1]
2. [Question 2]
3. [Question 3]
```

## Tools and Methods

### Key Methods
```python
async def _process(self, data_package: DataPackage) -> DataPackage:
    """Process the data package and enhance with follow-up questions."""
    
async def _predict_followup_questions(self, query: str, response: str, data_package: DataPackage) -> List[Dict[str, Any]]:
    """Generate and rank potential follow-up questions."""
    
async def _enhance_response_with_followup(self, response: str, top_followup: Dict[str, Any]) -> str:
    """Enhance the response with the answer to the top follow-up question."""
    
async def _add_followup_suggestions(self, response: str, followups: List[Dict[str, Any]]) -> str:
    """Add suggested follow-up questions to the response."""
    
async def _execute_followup_query(self, followup: Dict[str, Any], data_package: DataPackage) -> Optional[Dict[str, Any]]:
    """Execute a query to answer a follow-up question if necessary."""
```

### Question Generation Templates
The implementation will include a set of templates for generating follow-up questions, such as:

1. **Drill-down questions**:
   - "What abilities did [top_player] use the most?"
   - "How did [player]'s [metric] change over time?"

2. **Comparison questions**:
   - "How does [player1] compare to [player2] in terms of [metric]?"
   - "What's the difference between [team1] and [team2] in [metric]?"

3. **Explanation questions**:
   - "Why did [player] have such a high [metric]?"
   - "What factors contributed to [team]'s performance in [metric]?"

4. **Contextual questions**:
   - "What happened after [event]?"
   - "How did [metric] change before and after [objective]?"

## Testing Strategy

### Unit Testing
1. **Question Generation Tests**:
   - Test template-based question generation
   - Verify entity extraction and substitution
   - Ensure diverse question types are generated

2. **Question Ranking Tests**:
   - Verify questions are properly scored and ranked
   - Test diversity measures in the selection algorithm
   - Validate heuristics for specific query types

3. **Response Enhancement Tests**:
   - Verify formatting and integration of follow-up answers
   - Test seamless insertion into different response formats
   - Ensure suggested questions appear correctly

### Integration Testing
1. **Pipeline Flow Tests**:
   - Test integration with the ResponseComposerAgent
   - Verify DataPackage handling and modification
   - Ensure all metadata is properly passed through

2. **End-to-End Tests**:
   - Test with various query types (player performance, combat analysis, etc.)
   - Verify the quality and relevance of suggested questions
   - Test the accuracy of proactive answers

3. **Real-Data Tests**:
   - Use CombatLogExample.db for realistic testing
   - Verify predictions with known analytical patterns
   - Test with a range of simple to complex queries

### Test Cases
1. **Simple Query**: "Which player dealt the most damage in the match?"
   - Expected follow-ups about abilities used, damage types, time distribution, etc.

2. **Comparative Query**: "Compare the damage output of Player1 and Player2"
   - Expected follow-ups about specific abilities, efficiency metrics, etc.

3. **Timeline Query**: "What happened in the first 10 minutes of the match?"
   - Expected follow-ups about specific events, turning points, etc.

## Implementation Plan

### Phase 1: Core Implementation
1. Create the FollowUpPredictorAgent class
2. Implement basic question generation with templates
3. Add a simple ranking mechanism
4. Create response enhancement functionality
5. Test with a limited set of query types

### Phase 2: Enhanced Features
1. Improve question generation with more templates and context awareness
2. Enhance ranking algorithm with more sophisticated heuristics
3. Add proactive query execution for questions that need additional data
4. Implement response enhancement with inline answers
5. Test with more complex queries and scenarios

### Phase 3: Integration and Refinement
1. Fully integrate with the pipeline architecture
2. Add guardrails for quality assurance
3. Optimize performance for various query types
4. Fine-tune the balance between response length and information value
5. Conduct comprehensive testing with all query types

## Evaluation Metrics
1. **Relevance**: How relevant are the suggested follow-up questions to the original query?
2. **Diversity**: Do the suggested questions cover different aspects of exploration?
3. **Usefulness**: Would the additional information and suggestions genuinely help the user?
4. **Coherence**: Does the enhanced response flow naturally and remain coherent?
5. **Performance**: What's the impact on response time and resource usage?

## Guardrails
The FollowUpPredictorGuardrail will enforce:
1. Relevance of follow-up questions to the original query
2. Factual accuracy of proactive answers
3. Reasonable response length after enhancement
4. Diversity in suggested questions
5. Appropriate tone and style consistency

## Next Steps
1. Implement base FollowUpPredictorAgent class
2. Create question generation templates
3. Develop ranking algorithm
4. Implement response enhancement logic
5. Create comprehensive test suite
6. Integrate with the pipeline 