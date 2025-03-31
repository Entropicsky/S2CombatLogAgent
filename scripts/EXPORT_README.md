# SMITE 2 Combat Log Excel Export Documentation

## Overview

The `export_to_excel.py` script extracts data from the SMITE 2 Combat Log SQLite database and exports it to Excel format for analysis and visualization. This document provides a comprehensive explanation of the database schema, the exported dataframes, and how to interpret the data.

## Database Schema

The SMITE 2 Combat Log Parser uses a relational database with multiple interconnected tables. Each table serves a specific purpose in storing different aspects of match data.

### Core Tables

#### `matches` Table

Stores the central information about each match.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `match_id` | STRING | Primary key identifier for the match, typically formatted as "match-{filename}" |
| `source_file` | STRING | Name of the source log file that generated this match data |
| `map_name` | STRING | Name of the map on which the match was played |
| `game_type` | STRING | Type of game mode (e.g., "Conquest", "Arena") |
| `start_time` | DATETIME | Timestamp when the match started |
| `end_time` | DATETIME | Timestamp when the match ended |
| `duration_seconds` | INTEGER | Total duration of the match in seconds |
| `match_data` | TEXT | Additional JSON-encoded match metadata (if available) |

#### `players` Table

Contains information about each player in the match.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `player_id` | INTEGER | Auto-incrementing primary key |
| `match_id` | STRING | Foreign key referencing matches.match_id |
| `player_name` | STRING | Username of the player |
| `team_id` | INTEGER | Team identifier (1 = Order, 2 = Chaos) |
| `role` | STRING | Role assigned to the player (Jungle, Support, Solo, Middle, Carry) |
| `god_id` | INTEGER | Numerical identifier for the god/character played |
| `god_name` | STRING | Name of the god/character played |

#### `entities` Table

Tracks all entities (players, minions, objectives, etc.) in the match.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `entity_id` | INTEGER | Auto-incrementing primary key |
| `match_id` | STRING | Foreign key referencing matches.match_id |
| `entity_name` | STRING | Name of the entity |
| `entity_type` | STRING | Type of entity (player, minion, objective, etc.) |
| `team_id` | INTEGER | Team identifier (1 = Order, 2 = Chaos, NULL = Neutral) |

### Event Tables

#### `combat_events` Table

Records combat interactions between entities.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `event_id` | INTEGER | Auto-incrementing primary key |
| `match_id` | STRING | Foreign key referencing matches.match_id |
| `event_time` | DATETIME | Timestamp when the event occurred |
| `timestamp` | DATETIME | Alternative timestamp for compatibility |
| `event_type` | STRING | Type of combat event (Damage, Healing, Kill, KillingBlow, etc.) |
| `source_entity` | STRING | Entity that caused the event |
| `target_entity` | STRING | Entity that received the action |
| `ability_name` | STRING | Name of the ability or action used |
| `location_x` | FLOAT | X-coordinate of event location |
| `location_y` | FLOAT | Y-coordinate of event location |
| `damage_amount` | INTEGER | Amount of damage dealt (if applicable) |
| `damage_mitigated` | INTEGER | Amount of damage mitigated (if applicable) |
| `event_text` | TEXT | Additional text description of the event |

#### `reward_events` Table

Records experience and gold reward events.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `event_id` | INTEGER | Auto-incrementing primary key |
| `match_id` | STRING | Foreign key referencing matches.match_id |
| `event_time` | DATETIME | Timestamp when the event occurred |
| `timestamp` | DATETIME | Alternative timestamp for compatibility |
| `event_type` | STRING | Type of reward (Gold, Experience, ObjectiveComplete) |
| `entity_name` | STRING | Entity that received the reward |
| `location_x` | FLOAT | X-coordinate of event location |
| `location_y` | FLOAT | Y-coordinate of event location |
| `reward_amount` | INTEGER | Amount of reward received |
| `source_type` | STRING | Source of the reward (Minion, Objective, Structure, etc.) |
| `event_text` | TEXT | Additional text description of the event |

#### `item_events` Table

Tracks item purchases and upgrades.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `event_id` | INTEGER | Auto-incrementing primary key |
| `match_id` | STRING | Foreign key referencing matches.match_id |
| `event_time` | DATETIME | Timestamp when the event occurred |
| `timestamp` | DATETIME | Alternative timestamp for compatibility |
| `event_type` | STRING | Type of item event (ItemPurchase, ItemUpgrade, etc.) |
| `player_name` | STRING | Player who performed the action |
| `item_id` | INTEGER | Numerical identifier for the item |
| `item_name` | STRING | Name of the item |
| `location_x` | FLOAT | X-coordinate of event location |
| `location_y` | FLOAT | Y-coordinate of event location |
| `cost` | INTEGER | Gold cost of the item (if applicable) |
| `event_text` | TEXT | Additional text description of the event |

#### `player_events` Table

