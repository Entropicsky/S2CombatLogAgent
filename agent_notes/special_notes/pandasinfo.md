<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

# PandasAI Developer Guide

---

# PandasAI Developer Guide

Before diving in, this comprehensive guide summarizes key findings about PandasAI. PandasAI is a powerful Python library that makes data analysis conversational through natural language processing. It allows users to interact with various data sources including SQL databases, CSV files, pandas DataFrames, and more using everyday language rather than complex code.

## 1. Introduction to PandasAI

### What is PandasAI?

PandasAI is a Python platform developed by Sinaptik-AI that adds generative artificial intelligence capabilities to data analysis workflows. It's designed to make data interaction more intuitive by allowing users to ask questions in natural language[^6].

```python
# Basic concept of PandasAI
import pandasai as pai
df = pai.DataFrame(your_data)
result = df.chat("What insights can you give me about this data?")
```


### Key Features

- Natural language querying of data sources[^6][^11]
- Data visualization generation through simple text prompts[^6]
- Multi-DataFrame analysis with relationship understanding[^6]
- Support for various data sources (SQL, CSV, pandas, polars, MongoDB, etc.)[^11]
- Enterprise-grade security features[^7]
- Integration with leading LLM providers (GPT-3.5/4, Anthropic, VertexAI)[^11]


### Architecture Overview

PandasAI operates as either:

1. A standalone library used in Python environments[^6]
2. A client-server architecture for enterprise deployments[^6]
3. An integrated component in data platforms[^6]

## 2. Installation and Setup

### System Requirements

- Python 3.8+ (but below 3.12)[^6]
- Compatible with major operating systems (Windows, macOS, Linux)


### Installation Methods

**Using pip:**

```bash
pip install "pandasai&gt;=3.0.0b2"
```

**Using poetry:**

```bash
poetry add "pandasai&gt;=3.0.0b2"
```


### API Key Configuration

PandasAI uses BambooLLM by default, which requires an API key[^6][^11]:

```python
# Method 1: Environment variable
import os
os.environ["PANDASAI_API_KEY"] = "your-pai-api-key"

# Method 2: Direct setting
import pandasai as pai
pai.api_key.set("your-pai-api-key")
```

You can obtain a free API key by signing up at https://app.pandabi.ai[^6].

## 3. Basic Usage

### Creating DataFrames

Convert standard pandas DataFrames to PandasAI DataFrames:

```python
import pandasai as pai
import pandas as pd

# Original pandas DataFrame
pandas_df = pd.DataFrame({
    "country": ["United States", "United Kingdom", "France", "Germany", "Italy"],
    "sales": [5000, 3200, 2900, 4100, 2300]
})

# Convert to PandasAI DataFrame
df = pai.DataFrame(pandas_df)
```


### Asking Questions

The primary interaction method is through the `chat()` method:

```python
# Simple question
result = df.chat('Which country has the highest sales?')
print(result)  # Will output: United States

# More complex analysis
result = df.chat('What is the average sales value across all countries?')
print(result)
```


### Generating Visualizations

PandasAI can create charts based on natural language requests[^6][^11]:

```python
# Generate a bar chart
df.chat('Create a bar chart showing sales by country with different colors for each bar')

# Generate a more complex visualization
df.chat('Plot the sales data as a pie chart showing percentage contribution of each country')
```


### Working with Multiple DataFrames

PandasAI understands relationships between multiple DataFrames[^6]:

```python
# Create two related DataFrames
employees_df = pai.DataFrame({
    'EmployeeID': [1, 2, 3, 4, 5],
    'Name': ['John', 'Emma', 'Liam', 'Olivia', 'William'],
    'Department': ['HR', 'Sales', 'IT', 'Marketing', 'Finance']
})

salaries_df = pai.DataFrame({
    'EmployeeID': [1, 2, 3, 4, 5],
    'Salary': [5000, 6000, 4500, 7000, 5500]
})

# Ask questions across both DataFrames
pai.chat("Who gets paid the most?", employees_df, salaries_df)
# Output: Olivia gets paid the most.
```


## 4. Advanced Features

### Platform Integration

For teams wanting to use PandasAI collaboratively[^6]:

```python
import pandasai as pai

# Set up API key
pai.api_key.set("your-pai-api-key")

# Read data
file = pai.read_csv("./filepath.csv")

# Create and push dataset to the platform
dataset = pai.create(
    path="your-organization/dataset-name", 
    df=file, 
    name="dataset-name", 
    description="dataset-description"
)
dataset.push()
```


### Security Features

The `AdvancedSecurityAgent` provides protection against potentially malicious code execution[^7]:

