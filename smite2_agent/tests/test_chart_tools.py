"""
Tests for chart generation tools.
Verifies charts can be created from data from the real CombatLogExample.db.
"""

import unittest
import os
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Any, List

from smite2_agent.tests.fixtures import get_test_db_path
from smite2_agent.tools.chart_tools import generate_chart, ChartGenerationError
from smite2_agent.db.connection import get_connection


class TestChartTools(unittest.TestCase):
    """Test case for chart generation tools."""
    
    def setUp(self):
        """Set up test data from the real database."""
        self.db_path = get_test_db_path()
        db_conn = get_connection(self.db_path)
        
        # Get player damage data from the real database
        self.player_damage_data = db_conn.execute_query("""
            SELECT 
                p.player_name, 
                COUNT(c.event_id) as damage_events, 
                SUM(c.damage_amount) as total_damage
            FROM players p
            JOIN combat_events c ON p.player_id = c.source_entity 
            WHERE c.damage_amount IS NOT NULL AND c.damage_amount > 0
            GROUP BY p.player_id
            ORDER BY total_damage DESC
            LIMIT 5
        """)
        
        # Get time series damage data from the real database
        self.time_series_data = db_conn.execute_query("""
            SELECT 
                CAST(strftime('%M', timestamp) AS INTEGER) as minute,
                SUM(damage_amount) as damage_in_minute
            FROM combat_events
            WHERE damage_amount IS NOT NULL AND damage_amount > 0
            GROUP BY minute
            ORDER BY minute
            LIMIT 10
        """)
        
        # Get player stats for multi-column chart
        self.player_stats = db_conn.execute_query("""
            SELECT 
                p.player_name,
                COUNT(CASE WHEN c.event_type = 'PlayerKill' THEN 1 END) as kills,
                SUM(CASE WHEN c.damage_amount > 0 THEN c.damage_amount ELSE 0 END) as damage
            FROM players p
            LEFT JOIN combat_events c ON p.player_id = c.source_entity
            GROUP BY p.player_id
            ORDER BY kills DESC
            LIMIT 5
        """)
        
        # Make sure we have data for testing
        # If database doesn't have the right data, create fallback test data
        if not self.player_damage_data:
            self.player_damage_data = [
                {"player_name": "Player1", "damage_events": 15, "total_damage": 3500},
                {"player_name": "Player2", "damage_events": 10, "total_damage": 2800},
                {"player_name": "Player3", "damage_events": 20, "total_damage": 4200},
                {"player_name": "Player4", "damage_events": 12, "total_damage": 3100}
            ]
            
        if not self.time_series_data:
            self.time_series_data = [
                {"minute": 1, "damage_in_minute": 500},
                {"minute": 2, "damage_in_minute": 800},
                {"minute": 3, "damage_in_minute": 1200},
                {"minute": 4, "damage_in_minute": 950},
                {"minute": 5, "damage_in_minute": 1500}
            ]
            
        if not self.player_stats or all(player["kills"] == 0 for player in self.player_stats):
            self.player_stats = [
                {"player_name": "Player1", "kills": 5, "damage": 1200},
                {"player_name": "Player2", "kills": 3, "damage": 800},
                {"player_name": "Player3", "kills": 7, "damage": 1500},
                {"player_name": "Player4", "kills": 4, "damage": 950}
            ]
    
    def test_generate_bar_chart(self):
        """Test bar chart generation with real data."""
        result = generate_chart(
            data=self.player_damage_data,
            chart_type='bar',
            x_column='player_name',
            y_columns='total_damage',
            title='Total Damage by Player'
        )
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["chart_path"])
        self.assertTrue(os.path.exists(result["chart_path"]))
        
        # Clean up
        if os.path.exists(result["chart_path"]):
            os.remove(result["chart_path"])
    
    def test_generate_line_chart(self):
        """Test line chart generation with real time series data."""
        result = generate_chart(
            data=self.time_series_data,
            chart_type='line',
            x_column='minute',
            y_columns='damage_in_minute',
            title='Damage Over Time'
        )
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["chart_path"])
        self.assertTrue(os.path.exists(result["chart_path"]))
        
        # Clean up
        if os.path.exists(result["chart_path"]):
            os.remove(result["chart_path"])
    
    def test_generate_chart_with_dataframe(self):
        """Test chart generation with pandas DataFrame from real data."""
        # Convert list of dicts to DataFrame
        df = pd.DataFrame(self.player_damage_data)
        
        result = generate_chart(
            data=df,
            chart_type='bar',
            x_column='player_name',
            y_columns='total_damage',
            title='Damage by Player (DataFrame)'
        )
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["chart_path"])
        self.assertTrue(os.path.exists(result["chart_path"]))
        
        # Clean up
        if os.path.exists(result["chart_path"]):
            os.remove(result["chart_path"])
    
    def test_generate_multi_series_chart(self):
        """Test chart with multiple y columns using real data."""
        # Convert to DataFrame to ensure consistent handling
        df = pd.DataFrame(self.player_stats)
        
        result = generate_chart(
            data=df,
            chart_type='bar',
            x_column='player_name',
            y_columns=['damage', 'kills'],
            title='Damage and Kills by Player'
        )
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["chart_path"])
        self.assertTrue(os.path.exists(result["chart_path"]))
        
        # Clean up
        if os.path.exists(result["chart_path"]):
            os.remove(result["chart_path"])
    
    def test_generate_pie_chart(self):
        """Test pie chart generation with real data."""
        result = generate_chart(
            data=self.player_damage_data,
            chart_type='pie',
            x_column='player_name',
            y_columns='total_damage',
            title='Damage Distribution'
        )
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["chart_path"])
        self.assertTrue(os.path.exists(result["chart_path"]))
        
        # Clean up
        if os.path.exists(result["chart_path"]):
            os.remove(result["chart_path"])
    
    def test_invalid_chart_type(self):
        """Test with invalid chart type."""
        result = generate_chart(
            data=self.player_damage_data,
            chart_type='invalid_type',
            x_column='player_name',
            y_columns='total_damage'
        )
        
        self.assertFalse(result["success"])
        self.assertIn("Unsupported chart type", result["error"])
    
    def test_missing_required_columns(self):
        """Test with missing required columns."""
        result = generate_chart(
            data=self.player_damage_data,
            chart_type='bar',
            x_column='non_existent_column',
            y_columns='total_damage'
        )
        
        self.assertFalse(result["success"])
        self.assertIn("non_existent_column", result["error"])
        
        result = generate_chart(
            data=self.player_damage_data,
            chart_type='bar',
            x_column='player_name',
            y_columns='non_existent_column'
        )
        
        self.assertFalse(result["success"])
        self.assertIn("non_existent_column", result["error"])


if __name__ == "__main__":
    unittest.main() 