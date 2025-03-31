"""
Test suite for data fidelity guardrails.

This module tests the DataFidelityGuardrail base class and subclasses
to ensure they correctly validate outputs and prevent hallucinations.
"""

import os
import unittest
import asyncio
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch

from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    output_guardrail
)

from smite2_agent.guardrails.base import DataFidelityGuardrail, ValidationResult
from smite2_agent.guardrails.data_engineer import DataEngineerGuardrail, DataEngineerOutput
from smite2_agent.guardrails.data_analyst import DataAnalystGuardrail, DataAnalystOutput
from smite2_agent.pipeline.base.data_package import DataPackage


class TestDataFidelityGuardrail(unittest.TestCase):
    """Test case for the DataFidelityGuardrail base class."""
    
    class TestGuardrail(DataFidelityGuardrail):
        """Test implementation of the DataFidelityGuardrail."""
        
        @output_guardrail
        async def validate(self, ctx: RunContextWrapper, agent: Agent, output: Any) -> GuardrailFunctionOutput:
            """Test implementation of validate method."""
            # Simply validate that no fabricated entities are present
            validation = self.validate_no_fabricated_entities(
                response=output.response,
                known_entities={"player": {"MateoUwU": 114622}},
                entity_type="player"
            )
            return self.create_guardrail_output(validation)
    
    def setUp(self):
        """Set up test fixtures."""
        self.guardrail = self.TestGuardrail(
            name="TestGuardrail",
            description="Test guardrail for unit tests",
            tolerance=0.05,
            strict_mode=False
        )
    
    def test_init(self):
        """Test initialization of DataFidelityGuardrail."""
        self.assertEqual(self.guardrail.name, "TestGuardrail")
        self.assertEqual(self.guardrail.description, "Test guardrail for unit tests")
        self.assertEqual(self.guardrail.tolerance, 0.05)
        self.assertFalse(self.guardrail.strict_mode)
        self.assertIn("player", self.guardrail.known_fabricated_entities)
        self.assertIn("ability", self.guardrail.known_fabricated_entities)
        self.assertIn("damage", self.guardrail.patterns)
    
    def test_validate_entity_existence(self):
        """Test validation of entity existence."""
        # Test with entity present
        result = self.guardrail.validate_entity_existence(
            response="MateoUwU was the top damage dealer",
            known_entities={"MateoUwU": 114622},
            entity_type="player"
        )
        self.assertFalse(result.tripwire_triggered)
        self.assertEqual(len(result.discrepancies), 0)
        
        # Test with entity missing
        result = self.guardrail.validate_entity_existence(
            response="Someone else was the top damage dealer",
            known_entities={"MateoUwU": 114622},
            entity_type="player"
        )
        self.assertTrue(result.tripwire_triggered)
        self.assertEqual(len(result.discrepancies), 1)
    
    def test_validate_no_fabricated_entities(self):
        """Test validation of fabricated entities."""
        # Test with no fabricated entities
        result = self.guardrail.validate_no_fabricated_entities(
            response="MateoUwU was the top damage dealer",
            known_entities={"MateoUwU": 114622},
            entity_type="player"
        )
        self.assertFalse(result.tripwire_triggered)
        self.assertEqual(len(result.discrepancies), 0)
        
        # Test with fabricated entity
        result = self.guardrail.validate_no_fabricated_entities(
            response="Zephyr was the top damage dealer",
            known_entities={"MateoUwU": 114622},
            entity_type="player"
        )
        self.assertTrue(result.tripwire_triggered)
        self.assertEqual(len(result.discrepancies), 1)
    
    def test_validate_numerical_values(self):
        """Test validation of numerical values."""
        # Test with correct value
        result = self.guardrail.validate_numerical_values(
            response="MateoUwU dealt 114,622 damage",
            known_values=[114622],
            value_type="damage"
        )
        self.assertFalse(result.tripwire_triggered)
        self.assertEqual(len(result.discrepancies), 0)
        
        # Test with fabricated value
        result = self.guardrail.validate_numerical_values(
            response="MateoUwU dealt 35,000 damage",
            known_values=[114622],
            value_type="damage"
        )
        self.assertTrue(result.tripwire_triggered)
        self.assertEqual(len(result.discrepancies), 1)
    
    def test_combine_validation_results(self):
        """Test combining validation results."""
        results = [
            ValidationResult(
                discrepancies=["Error 1"],
                context={"test": "value1"},
                tripwire_triggered=True
            ),
            ValidationResult(
                discrepancies=["Error 2", "Error 3"],
                context={"test": "value2"},
                tripwire_triggered=False
            )
        ]
        
        combined = self.guardrail.combine_validation_results(results)
        self.assertEqual(len(combined.discrepancies), 3)
        self.assertTrue(combined.tripwire_triggered)


