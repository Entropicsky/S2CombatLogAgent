# SMITE 2 Combat Log Agent - Technical Specification

## 1. Introduction

The SMITE 2 Combat Log Agent is designed to be a world-class data analysis system that provides comprehensive, accurate, and beautifully formatted answers to user queries about match data. The agent architecture is the core of this system and must be engineered for excellence.

## 2. System Goals

### 2.1 Primary Goals
- Provide expert-level analysis of SMITE 2 combat log data
- Deliver concise answers upfront followed by comprehensive supporting information
- Anticipate and address likely follow-up questions proactively
- Present information with professional formatting and appropriate visualizations
- Maintain conversational context for follow-up queries

### 2.2 User Experience Principles
- Responses should resemble what a highly-paid professional game data analyst would provide
- Information should be layered: answer first, then supporting data, then deeper insights
- All assertions should be backed by data
- Visual elements should complement rather than replace textual explanations
- Response format should prioritize readability and information hierarchy

## 3. Agent Pipeline Architecture

The system implements a multi-agent pipeline where each agent specializes in a specific task, with data flowing through the pipeline to produce a comprehensive response.

```
User Query → [Orchestrator] → Branches to specialized pipelines:
    ↓
    ├─→ [Query Analyst] → [Data Engineer] → [Data Analyst] → [Visualization Specialist] → [Response Composer] → [Quality Reviewer] → Final Response
    ├─→ [Timeline Specialist Pipeline]
    └─→ [Player Specialist Pipeline]
```

Each stage is protected by data fidelity guardrails that prevent hallucination and ensure response accuracy.

### 3.1 Agent Roles and Responsibilities

#### 3.1.1 Orchestrator Agent
- **Purpose**: Direct queries to the appropriate specialist pipeline based on question type
- **Key Functions**:
  - Classify incoming queries by domain (combat events, timeline events, player performance)
  - Route to appropriate pipeline or handle simple queries directly
  - Maintain conversation context across multiple queries
  - Coordinate workflow between specialist agents
  - Handle agent failures and fallbacks
- **Guardrails**: Input validation, query classification verification

#### 3.1.2 Query Analyst
- **Purpose**: Understand the user's question and translate it into a data retrieval plan
- **Key Functions**:
  - Identify required data points and tables needed
  - Formulate optimal SQL queries for data extraction
  - Determine additional context needed beyond the direct question
  - Identify potential follow-up questions to address proactively
  - Create a query execution plan with dependency order
- **Guardrails**: Schema validation, query plan verification

#### 3.1.3 Data Engineer
- **Purpose**: Execute queries and transform raw data into analysis-ready formats
- **Key Functions**:
  - Execute SQL queries with proper security validation
  - Perform data cleaning and transformation as needed
  - Handle query performance optimization
  - Manage data caching for repeated queries
  - Prepare datasets for both analysis and visualization
- **Guardrails**: SQL query validation, database schema understanding, query result verification

#### 3.1.4 Data Analyst
- **Purpose**: Interpret query results and extract meaningful insights
- **Key Functions**:
  - Perform statistical analysis on retrieved data
  - Identify patterns, anomalies, and correlations
  - Compare results against relevant benchmarks or averages
  - Generate analytical conclusions based on the data
  - Suggest appropriate visualization methods for key insights
- **Guardrails**: Statistical claim validation, insight accuracy verification, numerical value validation

#### 3.1.5 Visualization Specialist
- **Purpose**: Create informative and attractive visualizations of the data
- **Key Functions**:
  - Select optimal chart types based on data characteristics
  - Generate clear, properly labeled visualizations
  - Ensure visualizations highlight key insights
  - Create multiple visualizations for complex data when appropriate
  - Format charts for readability and professional appearance
- **Guardrails**: Visualization data validation, chart accuracy verification

#### 3.1.6 Response Composer
- **Purpose**: Combine analyses and visualizations into a cohesive, well-structured response
- **Key Functions**:
  - Format the direct answer prominently at the beginning
  - Structure supporting information logically
  - Integrate visualizations with explanatory text
  - Include proactive answers to anticipated follow-up questions
  - Format text with appropriate headers, bullet points, and emphasis
