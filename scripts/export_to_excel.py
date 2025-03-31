#!/usr/bin/env python3
"""
SMITE 2 Combat Log Database Export Script
Exports the SMITE 2 Combat Log database to Excel format for visualization
"""

import argparse
import logging
import os
import sqlite3
import sys
from datetime import datetime

import pandas as pd

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('export_to_excel')

def export_to_excel(db_path, match_id=None, output_path=None):
    """
    Export data from SMITE 2 Combat Log database to Excel.
    
    Args:
        db_path (str): Path to the SQLite database
        match_id (int, optional): Specific match ID to export. If None, exports the most recent match.
        output_path (str, optional): Path for the output Excel file. If None, generates a default name.
        
    Returns:
        str: Path to the created Excel file
    """
    logger.info(f"Starting export from database: {db_path}")
    
    # Validate database file exists
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        raise FileNotFoundError(f"Database file not found: {db_path}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # If no match_id specified, get the most recent match
        if match_id is None:
            cursor.execute("""
                SELECT match_id FROM matches 
                ORDER BY start_time DESC 
                LIMIT 1
            """)
            result = cursor.fetchone()
            if result:
                match_id = result[0]
                logger.info(f"No match ID specified, using most recent match: {match_id}")
            else:
                logger.error("No matches found in the database")
                raise ValueError("No matches found in the database")
        
        # Check if match exists
        cursor.execute("SELECT COUNT(*) FROM matches WHERE match_id = ?", (match_id,))
        if cursor.fetchone()[0] == 0:
            logger.error(f"Match ID {match_id} not found in database")
            raise ValueError(f"Match ID {match_id} not found in database")
        
        # Get match details
        cursor.execute("""
            SELECT match_id, source_file, map_name, game_type, start_time, end_time, duration_seconds
            FROM matches 
            WHERE match_id = ?
        """, (match_id,))
        match_info = cursor.fetchone()
        
        logger.info(f"Exporting match: {match_id}")
        
        # Create a Pandas Excel writer
        if output_path is None:
            output_path = f"match_{match_id}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
        
        # Export match info to a DataFrame
        match_df = pd.DataFrame([match_info], columns=[
            'match_id', 'source_file', 'map_name', 'game_type', 'start_time', 'end_time', 'duration_seconds'
        ])
        match_df.to_excel(writer, sheet_name='Match Info', index=False)
        
        # Export players
        players_query = """
            SELECT player_id, player_name, team_id, god_name, role
            FROM players 
            WHERE match_id = ?
        """
        players_df = pd.read_sql(players_query, conn, params=(match_id,))
        players_df.to_excel(writer, sheet_name='Players', index=False)
        
        # Export timeline events
        timeline_query = """
            SELECT 
                event_id, event_time, game_time_seconds, event_type, event_category,
                importance, entity_name, target_name, team_id,
                location_x, location_y, value, event_description
            FROM timeline_events
            WHERE match_id = ?
            ORDER BY event_time ASC
        """
        timeline_df = pd.read_sql(timeline_query, conn, params=(match_id,))
        timeline_df.to_excel(writer, sheet_name='Timeline Events', index=False)
        
        # Export combat events
        combat_query = """
            SELECT 
                event_id, event_time, event_type,
                source_entity, target_entity,
                ability_name, damage_amount, damage_mitigated,
                location_x, location_y
            FROM combat_events
            WHERE match_id = ?
            ORDER BY event_time ASC
            LIMIT 10000  -- Limit to prevent Excel file size issues
        """
        combat_df = pd.read_sql(combat_query, conn, params=(match_id,))
        combat_df.to_excel(writer, sheet_name='Combat Events (Sample)', index=False)
        
        # Export item events
        item_query = """
            SELECT 
                event_id, event_time, event_type,
                player_name, item_name, cost,
                location_x, location_y
            FROM item_events
            WHERE match_id = ?
            ORDER BY event_time ASC
        """
        item_df = pd.read_sql(item_query, conn, params=(match_id,))
        item_df.to_excel(writer, sheet_name='Item Events', index=False)
        
        # Export reward events
        reward_query = """
            SELECT 
                event_id, event_time, event_type,
                entity_name, reward_amount, source_type,
                location_x, location_y
            FROM reward_events
            WHERE match_id = ?
            ORDER BY event_time ASC
            LIMIT 5000  -- Limit to prevent Excel file size issues
        """
        reward_df = pd.read_sql(reward_query, conn, params=(match_id,))
        reward_df.to_excel(writer, sheet_name='Reward Events (Sample)', index=False)
        
        # Export player stats
        player_stats_query = """
            SELECT 
                stat_id, player_name, team_id, 
                kills, deaths, assists,
                damage_dealt, damage_taken, healing_done, damage_mitigated,
                gold_earned, experience_earned
            FROM player_stats
            WHERE match_id = ?
            ORDER BY team_id, player_name
        """
        player_stats_df = pd.read_sql(player_stats_query, conn, params=(match_id,))
        player_stats_df.to_excel(writer, sheet_name='Player Stats', index=False)
        
        # Close the Excel writer
        writer.close()
        logger.info(f"Export completed successfully: {output_path}")
        
        return output_path
    
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Export SMITE 2 Combat Log database to Excel format'
    )
    parser.add_argument('db_path',
                        help='Path to the SQLite database file')
    parser.add_argument('--match', '-m',
                        help='Match ID to export (defaults to most recent)')
    parser.add_argument('--output', '-o',
                        help='Output Excel file path')
    
    args = parser.parse_args()
    
    try:
        output_file = export_to_excel(args.db_path, args.match, args.output)
        print(f"Export successful: {output_file}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 