Records player-specific events not covered by other tables.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `event_id` | INTEGER | Auto-incrementing primary key |
| `match_id` | STRING | Foreign key referencing matches.match_id |
| `event_time` | DATETIME | Timestamp when the event occurred |
| `timestamp` | DATETIME | Alternative timestamp for compatibility |
| `event_type` | STRING | Type of player event (LevelUp, RoleAssigned, GodPicked, etc.) |
| `player_name` | STRING | Name of the player |
| `entity_name` | STRING | Target entity name (if applicable) |
| `team_id` | INTEGER | Team identifier (1 = Order, 2 = Chaos) |
| `value` | STRING | Value associated with the event |
| `item_id` | INTEGER | Related item ID (if applicable) |
| `item_name` | STRING | Related item name (if applicable) |
| `location_x` | FLOAT | X-coordinate of event location |
| `location_y` | FLOAT | Y-coordinate of event location |
| `event_text` | TEXT | Additional text description of the event |

#### `player_stats` Table

Aggregated statistics for each player in the match.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `stat_id` | INTEGER | Auto-incrementing primary key |
| `match_id` | STRING | Foreign key referencing matches.match_id |
| `player_name` | STRING | Name of the player |
| `team_id` | INTEGER | Team identifier (1 = Order, 2 = Chaos) |
| `kills` | INTEGER | Number of player kills |
| `deaths` | INTEGER | Number of times the player died |
| `assists` | INTEGER | Number of kill assists |
| `damage_dealt` | INTEGER | Total damage dealt to other players |
| `damage_taken` | INTEGER | Total damage received from other players |
| `healing_done` | INTEGER | Total healing performed |
| `damage_mitigated` | INTEGER | Total damage mitigated |
| `gold_earned` | INTEGER | Total gold earned |
| `experience_earned` | INTEGER | Total experience earned |
| `cc_time_inflicted` | INTEGER | Total crowd control time inflicted on enemies |
| `structure_damage` | INTEGER | Total damage dealt to structures |

#### `timeline_events` Table

Enhanced timeline representation with categorized and contextualized events.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `event_id` | INTEGER | Auto-incrementing primary key |
| `match_id` | STRING | Foreign key referencing matches.match_id |
| `event_time` | DATETIME | Timestamp when the event occurred |
| `timestamp` | DATETIME | Alternative timestamp for compatibility |
| `game_time_seconds` | INTEGER | Time in seconds since match start |
| `event_type` | STRING | Specific event type (Kill, TowerDestroyed, ItemPurchase, etc.) |
| `event_category` | STRING | Higher-level category (Combat, Economy, Objective, etc.) |
| `importance` | INTEGER | Significance rating from 1 (minor) to 10 (major) |
| `event_description` | TEXT | Human-readable description of the event |
| `entity_name` | STRING | Primary entity involved in the event |
| `target_name` | STRING | Target entity involved in the event |
| `team_id` | INTEGER | Team associated with the event |
| `location_x` | FLOAT | X-coordinate of event location |
| `location_y` | FLOAT | Y-coordinate of event location |
| `value` | INTEGER | Numerical value associated with the event |
| `related_event_id` | INTEGER | Foreign key to related timeline events |
| `other_entities` | TEXT | JSON list of other entities involved |
| `event_details` | TEXT | JSON data with event-specific details |

### Support Tables

#### `items` Table

Information about items in the game.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `item_id` | INTEGER | Primary key, unique item identifier |
| `item_name` | STRING | Name of the item |
| `item_type` | STRING | Type of item (Item, Relic, Consumable) |

#### `abilities` Table

Information about abilities used in the game.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `ability_id` | INTEGER | Auto-incrementing primary key |
| `match_id` | STRING | Foreign key referencing matches.match_id |
| `ability_name` | STRING | Name of the ability |
| `ability_source` | STRING | Source entity that uses the ability |

## Excel Export Format

The `export_to_excel.py` script creates an Excel file with multiple sheets, each containing different aspects of the match data.

### Exported Sheets

1. **Match Info** - Basic match metadata
   - Contains one row with match details (ID, map, duration, etc.)
   - Key for interpreting timestamps in other sheets

2. **Players** - Information about all players in the match
   - Contains player names, teams, roles, and god selections
   - Foundation for player-based analyses

3. **Timeline Events** - Enhanced timeline of significant events
   - Chronological list of important match events
   - Contains categorized events with importance ratings
   - Includes player kills, objective captures, structure destruction
   - Critical for understanding match flow and key moments

4. **Combat Events (Sample)** - Sample of combat interactions
   - Limited to 10,000 records to prevent Excel file size issues
   - Contains damage, healing, and kill events
   - Essential for detailed combat analysis

5. **Item Events** - All item purchases during the match
   - Complete record of economy events
   - Shows player build progression
   - Important for understanding gold usage and build strategies

6. **Reward Events (Sample)** - Gold and experience rewards
   - Limited to 5,000 records to prevent Excel file size issues
   - Shows how and when players gained resources
   - Valuable for economy analysis

7. **Player Stats** - Aggregated statistics for each player
   - Summary of player performance metrics
   - Includes KDA, damage, healing, gold, and experience
   - Key for quick performance evaluation