- **Guardrails**: Response content validation, entity reference validation, comprehensive factual verification

#### 3.1.7 Quality Reviewer
- **Purpose**: Review and refine the complete response before delivery
- **Key Functions**:
  - Verify that the direct question is answered clearly
  - Check for completeness and accuracy of information
  - Ensure readable formatting and proper integration of visualizations
  - Remove redundancies and improve clarity
  - Add polish to ensure professional quality
- **Guardrails**: Final verification against all source data, comprehensive response validation

### 3.2 Domain-Specific Specialist Pipelines

Each domain-specific pipeline follows the same general structure but with specialized knowledge and tools:

#### 3.2.1 Combat Analysis Pipeline
- Focuses on damage, kills, abilities, and combat events
- Specialized in damage type analysis, kill participation, and effectiveness metrics
- Optimized for combat event tables and combat-related statistics
- Domain-specific guardrails for combat event validation

#### 3.2.2 Timeline Analysis Pipeline
- Focuses on match progression, phase analysis, and chronological patterns
- Specialized in understanding game phases, timing of key events, and momentum shifts
- Optimized for timeline events and time-series visualizations
- Domain-specific guardrails for temporal validation

#### 3.2.3 Player Performance Pipeline
- Focuses on individual player stats, builds, and comparative performance
- Specialized in evaluating build efficiency, play patterns, and player contributions
- Optimized for player-centric metrics and comparative analysis
- Domain-specific guardrails for player identity validation

## 4. Data Flow and Communication

### 4.1 Inter-Agent Communication
- Agents pass structured data packages between pipeline steps
- Each package contains:
  - Original user query
  - Accumulated context and intermediate results
  - Processing metadata (timing, confidence scores)
  - Raw data stored for validation
  - Validation history and results
  - Status flags for error handling

### 4.2 Agent Handoff Protocol
1. **Initialization**: Each agent receives complete context from previous agent
2. **Processing**: Agent performs its specialized task
3. **Enrichment**: Agent adds its output to the data package
4. **Validation**: Agent output is validated through data fidelity guardrails
5. **Handoff**: Agent passes enriched and validated package to next pipeline agent

### 4.3 Error Handling and Fallbacks
- Each agent implements error detection and handling appropriate to its role
- Guardrail tripwires trigger fallback paths or retry mechanisms
- Pipeline includes multiple fallback paths for handling agent failures
- Orchestrator can redirect to simpler processing path if specialized pipeline fails
- All errors and guardrail violations are logged for improvement of system over time

### 4.4 Implementation Patterns

Based on insights from OpenAI Agents SDK examples, we implement several agent interaction patterns:

#### 4.4.1 Pipeline Flow (Primary Pattern)
- Sequential flow through specialized agents as outlined in the main architecture
- Each stage focuses on a specific aspect of the analysis process
- Data package flows through the pipeline with enrichment at each stage
- Used for the primary query path where the sequence of operations is well-defined

#### 4.4.2 Agents as Tools (Specialist Integration)
- Specialist agents (like Data Analyst and Visualization Specialist) can also be exposed as tools
- This allows other agents to call them directly without a complete handoff
- Benefits:
  - Allows more flexible integration of specialist capabilities
  - Enables composable analysis patterns where multiple specialists contribute
  - Reduces overhead for simple specialist tasks
- Implementation:
  ```python
  specialist_agent = Agent(name="DataAnalyst", instructions="...")
  
  # Main agent can call specialist directly as a tool
  main_agent = Agent(
      name="ResponseComposer",
      tools=[
          specialist_agent.as_tool(
              tool_name="analyze_data",
              tool_description="Get specialized data analysis"
          )
      ]
  )
  ```

#### 4.4.3 Parallel Execution
- Multiple SQL queries can be executed in parallel during the Data Engineer stage
- Multiple analyses can be performed simultaneously by specialist agents
- Implementation:
  ```python
  async def execute_queries(queries):
      tasks = [execute_query(query) for query in queries]
      return await asyncio.gather(*tasks)
  ```