class TestDataEngineerGuardrail(unittest.TestCase):
    """Test case for the DataEngineerGuardrail."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.guardrail = DataEngineerGuardrail(
            tolerance=0.05,
            strict_mode=False
        )
    
    def test_validate_sql_query_valid(self):
        """Test validation of valid SQL queries."""
        valid_queries = [
            "SELECT * FROM players",
            "SELECT player_name, SUM(damage_amount) FROM combat_events GROUP BY player_name",
            "WITH damage_stats AS (SELECT source_entity, SUM(damage_amount) as total_damage FROM combat_events GROUP BY source_entity) SELECT * FROM damage_stats",
            "SELECT p.player_name, c.damage_amount FROM players p JOIN combat_events c ON p.player_name = c.source_entity"
        ]
        
        for query in valid_queries:
            result = self.guardrail.validate_sql_query(query)
            self.assertFalse(result.tripwire_triggered, f"Query should be valid: {query}")
            self.assertEqual(len(result.discrepancies), 0, f"Query should have no discrepancies: {query}")
    
    def test_validate_sql_query_invalid(self):
        """Test validation of invalid SQL queries."""
        invalid_queries = [
            "DELETE FROM players",
            "DROP TABLE players",
            "INSERT INTO players VALUES (1, 'test')",
            "UPDATE players SET player_name = 'test'",
            "ALTER TABLE players ADD COLUMN test TEXT",
            "CREATE DATABASE test",
            "PRAGMA table_info(players)",
            "SELECT * FROM non_existent_table"
        ]
        
        for query in invalid_queries:
            result = self.guardrail.validate_sql_query(query)
            self.assertTrue(result.tripwire_triggered, f"Query should be invalid: {query}")
            self.assertGreater(len(result.discrepancies), 0, f"Query should have discrepancies: {query}")
    
    def test_extract_table_references(self):
        """Test extracting table references from SQL queries."""
        query = "SELECT * FROM players JOIN combat_events ON players.player_id = combat_events.source_entity"
        tables = self.guardrail._extract_table_references(query)
        self.assertIn("players", tables)
        self.assertIn("combat_events", tables)
    
    def test_extract_column_references(self):
        """Test extracting column references from SQL queries."""
        query = "SELECT player_name, team_id FROM players WHERE role = 'Carry'"
        columns = self.guardrail._extract_column_references(query)
        
        # Extract column names for easier testing
        column_names = [col for col, _ in columns]
        
        self.assertIn("player_name", column_names)
        self.assertIn("team_id", column_names)
        self.assertIn("role", column_names)
    
    def test_validate_query_result(self):
        """Test validation of query results."""
        # Test with matching data
        response = "MateoUwU dealt 114622 damage"
        query_result = {
            "success": True,
            "data": [
                {"player": "MateoUwU", "damage": 114622}
            ]
        }
        
        result = self.guardrail.validate_query_result(response, query_result)
        self.assertFalse(result.tripwire_triggered)
        
        # Test with mismatched data
        response = "Zephyr dealt 35000 damage"
        result = self.guardrail.validate_query_result(response, query_result)
        self.assertTrue(result.tripwire_triggered)
    
    @patch('agents.output_guardrail')
    async def test_validate(self, mock_output_guardrail):
        """Test the validate method."""
        # Create mock context and agent
        ctx = Mock(spec=RunContextWrapper)
        agent = Mock(spec=Agent)
        
        # Create output with valid SQL
        output = DataEngineerOutput(
            response="MateoUwU dealt 114622 damage",
            sql_query="SELECT * FROM players",
            query_result={
                "success": True,
                "data": [
                    {"player": "MateoUwU", "damage": 114622}
                ]
            }
        )
        
        # Call validate method
        result = await self.guardrail.validate(ctx, agent, output)
        
        # Check that the guardrail output was created
        self.assertIsInstance(result, GuardrailFunctionOutput)


class TestDataPackageGuardrailIntegration(unittest.TestCase):
    """Test case for integration between DataPackage and guardrails."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.package = DataPackage(query="Who dealt the most damage?")
        self.guardrail = DataEngineerGuardrail()
    
    def test_add_raw_data_for_validation(self):
        """Test adding raw data for validation."""
        # Add sample data
        self.package.add_raw_data_for_validation(
            key="players",
            data={"MateoUwU": 114622},
            category="entity"
        )
        
        # Verify it was added correctly
        result = self.package.get_raw_data_for_validation(
            key="players",
            category="entity"
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result["MateoUwU"], 114622)
    
    def test_add_validation_result(self):
        """Test adding validation results."""
        # Add a successful validation
        self.package.add_validation_result(
            stage="data_engineer",
            guardrail_name="DataEngineerGuardrail",
            success=True,
            discrepancies=[]
        )
        
        # Verify validation status
        self.assertTrue(self.package.is_validated())
        self.assertEqual(len(self.package.get_validation_errors()), 0)
        
        # Add a failed validation
        self.package.add_validation_result(
            stage="data_engineer",
            guardrail_name="DataEngineerGuardrail",
            success=False,
            discrepancies=["Made-up player name 'Zephyr' found in response"]
        )
        
        # Verify validation status
        self.assertFalse(self.package.is_validated())
        self.assertEqual(len(self.package.get_validation_errors()), 1)


