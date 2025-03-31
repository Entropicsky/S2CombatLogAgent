# SMITE 2 Combat Log Parser - Technical Specification

## Architecture Overview

The SMITE 2 Combat Log Parser is built using a modular architecture with the following key components:

1. **Parser Engine**: Core component that processes log files
2. **Data Model Layer**: ORM-based database schema
3. **Transformation Layer**: Converts raw data to structured format
4. **CLI Interface**: Command-line tools for user interaction
5. **Utility Scripts**: Additional processing and export tools

## Component Details

### Parser Engine (`parser.py`)

The parser engine is responsible for:
- Reading log files line by line
- Parsing JSON data from each line
- Identifying event types
- Batching events for database insertion
- Managing the processing workflow

Key classes:
- `CombatLogParser`: Main parser class with parsing logic

### Data Model Layer (`models.py`)

SQLAlchemy ORM models that define the database schema:
- `Match`: Match metadata
- `Player`: Player information
- `Entity`: Game entities
- `CombatEvent`: Combat interactions
- `RewardEvent`: Reward events
- `ItemEvent`: Item-related events
- `PlayerEvent`: Player-specific events
- `TimelineEvent`: Enhanced timeline events

### Transformation Layer (`transformers.py`)

Contains logic to transform raw event data into database records:
- Event type identification
- Data normalization
- Entity resolution
- Derived data calculation

### CLI Interface (`cli.py`)

Command-line interface with the following commands:
- `parse`: Process a log file
- `info`: Display database information
- `query`: Run SQL queries against the database
- `reprocess`: Update existing database entries

### Configuration (`config.py`)

Configuration settings for the parser:
- Database connection settings
- Processing options
- Logging configuration

### Utility Scripts

- **Timeline Enhancement**: Improves timeline data with additional metadata
- **Excel Export**: Exports database tables to Excel format
- **Data Migration**: Updates database schema when changes occur

## Data Flow

1. Log file is read by the Parser Engine
2. Events are parsed from JSON format
3. Transformers convert events to appropriate database entities
4. Data is batched and inserted into the SQLite database
5. Additional processing may occur through utility scripts
6. Data can be exported or queried as needed

## Database Schema

### Core Tables
- `matches`: Central table with match information
- `players`: Player records linked to matches
- `entities`: Game entities relevant to matches

### Event Tables
- `combat_events`: Combat interactions (damage, healing, deaths)
- `reward_events`: Experience and gold rewards
- `item_events`: Item purchases and upgrades
- `player_events`: Player-specific events

### Analysis Tables
- `timeline_events`: Enhanced timeline for match analysis
- `player_stats`: Aggregated player statistics

## Performance Considerations

- Batch processing for database operations
- Progressive parsing to handle large log files
- Transaction management to ensure data integrity
- SQLite pragmas for optimized performance

## Extension Points

The system allows for extension in the following areas:
- New event types can be added with corresponding models
- Additional transformers can be implemented for new data types
- Visualization components can be built on top of the database
- Analytics modules can be developed using the structured data 