#### 4.4.4 LLM-as-a-Judge Pattern
- The Quality Reviewer agent implements a "judge" pattern for output quality assurance
- It evaluates outputs against quality metrics and suggests improvements
- Can optionally return outputs to previous stages for refinement in case of issues

#### 4.4.5 Guardrail Verification Pattern
- Each agent output passes through data fidelity guardrails before proceeding to next stage
- Guardrails validate that response data matches the actual data queried from database
- Prevents hallucination and fabrication of player names, statistics, and abilities
- Implementation:
  ```python
  try:
      # Process query and generate response
      response = await agent.process(query)
      
      # Validate response against database values
      await data_package.validate_with_guardrail(guardrail, agent, response, "stage_name")
      
      # If validation passes, proceed to next step
      return response
  except OutputGuardrailTripwireTriggered as e:
      # Handle guardrail failure (retry or fallback)
      return handle_guardrail_failure(e)
  ```

### 4.5 Hybrid Architecture

The overall system uses a hybrid architecture combining these patterns:

1. **Core Pipeline**: The main flow follows the pipeline pattern from Orchestrator through specialized stages
2. **Specialist Tools**: Specialist capabilities are exposed both as pipeline stages and as tools
3. **Parallel Processing**: Data retrieval and analysis stages leverage parallel execution when appropriate
4. **Quality Feedback Loop**: Quality review can trigger refinement of responses when needed
5. **Guardrail Verification**: Every stage output is verified for factual accuracy before proceeding

This hybrid approach combines the clarity and structure of the pipeline model with the flexibility and efficiency of tool-based and parallel execution patterns, while ensuring data fidelity through comprehensive guardrails.

## 5. Implementation Details

### 5.1 Agent Implementation

#### 5.1.1 Common Agent Structure
All agents share a common structure:
- **Name**: Unique identifier for the agent
- **Instructions**: Role-specific guidance to focus the agent
- **Model**: The model to use (e.g., "gpt-4o")
- **Model Settings**: Configuration parameters like temperature, max_tokens, etc.
- **Tools**: Specialized functions available to the agent
- **Guardrails**: Data fidelity validation for inputs and outputs
- **Handoffs**: Other agents this agent can hand off to (for orchestrator/routing agents)
- **Handoff Description**: Description for other agents to decide when to hand off to this agent
- **Input Schema**: Expected structure of incoming data
- **Output Schema**: Required structure of outgoing data
- **Error Handling**: Agent-specific error management

#### 5.1.2 Tool Integration
Each agent has access to specific tools relevant to its role:
- **Query Analyst**: Schema exploration, query validation tools
- **Data Engineer**: SQL execution, data transformation tools
- **Data Analyst**: Statistical analysis, data insights tools
- **Visualization Specialist**: Chart generation, visualization styling tools
- **Response Composer**: Markdown formatting, template management tools
- **Quality Reviewer**: Content validation, formatting validation tools

### 5.2 Database Interaction
- All database interactions use secure, read-only connections
- Query validation ensures only safe queries are executed
- Query caching improves performance for repeated queries
- Schema information is pre-loaded for query planning optimization
- Query results are stored in raw form for guardrail validation

### 5.3 Data Fidelity Guardrails

We've implemented a comprehensive guardrail system to prevent hallucination and ensure factual accuracy:

#### 5.3.1 Base DataFidelityGuardrail
- **Core functionality**: Common validation methods for all specialized guardrails
- **Validation types**:
  - Entity existence validation (ensure correct players, abilities, etc. are mentioned)
  - Fabricated entity detection (prevent made-up players, abilities, etc.)
  - Numerical value validation (ensure damage values, statistics match database)
  - Statistical claim validation (verify percentage increases, comparisons)