```python
import pandasai as pai
from pandasai.agent.agent import Agent
from pandasai.ee.agents.advanced_security_agent import AdvancedSecurityAgent

# Create security agent
security = AdvancedSecurityAgent()

# Create agent with security
agent = Agent("your-data.csv", security=security)

# Even potentially suspicious queries will be analyzed for safety
response = agent.chat("""Find all records and summarize them""")
```


### Docker Sandbox

For enhanced security, run PandasAI in an isolated Docker environment[^6]:

```python
import pandasai as pai
from pandasai_docker import DockerSandbox

# Initialize the sandbox
sandbox = DockerSandbox()
sandbox.start()

# Use PandasAI with the sandbox
df = pai.DataFrame(your_data)
pai.chat("Analyze this data", df, sandbox=sandbox)

# Stop the sandbox when done
sandbox.stop()
```


### Command Line Interface

PandasAI provides a CLI for quick data analysis[^5][^9]:

```bash
pai -d "path/to/your/dataset.csv" -m "openai" -p "How many unique values are in column X?"
```

Available options:

- `-d, --dataset`: Path to dataset
- `-t, --token`: API token
- `-m, --model`: LLM choice (openai, open-assistant, starcoder, falcon, azure-openai, google-palm)
- `-p, --prompt`: Natural language query


## 5. Working with Different Data Sources

PandasAI supports various data sources beyond pandas DataFrames[^6][^11]:

### SQL Databases

```python
import pandasai as pai
from pandasai.connectors import SQLConnector

# Connect to a SQL database
connector = SQLConnector(
    dialect="mysql",
    host="localhost",
    port=3306,
    username="user",
    password="pass",
    database="mydatabase"
)

# Create an agent for the SQL database
agent = pai.Agent(connector)

# Query the database in natural language
result = agent.chat("Find the top 10 customers by revenue")
```


### CSV Files

```python
import pandasai as pai

# Read directly from CSV
agent = pai.Agent("path/to/your/file.csv")

# Ask questions about the CSV data
result = agent.chat("Summarize this dataset")
```


## 6. Development Patterns and Best Practices

### Effective Query Formulation

- Be specific with your questions
- Include column names when possible
- Specify required output formats explicitly
- Break complex requests into smaller steps

```python
# Less effective
df.chat("Show me data")

# More effective
df.chat("Show me the top 5 countries by sales value in a formatted table")
```


### Error Handling

From recent issues in the GitHub repository[^8], handle these common errors:

```python
import pandasai as pai

try:
    df = pai.DataFrame(your_data)
    result = df.chat("Your query")
except JSONDecodeError:
    # Handle JSON parsing errors
    print("JSON parsing error - check your data format")
except KeyError as e:
    # Handle missing key errors
    print(f"Missing key in data structure: {e}")
except FileNotFoundError as e:
    # Handle missing file errors
    print(f"File not found: {e}")
```


### Performance Optimization

Based on reported issues[^8]:

1. Avoid repeatedly adding DataFrames to DuckDB during chat sessions
2. For large datasets, consider using smaller test samples during development
3. Structure data efficiently before loading into PandasAI

## 7. Recent Updates and Releases

The latest releases include[^2]:

### v3.0.0a16 (March 21, 2025)

- Fixed SQL query double dash issue in URL paths
- Optimized loaders
- Improved error correction for code generation
- Fixed DataFrame redeclaration issues
- Added column content truncation for better performance


### v3.0.0-beta.15

- Added LiteLLM wrapper
- Fixed query builders with proper identifier quoting
- Improved support for Windows environments


## 8. Advanced Configuration

### Custom LLM Integration

While BambooLLM is the default, you can use various LLMs[^9]:

```python
import pandasai as pai
from pandasai.llm.openai import OpenAI
from pandasai.llm.google_palm import GooglePalm

# Using OpenAI
llm = OpenAI(api_token="YOUR_OPENAI_API_KEY")
agent = pai.Agent(your_data, llm=llm)

# Using Google Palm
llm = GooglePalm(api_token="YOUR_GOOGLE_API_KEY")
agent = pai.Agent(your_data, llm=llm)
```


### Privacy Settings

For sensitive data handling[^9]:

```python
import pandasai as pai

# Create agent with privacy enforced
agent = pai.Agent(your_data, enforce_privacy=True)
# This will only send column names to the LLM, not actual data
```


## 9. Troubleshooting Common Issues

Based on recent GitHub issues[^8]:

1. **ImportError with pandasai.core and pandasai.connectors**:
    - Ensure you have the latest version of PandasAI
    - Check Python version compatibility (3.8+ <3.12)
2. **Excel Reading Errors**:
    - Install additional dependencies: `pip install openpyxl`
    - Ensure file path is correct and file is not corrupted