## Interpreting the Data

### Match Analysis

The exported data can be used to analyze various aspects of the match:

#### Combat Analysis
- Track damage dealt/received over time
- Identify key engagements and turning points
- Evaluate the effectiveness of different abilities
- Analyze kill participation and damage contribution

#### Economy Analysis
- Track gold and experience distribution
- Analyze item build paths and timing
- Identify power spikes based on item purchases
- Evaluate farming efficiency and objective control

#### Objective Control
- Analyze timing and control of key objectives
- Evaluate structure destruction sequence
- Track team progress through jungle objectives
- Identify critical map control moments

#### Player Performance
- Compare player statistics across multiple dimensions
- Evaluate role performance relative to expectations
- Track individual improvement over multiple matches
- Identify strengths and weaknesses in player behavior

### Timeline Analysis

The timeline_events table is particularly valuable for analysis as it provides a chronological narrative of the match. Events are categorized by importance, allowing for focus on critical moments.

#### Event Types and Categories

**Combat Events:**
- `PlayerKill`: When a player kills another player
- `MultiKill`: Multiple kills in quick succession
- `FirstBlood`: First player kill of the match

**Objective Events:**
- `TowerDestroyed`: Destruction of a tower
- `PhoenixDestroyed`: Destruction of a phoenix
- `TitanKilled`: Final objective that ends the match
- `GoldFuryKilled`: Team secured Gold Fury objective
- `FireGiantKilled`: Team secured Fire Giant objective
- `PyromancerKilled`: Team secured Pyromancer objective
- `BullDemonKilled`: Team secured Bull Demon objective

**Economy Events:**
- `ItemPurchase`: Significant item purchases
- `BuildCompletion`: Player completed core build
- `RelicPurchase`: Acquisition of relics

#### Importance Rating Scale

Timeline events are rated on a scale of 1-10 based on their significance:

- **10**: Match-defining events (Titan kill)
- **9**: Major objective control (Fire Giant, late-game Phoenix)
- **8**: Significant team advantage (deicide, Phoenix destruction)
- **7**: Important kills or objectives (Gold Fury, early Phoenix)
- **6**: Notable events (Tower destruction, core item completion)
- **5**: Standard significant events (regular kills)
- **4**: Minor advantages (buff control, relic usage)
- **3**: Build progression events (regular item purchases)
- **2**: Minor events (assist, minor objective damage)
- **1**: Routine events (minion waves, routine farming)

## Usage Instructions

### Command Line Interface

```bash
python scripts/export_to_excel.py <db_path> [--match MATCH_ID] [--output OUTPUT_FILE]
```

**Arguments:**
- `db_path`: Path to the SQLite database file (required)
- `--match, -m`: Match ID to export (defaults to most recent match)
- `--output, -o`: Output Excel file path (defaults to auto-generated name)

**Examples:**
```bash
# Export most recent match from specified database
python scripts/export_to_excel.py data/CombatLogExample.db

# Export specific match with custom output filename
python scripts/export_to_excel.py data/CombatLogExample.db --match match-CombatLogExample --output my_analysis.xlsx
```

### Programmatic Usage

```python
from scripts.export_to_excel import export_to_excel

# Export most recent match
excel_path = export_to_excel("data/CombatLogExample.db")

# Export specific match with custom output
excel_path = export_to_excel(
    db_path="data/CombatLogExample.db",
    match_id="match-CombatLogExample",
    output_path="custom_export.xlsx"
)
```

## Technical Details and Limitations

### Performance Considerations

- The export process is optimized for typical match sizes but may slow down with extremely large files
- Combat and reward events are limited to prevent Excel file size issues
- For very large matches, consider using targeted SQL queries instead of full export

### Data Limitations

- Timestamps are based on log file entries and may have slight discrepancies
- Some events may be missing if they weren't captured in the original log file
- Spatial coordinates (location_x, location_y) are based on the game's internal coordinate system

### Excel Limitations

- Excel has a row limit of 1,048,576 rows per sheet
- Large matches may hit this limit, especially for combat events
- For comprehensive analysis of large matches, consider using a database tool or specialized analysis software

## Visualization Recommendations

The exported Excel data is well-suited for various visualization approaches:

- **Timeline Visualizations**: Plot important events along a time axis
- **Heatmaps**: Visualize spatial data using the x,y coordinates
- **Network Graphs**: Analyze interactions between players
- **Stacked Area Charts**: Show resource accumulation over time
- **Radar Charts**: Compare player performance across multiple metrics

## Additional Resources

- Use `scripts/integration_test.py` to validate database and export functionality
- Refer to `smite_parser/models.py` for the complete database schema definition
- See `scripts/README.md` for information about other utility scripts

## Data Model Extensions

The current data model can be extended with additional derived tables for specific analyses:

- Player build progression timelines
- Team fight detection and analysis
- Gold and experience differential tracking
- Map control visualization data
- Performance comparison metrics

These extensions can be implemented by creating additional SQL queries against the base tables. 