- **Implementation**:
  ```python
  class DataFidelityGuardrail(ABC):
      def validate_entity_existence(self, response, known_entities, entity_type):
          # Verify required entities are present
      
      def validate_no_fabricated_entities(self, response, known_entities, entity_type):
          # Detect fabricated entities
      
      def validate_numerical_values(self, response, known_values, value_type):
          # Validate numerical claims
      
      @abstractmethod
      async def validate(self, ctx, agent, output):
          # Must be implemented by specific guardrails
  ```

#### 5.3.2 Specialized Guardrails
- **DataEngineerGuardrail**: Validates SQL queries and database schema understanding
- **DataAnalystGuardrail**: Validates analytical claims and statistical interpretations
- **VisualizationGuardrail**: Validates that visualizations accurately represent data
- **ResponseGuardrail**: Validates final response for factual accuracy and completeness

#### 5.3.3 Guardrail Integration with DataPackage
- DataPackage includes validation history and results
- Raw query data is stored for validation purposes
- Response validation ensures reliability at every stage

### 5.4 Visualization Generation
- Visualizations are generated using Matplotlib with a custom styling theme
- Chart types are selected based on data characteristics and insight type
- All charts include proper labels, legends, and titles
- Charts are embedded in markdown responses or saved as files as appropriate
- Visualization data is verified against source data for accuracy

### 5.5 Response Formatting
- Responses follow a consistent structure:
  1. **Direct Answer**: Concise response to the main question
  2. **Key Insights**: Bulleted list of most important findings
  3. **Supporting Data**: Relevant statistics and visualizations
  4. **Additional Context**: Related information and proactive answers to follow-ups
  5. **Methodology Note**: Brief explanation of how the analysis was performed
- Markdown formatting is used for emphasis, headers, and lists
- Code blocks are used for displaying raw data when appropriate

## 6. Performance Considerations

### 6.1 Response Time Optimization
- Implement caching at multiple levels:
  - Query results caching
  - Visualization caching
  - Schema information caching
- Use asynchronous processing where possible
- Implement progressive response generation for longer analyses
- Optimize guardrail validation for minimal overhead

### 6.2 Resource Management
- Limit visualization complexity for performance
- Implement timeout handling for long-running queries
- Use connection pooling for database interactions
- Optimize memory usage for large datasets
- Implement retry mechanisms with backoff for failing components

## 7. Testing and Evaluation

### 7.1 Quality Metrics
- **Accuracy**: Correctness of factual information and analysis
- **Completeness**: Coverage of relevant aspects of the question
- **Clarity**: Readability and understandability of the response
- **Formatting**: Professional appearance and proper structure
- **Insight Value**: Depth and usefulness of analytical insights
- **Guardrail Effectiveness**: Success rate in preventing hallucinations

### 7.2 Testing Methodology
- Develop a comprehensive test suite for pipeline components
- Create tests specifically for guardrail validation
- Develop "adversarial" tests to verify guardrail effectiveness
- Create gold-standard reference responses for comparison
- Implement automated testing of agent pipeline components
- Conduct regular end-to-end testing of the full system

## 8. Implementation Plan

### 8.1 Phase 1: Core Pipeline (Completed)
- Implement the base agent and pipeline structure
- Develop DataPackage for inter-agent communication
- Create basic examples to validate pipeline approach
- Test with simple queries

### 8.2 Phase 2: Data Fidelity Guardrails (Current)
- Implement base DataFidelityGuardrail class
- Develop specialized guardrails for each agent role
- Integrate guardrails with DataPackage system
- Test guardrail effectiveness against hallucinations

### 8.3 Phase 3: Specialized Agents (Next)
- Implement each specialized agent role
- Integrate with database and visualization tools
- Create domain-specific pipeline variants
- Develop retry and fallback mechanisms

### 8.4 Phase 4: Refinement and Optimization
- Implement caching and performance optimizations
- Enhance error handling and fallback mechanisms
- Refine response quality and formatting
- Add support for more complex query types

## 9. Future Enhancements

### 9.1 Potential Enhancements
- Comparative analysis across multiple matches
- Player trend analysis over time
- Team composition effectiveness analysis
- Meta analysis and strategy recommendations
- Interactive visualizations in web interface
- Advanced guardrails for more specialized validation

