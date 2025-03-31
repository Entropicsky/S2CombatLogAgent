"""
Implementation of the DataAnalystGuardrail.

This module provides a guardrail for validating Data Analyst agent outputs,
focusing on statistical claim accuracy and analytical interpretation correctness.
"""

import re
import logging
import statistics
from typing import Dict, List, Any, Optional, Union, Set, Tuple
from pydantic import BaseModel, Field

from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    output_guardrail
)

from smite2_agent.guardrails.base import DataFidelityGuardrail, ValidationResult

# Set up logging
logger = logging.getLogger(__name__)


class DataAnalystOutput(BaseModel):
    """Expected output structure from a Data Analyst agent."""
    response: str
    key_findings: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of key findings from the analysis")
    patterns: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of patterns found in the data")
    comparisons: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of comparisons between data points")
    statistical_claims: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of statistical claims made in the analysis")
    raw_data_references: Optional[Dict[str, Any]] = Field(default=None, description="References to raw data used in analysis")

    class Config:
        """Pydantic model configuration."""
        extra = "forbid"  # Forbid extra attributes


class DataAnalystGuardrail(DataFidelityGuardrail):
    """
    Guardrail for validating Data Analyst agent outputs.
    
    This guardrail focuses on:
    1. Statistical claim accuracy
    2. Pattern and trend validity
    3. Comparison correctness
    4. Insight validity against raw data
    """
    
    def __init__(
        self,
        statistical_tolerance: float = 0.05,
        trend_significance_threshold: float = 0.10,
        **kwargs
    ):
        """
        Initialize a new DataAnalystGuardrail.
        
        Args:
            statistical_tolerance: Tolerance for statistical claims (default: 0.05 or 5%)
            trend_significance_threshold: Threshold for trend significance (default: 0.10 or 10%)
            **kwargs: Additional arguments to pass to the parent class
        """
        # Call the parent constructor with a default name and description
        super().__init__(
            name="DataAnalystGuardrail",
            description="Validates analytical claims and statistical interpretations",
            tolerance=statistical_tolerance,  # Use the statistical_tolerance as the base tolerance
            **kwargs
        )
        
        self.trend_significance_threshold = trend_significance_threshold
        
        # Patterns for extracting specific types of claims
        self.claim_patterns = {
            "increase": [
                r"increased by (\d+(?:\.\d+)?)%",
                r"(\d+(?:\.\d+)?)% increase",
                r"grew by (\d+(?:\.\d+)?)%"
            ],
            "decrease": [
                r"decreased by (\d+(?:\.\d+)?)%",
                r"(\d+(?:\.\d+)?)% decrease",
                r"fell by (\d+(?:\.\d+)?)%"
            ],
            "comparison": [
                r"(\d+(?:\.\d+)?)% (higher|more than|greater than)",
                r"(\d+(?:\.\d+)?)% (lower|less than)"
            ],
            "average": [
                r"average of (\d{1,3}(?:,\d{3})*|\d+(?:\.\d+)?)",
                r"(\d{1,3}(?:,\d{3})*|\d+(?:\.\d+)?) on average"
            ],
            "total": [
                r"total of (\d{1,3}(?:,\d{3})*|\d+(?:\.\d+)?)",
                r"(\d{1,3}(?:,\d{3})*|\d+(?:\.\d+)?) in total"
            ],
            "max": [
                r"maximum of (\d{1,3}(?:,\d{3})*|\d+(?:\.\d+)?)",
                r"highest at (\d{1,3}(?:,\d{3})*|\d+(?:\.\d+)?)"
            ],
            "min": [
                r"minimum of (\d{1,3}(?:,\d{3})*|\d+(?:\.\d+)?)",
                r"lowest at (\d{1,3}(?:,\d{3})*|\d+(?:\.\d+)?)"
            ]
        }
        
        logger.info(f"Initialized {self.name} with tolerance {self.tolerance}")
    
    def validate_statistical_claim(
        self,
        claim: str,
        claim_type: str,
        raw_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate a specific statistical claim against raw data.
        
        Args:
            claim: The claim text to validate
            claim_type: Type of claim (e.g., "increase", "average", "comparison")
            raw_data: The raw data to validate against
            context: Optional additional context
            
        Returns:
            ValidationResult with any discrepancies found
        """
        discrepancies = []
        
        # Skip validation if no raw data
        if not raw_data:
            return ValidationResult(
                discrepancies=["No raw data provided for validation"],
                context={"claim": claim, "claim_type": claim_type},
                tripwire_triggered=False  # Don't trigger for missing data
            )
        
        # Extract the claimed value
        claimed_value = None
        for pattern in self.claim_patterns.get(claim_type, []):
            match = re.search(pattern, claim, re.IGNORECASE)
            if match:
                claimed_value = float(match.group(1).replace(",", ""))
                break
        
        # Skip if we couldn't extract a value
        if claimed_value is None:
            return ValidationResult(
                discrepancies=[f"Could not extract numeric value from claim: '{claim}'"],
                context={"claim": claim, "claim_type": claim_type},
                tripwire_triggered=False  # Don't trigger if we can't extract a value
            )
        
        # Validate based on claim type
        if claim_type == "average":
            if "values" in raw_data:
                values = raw_data["values"]
                if values and all(isinstance(v, (int, float)) for v in values):
                    actual_average = sum(values) / len(values)
                    if abs(claimed_value - actual_average) / actual_average > self.tolerance:
                        discrepancies.append(
                            f"Average claim '{claimed_value}' does not match actual average '{actual_average}'"
                        )
        
        elif claim_type == "total":
            if "values" in raw_data:
                values = raw_data["values"]
                if values and all(isinstance(v, (int, float)) for v in values):
                    actual_total = sum(values)
                    if abs(claimed_value - actual_total) / actual_total > self.tolerance:
                        discrepancies.append(
                            f"Total claim '{claimed_value}' does not match actual total '{actual_total}'"
                        )
        
        elif claim_type == "max":
            if "values" in raw_data:
                values = raw_data["values"]
                if values and all(isinstance(v, (int, float)) for v in values):
                    actual_max = max(values)
                    if abs(claimed_value - actual_max) / actual_max > self.tolerance:
                        discrepancies.append(
                            f"Maximum claim '{claimed_value}' does not match actual maximum '{actual_max}'"
                        )
        
        elif claim_type == "min":
            if "values" in raw_data:
                values = raw_data["values"]
                if values and all(isinstance(v, (int, float)) for v in values):
                    actual_min = min(values)
                    if abs(claimed_value - actual_min) / actual_min > self.tolerance:
                        discrepancies.append(
                            f"Minimum claim '{claimed_value}' does not match actual minimum '{actual_min}'"
                        )
        
        elif claim_type in ["increase", "decrease"]:
            if "before" in raw_data and "after" in raw_data:
                before = raw_data["before"]
                after = raw_data["after"]
                
                if isinstance(before, (int, float)) and isinstance(after, (int, float)) and before != 0:
                    if claim_type == "increase":
                        actual_percentage = ((after - before) / before) * 100
                    else:  # decrease
                        actual_percentage = ((before - after) / before) * 100
                        
                    if abs(claimed_value - actual_percentage) > self.tolerance * 100:  # Allow larger tolerance for percentages
                        discrepancies.append(
                            f"{claim_type.capitalize()} claim '{claimed_value}%' does not match "
                            f"actual {claim_type} '{actual_percentage:.2f}%'"
                        )
        
        elif claim_type == "comparison":
            if "first" in raw_data and "second" in raw_data:
                first = raw_data["first"]
                second = raw_data["second"]
                
                if isinstance(first, (int, float)) and isinstance(second, (int, float)) and second != 0:
                    # Check if it's a "higher than" or "lower than" comparison
                    if any(term in claim.lower() for term in ["higher", "more than", "greater than"]):
                        actual_percentage = ((first - second) / second) * 100
                    else:  # lower than
                        actual_percentage = ((second - first) / second) * 100
                        
                    if abs(claimed_value - actual_percentage) > self.tolerance * 100:  # Allow larger tolerance for percentages
                        discrepancies.append(
                            f"Comparison claim '{claimed_value}%' does not match "
                            f"actual difference '{actual_percentage:.2f}%'"
                        )
        
        return ValidationResult(
            discrepancies=discrepancies,
            context={
                "claim": claim,
                "claim_type": claim_type,
                "claimed_value": claimed_value
            },
            tripwire_triggered=len(discrepancies) > 0
        )
    
    def validate_trend_claim(
        self, 
        claim: str, 
        time_series_data: List[float]
    ) -> ValidationResult:
        """
        Validate a trend claim against time series data.
        
        Args:
            claim: The trend claim to validate
            time_series_data: List of values representing a time series
            
        Returns:
            ValidationResult with any discrepancies found
        """
        discrepancies = []
        
        # Skip validation if insufficient data
        if not time_series_data or len(time_series_data) < 3:
            return ValidationResult(
                discrepancies=["Insufficient time series data for trend validation"],
                context={"claim": claim},
                tripwire_triggered=False  # Don't trigger for insufficient data
            )
        
        # Extract trend type from claim
        trend_type = None
        if re.search(r'\b(increas|rising|upward|grow|climb)\w*\b', claim, re.IGNORECASE):
            trend_type = "increasing"
        elif re.search(r'\b(decreas|falling|downward|declin|drop)\w*\b', claim, re.IGNORECASE):
            trend_type = "decreasing"
        elif re.search(r'\b(stable|steady|constant|flat|consistent)\w*\b', claim, re.IGNORECASE):
            trend_type = "stable"
        elif re.search(r'\b(fluctuat|vari|inconsistent|volatile)\w*\b', claim, re.IGNORECASE):
            trend_type = "fluctuating"
        
        # Skip validation if we couldn't determine trend type
        if trend_type is None:
            return ValidationResult(
                discrepancies=["Could not determine trend type from claim"],
                context={"claim": claim},
                tripwire_triggered=False  # Don't trigger if we can't determine trend type
            )
        
        # Calculate actual trend
        actual_trend = None
        if len(time_series_data) >= 2:
            # Simple linear regression
            n = len(time_series_data)
            x = list(range(n))
            
            # Calculate slope
            x_mean = sum(x) / n
            y_mean = sum(time_series_data) / n
            
            numerator = sum((x[i] - x_mean) * (time_series_data[i] - y_mean) for i in range(n))
            denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
            
            if denominator != 0:
                slope = numerator / denominator
                
                # Calculate correlation coefficient for significance
                std_x = (sum((i - x_mean) ** 2 for i in range(n)) / n) ** 0.5
                std_y = (sum((y - y_mean) ** 2 for y in time_series_data) / n) ** 0.5
                
                if std_x != 0 and std_y != 0:
                    correlation = numerator / (n * std_x * std_y)
                    
                    # Determine actual trend based on slope and significance
                    if abs(correlation) < self.trend_significance_threshold:
                        actual_trend = "stable"  # Not significant enough to claim trend
                    elif slope > 0:
                        actual_trend = "increasing"
                    elif slope < 0:
                        actual_trend = "decreasing"
                    else:
                        actual_trend = "stable"
                else:
                    actual_trend = "stable"  # No variation
            else:
                actual_trend = "stable"  # All x values are the same
            
            # Check for fluctuation (high standard deviation relative to mean)
            if actual_trend:
                mean = sum(time_series_data) / len(time_series_data)
                if mean != 0:
                    # Calculate coefficient of variation
                    std_dev = (sum((x - mean) ** 2 for x in time_series_data) / len(time_series_data)) ** 0.5
                    cv = std_dev / abs(mean)
                    
                    # If high relative variation, it's fluctuating regardless of slope
                    if cv > 0.25:  # Threshold for considering something "fluctuating"
                        actual_trend = "fluctuating"
        
        # Compare claimed trend with actual trend
        if actual_trend and trend_type != actual_trend:
            discrepancies.append(
                f"Trend claim '{trend_type}' does not match actual trend '{actual_trend}'"
            )
        
        return ValidationResult(
            discrepancies=discrepancies,
            context={
                "claim": claim,
                "claimed_trend": trend_type,
                "actual_trend": actual_trend
            },
            tripwire_triggered=len(discrepancies) > 0
        )
    
    def validate_key_findings(
        self,
        key_findings: List[Dict[str, Any]],
        raw_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate key findings against raw data.
        
        Args:
            key_findings: List of key findings to validate
            raw_data: Raw data to validate against
            
        Returns:
            ValidationResult with any discrepancies found
        """
        all_results = []
        
        for finding in key_findings:
            finding_text = finding.get("description", "")
            
            # Check for entity references
            entities_result = self.validate_entity_existence(
                response=finding_text,
                known_entities=raw_data.get("entities", {}),
                entity_type="player"
            )
            all_results.append(entities_result)
            
            # Check for fabricated entities
            fabrication_result = self.validate_no_fabricated_entities(
                response=finding_text,
                known_entities=raw_data.get("entities", {}),
                entity_type="player"
            )
            all_results.append(fabrication_result)
            
            # Check numerical values
            numerical_result = self.validate_numerical_values(
                response=finding_text,
                known_values=raw_data.get("values", []),
                value_type="database"
            )
            all_results.append(numerical_result)
            
            # Check statistical claims
            stats_result = self.validate_statistical_claims(
                response=finding_text,
                known_stats=raw_data.get("statistics", {}),
                strict_mode=self.strict_mode
            )
            all_results.append(stats_result)
        
        # Combine all validation results
        return self.combine_validation_results(all_results)
    
    def validate_analytical_response(
        self,
        response: str,
        raw_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate an analytical response against raw data.
        
        Args:
            response: The response to validate
            raw_data: Raw data to validate against
            
        Returns:
            ValidationResult with any discrepancies found
        """
        all_results = []
        
        # Check for entity references
        entities_result = self.validate_entity_existence(
            response=response,
            known_entities=raw_data.get("entities", {}),
            entity_type="player"
        )
        all_results.append(entities_result)
        
        # Check for fabricated entities
        fabrication_result = self.validate_no_fabricated_entities(
            response=response,
            known_entities=raw_data.get("entities", {}),
            entity_type="player"
        )
        all_results.append(fabrication_result)
        
        # Check numerical values
        numerical_result = self.validate_numerical_values(
            response=response,
            known_values=raw_data.get("values", []),
            value_type="database"
        )
        all_results.append(numerical_result)
        
        # Check statistical claims
        stats_result = self.validate_statistical_claims(
            response=response,
            known_stats=raw_data.get("statistics", {}),
            strict_mode=self.strict_mode
        )
        all_results.append(stats_result)
        
        # Extract and validate specific statistical claims
        for claim_type, patterns in self.claim_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, response, re.IGNORECASE)
                for match in matches:
                    claim = match.group(0)
                    relevant_data = {}
                    
                    # Find relevant data for this type of claim
                    if claim_type in ["average", "total", "max", "min"]:
                        relevant_data = {"values": raw_data.get("values", [])}
                    elif claim_type in ["increase", "decrease"]:
                        # Look for before/after in raw data
                        if "before_after" in raw_data:
                            for pair in raw_data["before_after"]:
                                if pair.get("description", "").lower() in claim.lower():
                                    relevant_data = {
                                        "before": pair.get("before"),
                                        "after": pair.get("after")
                                    }
                                    break
                    elif claim_type == "comparison":
                        # Look for comparisons in raw data
                        if "comparisons" in raw_data:
                            for comp in raw_data["comparisons"]:
                                if comp.get("description", "").lower() in claim.lower():
                                    relevant_data = {
                                        "first": comp.get("first"),
                                        "second": comp.get("second")
                                    }
                                    break
                    
                    # Validate the claim if we have relevant data
                    if relevant_data:
                        claim_result = self.validate_statistical_claim(
                            claim=claim,
                            claim_type=claim_type,
                            raw_data=relevant_data
                        )
                        all_results.append(claim_result)
        
        # Validate trend claims
        trend_claim_pattern = r'([\w\s]+)\s+(?:is|are|was|were)\s+(increasing|decreasing|rising|falling|growing|declining|stable|constant|fluctuating|varying)'
        matches = re.finditer(trend_claim_pattern, response, re.IGNORECASE)
        for match in matches:
            entity = match.group(1).strip()
            claim = match.group(0)
            
            # Find time series data for this entity
            time_series_data = []
            if "time_series" in raw_data:
                for series in raw_data["time_series"]:
                    if series.get("entity", "").lower() == entity.lower():
                        time_series_data = series.get("values", [])
                        break
            
            # Validate the trend claim if we have data
            if time_series_data:
                trend_result = self.validate_trend_claim(
                    claim=claim,
                    time_series_data=time_series_data
                )
                all_results.append(trend_result)
        
        # Combine all validation results
        return self.combine_validation_results(all_results)
    
    @output_guardrail
    async def validate(
        self,
        ctx: RunContextWrapper,
        agent: Agent,
        output: DataAnalystOutput
    ) -> GuardrailFunctionOutput:
        """
        Validate the Data Analyst agent's output.
        
        Args:
            ctx: The run context
            agent: The agent that generated the output
            output: The output to validate
            
        Returns:
            GuardrailFunctionOutput with validation results
        """
        logger.info(f"Validating Data Analyst output")
        
        validation_results = []
        
        # Get raw data for validation from the context
        raw_data = {}
        
        # Try to get raw data from data package if available
        try:
            raw_data["entities"] = ctx.context["data"]["raw_data"]["entity"] if "raw_data" in ctx.context["data"] else {}
            raw_data["values"] = []
            
            # Extract numerical values from query results
            if "query_results" in ctx.context["data"]:
                for query_id, result in ctx.context["data"]["query_results"].items():
                    if "data" in result and isinstance(result["data"], list):
                        for row in result["data"]:
                            for key, value in row.items():
                                if isinstance(value, (int, float)) and value > 0:
                                    raw_data["values"].append(value)
            
            # Use raw data references if provided in output
            if output.raw_data_references:
                # Merge with existing raw data
                raw_data.update(output.raw_data_references)
        except (KeyError, TypeError, AttributeError) as e:
            logger.warning(f"Error extracting raw data from context: {str(e)}")
        
        # Validate the response text
        response_validation = self.validate_analytical_response(
            response=output.response,
            raw_data=raw_data
        )
        validation_results.append(response_validation)
        
        # Validate key findings if provided
        if output.key_findings:
            findings_validation = self.validate_key_findings(
                key_findings=output.key_findings,
                raw_data=raw_data
            )
            validation_results.append(findings_validation)
        
        # Combine all validation results
        combined_validation = self.combine_validation_results(validation_results)
        
        logger.info(
            f"Validation completed with {len(combined_validation.discrepancies)} discrepancies. "
            f"Tripwire triggered: {combined_validation.tripwire_triggered}"
        )
        
        # Return the guardrail output
        return self.create_guardrail_output(combined_validation) 