class TestDataAnalystGuardrail(unittest.TestCase):
    """Test case for the DataAnalystGuardrail."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.guardrail = DataAnalystGuardrail(
            statistical_tolerance=0.05,
            trend_significance_threshold=0.10,
            strict_mode=False
        )
    
    def test_validate_statistical_claim(self):
        """Test validation of statistical claims."""
        # Test with correct average value
        result = self.guardrail.validate_statistical_claim(
            claim="The average damage was 100",
            claim_type="average",
            raw_data={"values": [95, 100, 105]}
        )
        self.assertFalse(result.tripwire_triggered)
        
        # Test with incorrect average value
        result = self.guardrail.validate_statistical_claim(
            claim="The average damage was 150",
            claim_type="average",
            raw_data={"values": [95, 100, 105]}
        )
        self.assertTrue(result.tripwire_triggered)
        
        # Test with correct percentage increase
        result = self.guardrail.validate_statistical_claim(
            claim="Damage increased by 50%",
            claim_type="increase",
            raw_data={"before": 100, "after": 150}
        )
        self.assertFalse(result.tripwire_triggered)
        
        # Test with incorrect percentage increase
        result = self.guardrail.validate_statistical_claim(
            claim="Damage increased by 20%",
            claim_type="increase",
            raw_data={"before": 100, "after": 150}
        )
        self.assertTrue(result.tripwire_triggered)
    
    def test_validate_trend_claim(self):
        """Test validation of trend claims."""
        # Test with correct increasing trend
        result = self.guardrail.validate_trend_claim(
            claim="Damage is increasing over time",
            time_series_data=[100, 120, 140, 160, 180]
        )
        self.assertFalse(result.tripwire_triggered)
        
        # Test with incorrect trend (claiming increasing when decreasing)
        result = self.guardrail.validate_trend_claim(
            claim="Damage is increasing over time",
            time_series_data=[180, 160, 140, 120, 100]
        )
        self.assertTrue(result.tripwire_triggered)
        
        # Test with fluctuating data
        result = self.guardrail.validate_trend_claim(
            claim="Damage is fluctuating over time",
            time_series_data=[100, 180, 120, 200, 110]
        )
        self.assertFalse(result.tripwire_triggered)
    
    def test_validate_analytical_response(self):
        """Test validation of analytical responses."""
        # Test with correct response
        response = """
        Player MateoUwU dealt an average of 114622 damage.
        The damage increased by 50% from the previous match.
        The highest damage value was 150000.
        """
        
        raw_data = {
            "entities": {"MateoUwU": "player_id_123"},
            "values": [114622, 110000, 150000],
            "before_after": [
                {"description": "damage", "before": 100000, "after": 150000}
            ]
        }
        
        result = self.guardrail.validate_analytical_response(
            response=response,
            raw_data=raw_data
        )
        self.assertFalse(result.tripwire_triggered)
        
        # Test with fabricated entity
        response = """
        Player Zephyr dealt an average of 114622 damage.
        """
        
        result = self.guardrail.validate_analytical_response(
            response=response,
            raw_data=raw_data
        )
        self.assertTrue(result.tripwire_triggered)
        
        # Test with incorrect average
        response = """
        Player MateoUwU dealt an average of 200000 damage.
        """
        
        result = self.guardrail.validate_analytical_response(
            response=response,
            raw_data=raw_data
        )
        self.assertTrue(result.tripwire_triggered)
    
    @patch('agents.output_guardrail')
    async def test_validate(self, mock_output_guardrail):
        """Test the validate method."""
        # Create mock context and agent
        ctx = Mock(spec=RunContextWrapper)
        ctx.context = {
            "data": {
                "raw_data": {
                    "entity": {"MateoUwU": "player_id_123"}
                },
                "query_results": {
                    "query1": {
                        "data": [
                            {"player": "MateoUwU", "damage": 114622}
                        ]
                    }
                }
            }
        }
        
        agent = Mock(spec=Agent)
        
        # Create output with valid analysis
        output = DataAnalystOutput(
            response="MateoUwU dealt an average of 114622 damage.",
            key_findings=[
                {"description": "MateoUwU was the top damage dealer with 114622 damage"}
            ]
        )
        
        # Call validate method
        result = await self.guardrail.validate(ctx, agent, output)
        
        # Check that the guardrail output was created
        self.assertIsInstance(result, GuardrailFunctionOutput)


if __name__ == "__main__":
    unittest.main() 