## 10. Conclusion

The multi-agent pipeline architecture described in this specification is designed to deliver exceptional quality analysis of SMITE 2 combat log data. By breaking down the analysis process into specialized steps performed by purpose-built agents, the system can achieve a level of sophistication and quality comparable to human expert analysis while maintaining the advantages of AI-powered automation. 

The addition of comprehensive data fidelity guardrails ensures that all responses are factually accurate and prevents hallucination or fabrication of information, addressing a critical challenge in LLM-based analysis systems. 

## Enhanced Multi-Agent Architecture (2025-03-31)

Building on our current pipeline implementation, we'll enhance the architecture to support parallel agent execution and domain-specific validation:

### Parallel Specialized Agents

Instead of a simple linear pipeline, we'll implement multiple specialized agents that can run in parallel:

1. **Data Engineer Agent** (existing)
   - Translates natural language to SQL
   - Retrieves data from the database
   - Validates SQL against schema

2. **Data Analyst Agent** (existing)
   - Analyzes query results
   - Generates statistical insights
   - Identifies patterns and outliers

3. **Visualization Agent** (new)
   - Creates charts, graphs, and visual representations
   - Selects optimal visualization types for the data
   - Generates and embeds visualizations in responses

4. **Context Agent** (new)
   - Provides historical/comparative context
   - Connects current data to broader patterns
   - Enhances understanding with related information

5. **Pattern Agent** (new)
   - Identifies gameplay patterns
   - Detects strategies and counter-strategies
   - Finds non-obvious correlations in the data

6. **Timeline Agent** (new)
   - Maps how events unfolded chronologically
   - Identifies key moments and turning points
   - Provides temporal context to events

7. **Response Composer Agent** (existing, enhanced)
   - Assembles contributions from all agents
   - Creates a cohesive narrative with layered information
   - Organizes content in a logical, structured way

8. **SMITE Expert Agent** (new)
   - Validates responses against game knowledge
   - Adds domain-specific context and interpretation
   - Serves as a "bullshit detector" for accuracy
   - Explains the significance of statistics in SMITE context

### Enhanced Orchestration

The Orchestrator will be upgraded to:

1. **Parallel Processing**
   - Execute compatible agents simultaneously
   - Manage dependencies between agent outputs
   - Aggregate results from parallel processes

2. **Dynamic Agent Selection**
   - Determine which specialized agents are relevant to the query
   - Create customized workflows based on query type
   - Adaptively expand or contract the agent pool based on complexity

3. **Enhanced Data Package**
   - Support multi-agent contributions in structured sections
   - Maintain clear provenance of information
   - Track confidence levels and validation status

### Response Composition

The response composition process will be enhanced to:

1. **Layer Information**
   - Core facts from Data Analyst
   - Visual elements from Visualization Agent
   - Context and patterns from specialized agents
   - Game-specific insights from SMITE Expert

2. **Structured Organization**
   - Clear sectioning based on information type
   - Progressive disclosure (most relevant first)
   - Supporting details and methodology descriptions

3. **Domain Validation**
   - All responses pass through SMITE Expert validation
   - Facts are checked against game mechanics knowledge
   - Domain-specific context is added
   - Significance of statistics is explained in game terms

### Implementation Approach

1. **Staged Rollout**
   - Implement SMITE Expert agent first as final validation layer
   - Add Visualization Agent to enhance current responses
   - Progressively add other specialized agents
   - Enhance orchestrator to support increasing parallelism

2. **Domain Knowledge Integration**
   - Create SMITE-specific knowledge base for the expert agent
   - Include god abilities, items, mechanics, and meta strategies
   - Build statistical benchmarks for meaningful comparisons

3. **Enhanced DataPackage**
   - Expand to support multi-agent contributions
   - Add sections for visualizations, domain context, etc.
   - Create standardized formats for each agent's outputs

This enhanced architecture will provide much richer, more accurate, and more contextually relevant responses to user queries about SMITE combat logs. 