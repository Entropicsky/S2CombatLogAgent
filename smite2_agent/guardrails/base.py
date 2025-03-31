"""
Base implementation of data fidelity guardrails.

This module provides the foundation for all data fidelity guardrails,
with common validation functions and utilities for detecting hallucinated content.
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Pattern, Set, Tuple
from pydantic import BaseModel

from agents import (
    Agent,
    GuardrailFunctionOutput,
    OutputGuardrailTripwireTriggered,
    RunContextWrapper,
    output_guardrail,
)

# Set up logging
logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    """Result of a validation check with discrepancies and context."""
    discrepancies: List[str] = []
    context: Dict[str, Any] = {}
    tripwire_triggered: bool = False


class DataFidelityGuardrail(ABC):
    """
    Base class for all data fidelity guardrails.
    
    This class provides common functionality for validating agent outputs
    against actual data from the database, to prevent hallucinations.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        tolerance: float = 0.05,
        known_fabricated_entities: Optional[Dict[str, List[str]]] = None,
        strict_mode: bool = False
    ):
        """
        Initialize a new data fidelity guardrail.
        
        Args:
            name: Guardrail name for logging and identification
            description: Description of what this guardrail validates
            tolerance: Numerical tolerance for value comparisons (default: 0.05 or 5%)
            known_fabricated_entities: Dictionary of known fabricated entities by type
            strict_mode: If True, applies stricter validation rules
        """
        self.name = name
        self.description = description
        self.tolerance = tolerance
        self.strict_mode = strict_mode
        
        # Default fabricated entities if none provided
        self.known_fabricated_entities = known_fabricated_entities or {
            "player": ["Zephyr", "Ares", "Apollo", "Zeus", "Athena"],
            "ability": ["Wind Blast", "Arcane Surge", "Tornado", "Lightning Strike"],
            "item": ["Mystic Blade", "Eternal Shield", "Void Staff", "Celestial Armor"]
        }
        
        # Common regex patterns for extracting values
        self.patterns = {
            "damage": [
                r"Total Damage:?\s+(\d{1,3}(?:,\d{3})*|\d+)",
                r"(\d{1,3}(?:,\d{3})*|\d+)\s+damage",
                r"damage of\s+(\d{1,3}(?:,\d{3})*|\d+)",
                r"dealt\s+(\d{1,3}(?:,\d{3})*|\d+)"
            ],
            "percentage": [
                r"(\d{1,3}(?:\.\d+)?)%",
                r"(\d{1,3}(?:\.\d+)?)\s+percent"
            ],
            "player_reference": [
                r"\b([A-Z][a-z]+|[a-zA-Z0-9_]+)\b\s+(?:dealt|player|was|did|had)"
            ]
        }
        
        logger.info(f"Initialized {self.name} guardrail")
    
    def validate_entity_existence(
        self,
        response: str,
        known_entities: Dict[str, Any],
        entity_type: str,
        min_required: int = 1
    ) -> ValidationResult:
        """
        Validate that entities from the database are mentioned in the response.
        
        Args:
            response: The agent's response text
            known_entities: Dictionary of known entities from the database
            entity_type: Type of entity being validated (e.g., "player", "ability")
            min_required: Minimum number of known entities that must be present
            
        Returns:
            ValidationResult with any discrepancies found
        """
        discrepancies = []
        found_entities = 0
        
        # Create a list of keys from known_entities
        known_entity_names = list(known_entities.keys())
        
        # Check for each known entity
        for entity_name in known_entity_names:
            # Skip empty entity names
            if not entity_name:
                continue
                
            # Use word boundary for more accurate matching
            entity_pattern = fr'\b{re.escape(entity_name)}\b'
            if re.search(entity_pattern, response, re.IGNORECASE):
                found_entities += 1
        
        # If not enough known entities were found
        if found_entities < min_required:
            discrepancies.append(
                f"Found only {found_entities} {entity_type}(s) from the database "
                f"in the response, but at least {min_required} is required."
            )
        
        return ValidationResult(
            discrepancies=discrepancies,
            context={
                "entity_type": entity_type,
                "found_entities": found_entities,
                "required_entities": min_required
            },
            tripwire_triggered=len(discrepancies) > 0
        )
    
    def validate_no_fabricated_entities(
        self,
        response: str,
        known_entities: Dict[str, Any],
        entity_type: str
    ) -> ValidationResult:
        """
        Validate that no fabricated entities are mentioned in the response.
        
        Args:
            response: The agent's response text
            known_entities: Dictionary of known entities from the database
            entity_type: Type of entity being validated (e.g., "player", "ability")
            
        Returns:
            ValidationResult with any discrepancies found
        """
        discrepancies = []
        fabricated_entities = []
        
        # Get known fabricated entities for this type
        known_fabricated = self.known_fabricated_entities.get(entity_type, [])
        
        # Known entity names converted to lowercase for case-insensitive comparison
        known_entity_names_lower = {name.lower() for name in known_entities.keys() if name}
        
        # Check for known fabricated entities
        for fabricated in known_fabricated:
            # Skip empty fabricated entity names
            if not fabricated:
                continue
                
            entity_pattern = fr'\b{re.escape(fabricated)}\b'
            if re.search(entity_pattern, response, re.IGNORECASE):
                # Verify it's not actually a known entity
                if fabricated.lower() not in known_entity_names_lower:
                    fabricated_entities.append(fabricated)
                    discrepancies.append(
                        f"Made-up {entity_type} '{fabricated}' found in response"
                    )
        
        # Use pattern matching to detect potential fabricated entities we didn't specify
        if entity_type == "player":
            # Extract potential player names using regex patterns
            for pattern in self.patterns.get("player_reference", []):
                matches = re.finditer(pattern, response)
                for match in matches:
                    potential_entity = match.group(1)
                    # Skip if it's empty or too short to be a name
                    if not potential_entity or len(potential_entity) < 3:
                        continue
                    
                    # Check if this is a potential fabricated entity
                    if (
                        potential_entity.lower() not in known_entity_names_lower
                        and potential_entity not in fabricated_entities  # Avoid duplicates
                        and not any(potential_entity.lower() == fab.lower() for fab in fabricated_entities)
                    ):
                        # In strict mode, any unknown entity is flagged
                        if self.strict_mode:
                            fabricated_entities.append(potential_entity)
                            discrepancies.append(
                                f"Potentially fabricated {entity_type} '{potential_entity}' "
                                f"found in response"
                            )
        
        return ValidationResult(
            discrepancies=discrepancies,
            context={
                "entity_type": entity_type,
                "fabricated_entities": fabricated_entities
            },
            tripwire_triggered=len(discrepancies) > 0
        )
    
    def validate_numerical_values(
        self,
        response: str,
        known_values: List[int],
        value_type: str,
        patterns: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Validate that numerical values in the response match known values.
        
        Args:
            response: The agent's response text
            known_values: List of known numerical values from the database
            value_type: Type of value being validated (e.g., "damage", "healing")
            patterns: Optional override of regex patterns to use
            
        Returns:
            ValidationResult with any discrepancies found
        """
        discrepancies = []
        fabricated_values = []
        
        # Use provided patterns or default ones for the value type
        if patterns is None:
            patterns = self.patterns.get(value_type, [r"(\d{1,3}(?:,\d{3})*|\d+)"])
        
        # Find all numerical values in the response that match the patterns
        for pattern in patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                # Extract the value and remove commas
                value_str = match.group(1).replace(",", "")
                try:
                    extracted_value = int(value_str)
                    
                    # Check if this value is close to any known value
                    is_valid = False
                    for known_value in known_values:
                        # Allow for some tolerance in the values
                        if known_value > 0 and abs(extracted_value - known_value) / known_value <= self.tolerance:
                            is_valid = True
                            break
                    
                    # If not valid, this is a fabricated value
                    if not is_valid:
                        # Apply more tolerance for rounded values
                        # Check if this might be a rounded value (e.g., 35,000 for 34,567)
                        is_rounded = False
                        for known_value in known_values:
                            if known_value > 1000:
                                # Check rounding to nearest 1000
                                rounded_value = round(known_value, -3)
                                if abs(extracted_value - rounded_value) < 1000:
                                    is_rounded = True
                                    break
                                
                                # Check rounding to nearest 100
                                rounded_value = round(known_value, -2)
                                if abs(extracted_value - rounded_value) < 100:
                                    is_rounded = True
                                    break
                        
                        if not is_rounded:
                            fabricated_values.append(extracted_value)
                            discrepancies.append(
                                f"Made-up {value_type} value '{extracted_value}' found in response"
                            )
                except ValueError:
                    # Not a valid number, skip it
                    pass
        
        return ValidationResult(
            discrepancies=discrepancies,
            context={
                "value_type": value_type,
                "fabricated_values": fabricated_values
            },
            tripwire_triggered=len(discrepancies) > 0
        )
    
    def validate_statistical_claims(
        self,
        response: str,
        known_stats: Dict[str, float],
        strict_mode: Optional[bool] = None
    ) -> ValidationResult:
        """
        Validate statistical claims in the response.
        
        Args:
            response: The agent's response text
            known_stats: Dictionary of known statistics from the database
            strict_mode: Optional override of strict mode setting
            
        Returns:
            ValidationResult with any discrepancies found
        """
        discrepancies = []
        use_strict = self.strict_mode if strict_mode is None else strict_mode
        
        # Extract percentage claims
        percentage_patterns = [
            r"increased by (\d+(?:\.\d+)?)%",
            r"decreased by (\d+(?:\.\d+)?)%",
            r"(\d+(?:\.\d+)?)% (higher|lower|more|less)"
        ]
        
        for pattern in percentage_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                # In strict mode, flag all statistical claims that can't be verified
                if use_strict:
                    context = response[max(0, match.start() - 50):min(len(response), match.end() + 50)]
                    discrepancies.append(
                        f"Unverifiable statistical claim found: '{match.group(0)}' in context '{context}'"
                    )
        
        return ValidationResult(
            discrepancies=discrepancies,
            context={
                "strict_mode": use_strict,
            },
            tripwire_triggered=len(discrepancies) > 0
        )
    
    def combine_validation_results(self, results: List[ValidationResult]) -> ValidationResult:
        """
        Combine multiple validation results into a single result.
        
        Args:
            results: List of ValidationResult objects
            
        Returns:
            Combined ValidationResult
        """
        all_discrepancies = []
        combined_context = {}
        triggered = False
        
        for result in results:
            all_discrepancies.extend(result.discrepancies)
            combined_context.update(result.context)
            triggered = triggered or result.tripwire_triggered
        
        return ValidationResult(
            discrepancies=all_discrepancies,
            context=combined_context,
            tripwire_triggered=triggered
        )
    
    @abstractmethod
    async def validate(self, ctx: RunContextWrapper, agent: Agent, output: Any) -> GuardrailFunctionOutput:
        """
        Abstract method to validate agent output.
        Must be implemented by subclasses.
        """
        pass
    
    def create_guardrail_output(self, validation_result: ValidationResult) -> GuardrailFunctionOutput:
        """
        Create a GuardrailFunctionOutput from a ValidationResult.
        
        Args:
            validation_result: The validation result
            
        Returns:
            A GuardrailFunctionOutput object
        """
        return GuardrailFunctionOutput(
            output_info={"discrepancies": validation_result.discrepancies, **validation_result.context},
            tripwire_triggered=validation_result.tripwire_triggered
        )
    
    def get_name(self) -> str:
        """
        Get the name of the guardrail.
        
        Required by OpenAI's Agents SDK for guardrail integration.
        
        Returns:
            The name of the guardrail
        """
        return self.name
    
    async def run(self, agent: 'Agent', agent_output: Any, context: Any) -> GuardrailFunctionOutput:
        """
        Run the guardrail validation.
        
        This is a wrapper around the validate method to make it compatible with
        OpenAI's Agents SDK guardrail interface.
        
        Args:
            agent: The agent that produced the output
            agent_output: The output to validate
            context: The context for validation
            
        Returns:
            A GuardrailFunctionOutput object with validation results
        """
        # Create a mock context wrapper if needed
        ctx = context
        if not isinstance(context, RunContextWrapper):
            class MockContextWrapper:
                def __init__(self, context_data):
                    self.context = context_data
            ctx = MockContextWrapper(context)
        
        # Run the actual validation
        return await self.validate(ctx, agent, agent_output) 