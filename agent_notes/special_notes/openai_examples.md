# OpenAI Agents SDK Example References

This document catalogs relevant examples from the OpenAI Agents SDK repository that relate to our multi-agent pipeline architecture design.

## Financial Research Agent

Source: [openai-agents-python/examples/financial_research_agent](https://github.com/openai/openai-agents-python/tree/main/examples/financial_research_agent)

This example implements a multi-agent financial research system with the following components:

1. **Planning Agent**: Turns the user's request into a list of search terms relevant to financial analysis
2. **Search Agent**: Uses the WebSearchTool to retrieve summaries for each search term
3. **Sub-Analysts**: Additional specialist agents exposed as tools for inline calls
4. **Writer Agent**: Combines search results and analyst inputs into a formatted report
5. **Verifier Agent**: Audits the report for inconsistencies or missing sources

**Relevance to our project**: This closely mirrors our pipeline architecture with specialized agents working in sequence. Their approach of using some agents as tools (rather than handoffs) could be valuable for our data analysis specialists.

## Agent Patterns

Source: [openai-agents-python/examples/agent_patterns](https://github.com/openai/openai-agents-python/tree/main/examples/agent_patterns)

This directory showcases various agent patterns:

1. **Deterministic Flows**: Breaking tasks into sequential steps performed by different agents
2. **Handoffs and Routing**: Using specialized sub-agents for specific tasks
3. **Agents as Tools**: Using agents as tools rather than complete handoffs
4. **LLM-as-a-Judge**: Using a second LLM to evaluate and provide feedback on outputs

**Relevance to our project**: 
- The deterministic flow pattern matches our pipeline model
- The agents-as-tools pattern could be useful for our specialist agents
- The LLM-as-a-judge pattern is similar to our Quality Reviewer agent

## Research Bot

Source: [openai-agents-python/examples/research_bot](https://github.com/openai/openai-agents-python/tree/main/examples/research_bot)

This example implements a research bot with these components:

1. **Planner Agent**: Creates a research plan with search queries
2. **Search Agents**: Run searches in parallel and summarize results
3. **Writer Agent**: Creates a final report from search summaries

**Relevance to our project**: The parallel search execution could be adapted for our Data Engineer stage to run multiple SQL queries simultaneously.

## Implementation Guidance

Based on these examples, we should consider:

1. **Agent Configuration**:
   ```python
   agent = Agent(
       name="QueryAnalyst",
       instructions=INSTRUCTIONS,
       model="gpt-4o",
       tools=[list_tables, get_table_schema, validate_sql]
   )
   ```

2. **Using Agents as Tools**:
   ```python
   # Create specialist agents
   data_analyst = Agent(name="DataAnalyst", instructions=INSTRUCTIONS)
   
   # Use as a tool in another agent
   orchestrator = Agent(
       name="Orchestrator",
       tools=[
           data_analyst.as_tool(
               tool_name="analyze_data",
               tool_description="Analyze data from queries"
           )
       ]
   )
   ```

3. **Sequential Pipeline Architecture**:
   ```python
   # Example from deterministic flow pattern
   async def run_pipeline(query):
       # Stage 1: Analyze query
       query_package = DataPackage(query)
       query_result = await Runner.run(query_analyst, query_package)
       
       # Stage 2: Process data
       data_result = await Runner.run(data_engineer, query_result.to_data_package())
       
       # Continue through pipeline...
   ```

These examples provide excellent reference implementations as we develop our multi-agent pipeline.