3. **Chart Generation Problems**:
    - Install required visualization dependencies: `pip install matplotlib seaborn`
    - Check chart export path permissions
4. **LiteLLM Compatibility**:
    - When using Mixtral models, verify compatibility with current PandasAI version

## 10. License Information

PandasAI is licensed under the MIT expat license, with exceptions[^6][^14]:

- Content under "pandasai/ee/" directory has its own license
- Third-party components maintain their original licenses
- Enterprise offerings are available for commercial use


## 11. Community and Support

- GitHub Repository: https://github.com/sinaptik-ai/pandas-ai
- Documentation: https://pandasai-docs.readthedocs.io
- Issue Tracking: https://github.com/sinaptik-ai/pandas-ai/issues


## 12. Full Code Example

Here's a comprehensive example showing multiple features:

```python
import os
import pandas as pd
import pandasai as pai
from pandasai_docker import DockerSandbox

# Set up environment
os.environ["PANDASAI_API_KEY"] = "your-pai-api-key"

# Create sample data
sales_data = {
    "country": ["United States", "United Kingdom", "France", "Germany", "Italy"],
    "year": [2022, 2022, 2022, 2022, 2022],
    "quarter": ["Q1", "Q1", "Q1", "Q1", "Q1"],
    "sales": [5000, 3200, 2900, 4100, 2300],
    "expenses": [3000, 2100, 1800, 2500, 1400]
}

employee_data = {
    "country": ["United States", "United Kingdom", "France", "Germany", "Italy"],
    "employees": [120, 85, 67, 93, 42]
}

# Convert to pandas DataFrames
sales_df = pd.DataFrame(sales_data)
employee_df = pd.DataFrame(employee_data)

# Convert to PandasAI DataFrames
pai_sales = pai.DataFrame(sales_df)
pai_employees = pai.DataFrame(employee_df)

# Initialize Docker sandbox for security
sandbox = DockerSandbox()
sandbox.start()

try:
    # Ask a simple question
    print("=== Basic Query ===")
    result = pai_sales.chat("Which country had the highest sales?")
    print(result)
    
    # Generate a visualization
    print("\n=== Visualization ===")
    result = pai_sales.chat("Create a bar chart comparing sales and expenses by country")
    print("Visualization created")
    
    # Analyze across multiple dataframes
    print("\n=== Multi-DataFrame Analysis ===")
    result = pai.chat(
        "Calculate the sales per employee for each country and rank them", 
        pai_sales, 
        pai_employees,
        sandbox=sandbox
    )
    print(result)
    
    # Perform a more complex analysis
    print("\n=== Advanced Analysis ===")
    result = pai_sales.chat(
        "Calculate the profit for each country and show the profit margin as a percentage"
    )
    print(result)
    
finally:
    # Always stop the sandbox when done
    sandbox.stop()
```

This comprehensive developer guide should provide all the necessary information for an LLM to effectively develop applications using PandasAI, understanding its capabilities, best practices, and potential pitfalls.

<div>⁂</div>

[^1]: https://github.com/sinaptik-ai

[^2]: https://github.com/Sinaptik-AI/pandas-ai/releases

[^3]: https://github.com/sinaptik-ai/pandas-ai

[^4]: https://www.restack.io/p/pandas-ai-answer-advanced-data-analysis-cat-ai

[^5]: https://github.com/aitomatic/Pandas-AI

[^6]: https://github.com/sinaptik-ai/pandas-ai/blob/main/README.md

[^7]: https://www.restack.io/p/pandas-ai-answer-api-documentation-cat-ai

[^8]: https://github.com/sinaptik-ai/pandas-ai/issues

[^9]: https://pandasai-docs.readthedocs.io

[^10]: https://github.com/Sinaptik-AI/pandas-ai/blob/main/pandasai/agent/base.py

[^11]: https://pypi.org/project/pandasai/

[^12]: https://github.com/sinaptik-ai/pandas-ai/blob/main/MANIFEST.in

[^13]: https://www.linkedin.com/posts/miketamir_github-sinaptik-aipandas-ai-chat-with-activity-7198035041862508545-ANFH

[^14]: https://github.com/sinaptik-ai/pandas-ai/blob/main/LICENSE

[^15]: https://github.com/sinaptik-ai

[^16]: https://github.com/sinaptik-ai/pandas-ai/activity

[^17]: https://github.com/Sinaptik-AI/pandas-ai/issues/1315

[^18]: https://www.linkedin.com/posts/ppujari_github-sinaptik-aipandas-ai-chat-with-activity-7219504926404534272-1FKs

[^19]: https://blog.sinaptik.ai

[^20]: https://www.123ofai.com/post/pandas-ai

[^21]: https://waylonwalker.com/sinaptik-ai-pandas-ai/

