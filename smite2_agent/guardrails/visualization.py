"""
Implementation of the VisualizationGuardrail.

This module provides a guardrail for validating Visualization Specialist agent outputs,
focusing on chart accuracy and ensuring visualizations properly represent the underlying data.
"""

import re
import logging
import json
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


class ChartData(BaseModel):
    """Structured representation of chart data."""
    data: List[Dict[str, Any]] = Field(default_factory=list, description="Data points for the chart")
    x_values: Optional[List[Any]] = Field(default=None, description="X-axis values")
    y_values: Optional[List[Any]] = Field(default=None, description="Y-axis values")
    categories: Optional[List[str]] = Field(default=None, description="Categories for categorical charts")
    series: Optional[Dict[str, List[Any]]] = Field(default=None, description="Series data for multi-series charts")


class ChartMetadata(BaseModel):
    """Metadata for a chart visualization."""
    title: str = Field(description="Chart title")
    x_label: Optional[str] = Field(default=None, description="X-axis label")
    y_label: Optional[str] = Field(default=None, description="Y-axis label")
    chart_type: str = Field(description="Type of chart (e.g., bar, line, pie)")
    data_source: Optional[str] = Field(default=None, description="Data source identifier")
    entity_references: Optional[List[str]] = Field(default=None, description="Entities referenced in the chart")


class VisualizationOutput(BaseModel):
    """Expected output structure from a Visualization Specialist agent."""
    response: str
    charts: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of charts produced")
    chart_data: Optional[Dict[str, ChartData]] = Field(default=None, description="Data used for charts")
    chart_metadata: Optional[Dict[str, ChartMetadata]] = Field(default=None, description="Metadata for charts")
    chart_descriptions: Optional[List[str]] = Field(default=None, description="Textual descriptions of charts")
    raw_data_references: Optional[Dict[str, Any]] = Field(default=None, description="References to raw data used in visualizations")

    class Config:
        """Pydantic model configuration."""
        extra = "allow"  # Allow extra attributes


class VisualizationGuardrail(DataFidelityGuardrail):
    """
    Guardrail for validating Visualization Specialist agent outputs.
    
    This guardrail focuses on:
    1. Chart data accuracy
    2. Visualization-to-data fidelity
    3. Entity reference validation in visualizations
    4. Appropriate chart type selection
    """
    
    def __init__(
        self,
        data_tolerance: float = 0.05,
        strict_mode: bool = False,
        **kwargs
    ):
        """
        Initialize a new VisualizationGuardrail.
        
        Args:
            data_tolerance: Tolerance for numerical data in visualizations (default: 0.05 or 5%)
            strict_mode: If True, applies stricter validation rules (default: False)
            **kwargs: Additional arguments to pass to the parent class
        """
        # Call the parent constructor with a default name and description
        super().__init__(
            name="VisualizationGuardrail",
            description="Validates chart accuracy and visualization fidelity",
            tolerance=data_tolerance,
            strict_mode=strict_mode,
            **kwargs
        )
        
        # Chart type appropriateness mappings
        self.appropriate_chart_types = {
            "categorical": ["bar", "column", "pie", "donut", "radar"],
            "time_series": ["line", "area", "bar", "column", "scatter"],
            "comparison": ["bar", "column", "radar", "pie", "donut"],
            "distribution": ["histogram", "box", "violin", "scatter"],
            "correlation": ["scatter", "heatmap", "bubble"],
            "part_to_whole": ["pie", "donut", "stacked_bar", "stacked_column", "treemap"],
            "ranking": ["bar", "column", "lollipop"],
            "geospatial": ["map", "choropleth", "bubble_map"]
        }
        
        # Common data types and appropriate chart types
        self.data_type_chart_mapping = {
            "numerical_vs_numerical": ["scatter", "line", "bubble"],
            "numerical_vs_categorical": ["bar", "column", "box", "violin"],
            "categorical_vs_categorical": ["heatmap", "mosaic", "grouped_bar"],
            "numerical_distribution": ["histogram", "density", "box", "violin"],
            "categorical_distribution": ["bar", "pie", "donut"],
            "time_vs_numerical": ["line", "area", "bar", "column"],
            "time_vs_categorical": ["heatmap", "stacked_bar", "stacked_area"]
        }
        
        logger.info(f"Initialized {self.name} with tolerance {self.tolerance}")
    
    def validate_chart_data_accuracy(
        self,
        chart_data: ChartData,
        original_data: List[Dict[str, Any]],
        chart_type: str
    ) -> ValidationResult:
        """
        Validate that chart data accurately represents the original data.
        
        Args:
            chart_data: The structured chart data
            original_data: The original data that the chart is based on
            chart_type: The type of chart
            
        Returns:
            ValidationResult with any discrepancies found
        """
        discrepancies = []
        
        # Skip validation if no original data
        if not original_data:
            return ValidationResult(
                discrepancies=["No original data provided for validation"],
                context={"chart_type": chart_type},
                tripwire_triggered=False  # Don't trigger for missing data
            )
        
        # Check if the chart data contains the correct number of data points
        if len(chart_data.data) != len(original_data):
            discrepancies.append(
                f"Chart contains {len(chart_data.data)} data points, but original data has {len(original_data)} points"
            )
        
        # For pie/donut charts, check that percentages sum to approximately 100%
        if chart_type in ["pie", "donut"] and chart_data.y_values:
            total = sum(chart_data.y_values)
            if abs(total - 100) > 1.0:  # Allow for minor rounding errors
                discrepancies.append(
                    f"Pie/donut chart percentages sum to {total}, not 100%"
                )
        
        # For bar/column/line charts, check each value against original data
        if chart_type in ["bar", "column", "line", "scatter"] and chart_data.x_values and chart_data.y_values:
            # Create a lookup from the original data
            original_lookup = {}
            x_field = None
            y_field = None
            
            # Try to detect the x and y fields from the data
            if len(original_data) > 0 and len(original_data[0]) >= 2:
                # Simple heuristic: first field is x, second is y
                fields = list(original_data[0].keys())
                x_field = fields[0]
                y_field = fields[1]
                
                # But if we can find number-like values, prefer those for y
                for field in fields:
                    if any(isinstance(row.get(field), (int, float)) for row in original_data):
                        if y_field != field:  # Already found a numeric field
                            x_field = field  # The non-numeric field is likely x
                            y_field = next(f for f in fields if f != field)
                            break
            
            # Build lookup table if we identified fields
            if x_field and y_field:
                for row in original_data:
                    x_val = row.get(x_field)
                    y_val = row.get(y_field)
                    if x_val is not None:
                        original_lookup[str(x_val)] = y_val
                
                # Check each chart value against the original data
                for i, x_val in enumerate(chart_data.x_values):
                    x_str = str(x_val)
                    if x_str in original_lookup:
                        original_y = original_lookup[x_str]
                        chart_y = chart_data.y_values[i]
                        
                        # Check for numerical accuracy, allowing for tolerance
                        if (isinstance(original_y, (int, float)) and 
                            isinstance(chart_y, (int, float)) and 
                            original_y != 0):
                            
                            rel_diff = abs(chart_y - original_y) / abs(original_y)
                            if rel_diff > self.tolerance:
                                discrepancies.append(
                                    f"Chart value {chart_y} for {x_val} differs from original value {original_y} by {rel_diff:.2%}"
                                )
        
        return ValidationResult(
            discrepancies=discrepancies,
            context={
                "chart_type": chart_type,
                "original_data_size": len(original_data),
                "chart_data_size": len(chart_data.data)
            },
            tripwire_triggered=len(discrepancies) > 0
        )
    
    def validate_chart_type_appropriateness(
        self,
        chart_type: str,
        data_characteristics: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate that the chart type is appropriate for the data characteristics.
        
        Args:
            chart_type: The type of chart
            data_characteristics: Characteristics of the data being visualized
            
        Returns:
            ValidationResult with any discrepancies found
        """
        discrepancies = []
        
        # Default values if not provided
        data_purpose = data_characteristics.get("purpose", "comparison")
        data_structure = data_characteristics.get("structure", "categorical_vs_numerical")
        data_size = data_characteristics.get("size", 0)
        
        # Check if chart type is appropriate for the data purpose
        if data_purpose in self.appropriate_chart_types:
            appropriate_types = self.appropriate_chart_types[data_purpose]
            if chart_type not in appropriate_types:
                discrepancies.append(
                    f"Chart type '{chart_type}' may not be appropriate for {data_purpose} data. "
                    f"Consider using one of: {', '.join(appropriate_types)}"
                )
        
        # Check if chart type is appropriate for the data structure
        if data_structure in self.data_type_chart_mapping:
            appropriate_types = self.data_type_chart_mapping[data_structure]
            if chart_type not in appropriate_types:
                discrepancies.append(
                    f"Chart type '{chart_type}' may not be appropriate for {data_structure} data. "
                    f"Consider using one of: {', '.join(appropriate_types)}"
                )
        
        # Check if chart type is appropriate for the data size
        if chart_type == "pie" and data_size > 7:
            discrepancies.append(
                f"Pie chart is not recommended for more than 7 categories (found {data_size})"
            )
        
        # Warn about 3D charts (generally discouraged for accuracy)
        if "3d" in chart_type.lower():
            discrepancies.append(
                "3D charts can distort data perception and are generally not recommended"
            )
        
        return ValidationResult(
            discrepancies=discrepancies,
            context={
                "chart_type": chart_type,
                "data_purpose": data_purpose,
                "data_structure": data_structure,
                "data_size": data_size
            },
            tripwire_triggered=False  # Only warn about chart type issues, don't trigger guardrail
        )
    
    def validate_chart_entity_references(
        self,
        chart_metadata: ChartMetadata,
        chart_description: str,
        known_entities: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate entity references in chart titles, labels, and descriptions.
        
        Args:
            chart_metadata: Metadata for the chart
            chart_description: Textual description of the chart
            known_entities: Dictionary of known entities from the database
            
        Returns:
            ValidationResult with any discrepancies found
        """
        # Combine all text for entity validation
        combined_text = f"{chart_metadata.title} "
        if chart_metadata.x_label:
            combined_text += f"{chart_metadata.x_label} "
        if chart_metadata.y_label:
            combined_text += f"{chart_metadata.y_label} "
        combined_text += chart_description
        
        # Validate entity existence
        entity_result = self.validate_entity_existence(
            response=combined_text,
            known_entities=known_entities,
            entity_type="player"
        )
        
        # Validate no fabricated entities
        fabrication_result = self.validate_no_fabricated_entities(
            response=combined_text,
            known_entities=known_entities,
            entity_type="player"
        )
        
        # Combine the results
        return self.combine_validation_results([entity_result, fabrication_result])
    
    def validate_chart_labels(
        self,
        chart_metadata: ChartMetadata,
        data_fields: List[str]
    ) -> ValidationResult:
        """
        Validate that chart labels accurately reflect the data fields.
        
        Args:
            chart_metadata: Metadata for the chart
            data_fields: List of field names in the data
            
        Returns:
            ValidationResult with any discrepancies found
        """
        discrepancies = []
        
        # Check if the chart has appropriate axis labels
        if chart_metadata.chart_type in ["bar", "column", "line", "scatter", "area"]:
            if not chart_metadata.x_label:
                discrepancies.append(f"Chart is missing x-axis label")
            if not chart_metadata.y_label:
                discrepancies.append(f"Chart is missing y-axis label")
        
        # Check if the chart has a title
        if not chart_metadata.title:
            discrepancies.append("Chart is missing a title")
        
        # Check if the labels match data fields (simple substring check)
        # This is a best-effort approach since labels often use friendly names
        # rather than exact field names
        has_x_match = False
        has_y_match = False
        
        if chart_metadata.x_label:
            x_label_lower = chart_metadata.x_label.lower()
            for field in data_fields:
                field_lower = field.lower()
                # Check if field name appears in label or vice versa
                if field_lower in x_label_lower or x_label_lower in field_lower:
                    has_x_match = True
                    break
        
        if chart_metadata.y_label:
            y_label_lower = chart_metadata.y_label.lower()
            for field in data_fields:
                field_lower = field.lower()
                # Check if field name appears in label or vice versa
                if field_lower in y_label_lower or y_label_lower in field_lower:
                    has_y_match = True
                    break
        
        # Warn if labels don't seem to match fields
        if chart_metadata.x_label and data_fields and not has_x_match:
            discrepancies.append(
                f"X-axis label '{chart_metadata.x_label}' doesn't seem to match any data fields: {', '.join(data_fields)}"
            )
        
        if chart_metadata.y_label and data_fields and not has_y_match:
            discrepancies.append(
                f"Y-axis label '{chart_metadata.y_label}' doesn't seem to match any data fields: {', '.join(data_fields)}"
            )
        
        return ValidationResult(
            discrepancies=discrepancies,
            context={
                "chart_title": chart_metadata.title,
                "x_label": chart_metadata.x_label,
                "y_label": chart_metadata.y_label,
                "data_fields": data_fields
            },
            tripwire_triggered=len(discrepancies) > 0
        )
    
    def validate_visualization_response(
        self,
        response: str,
        raw_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate a visualization response against raw data.
        
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
        
        # Combine all validation results
        return self.combine_validation_results(all_results)
    
    def validate_chart(
        self,
        chart_data: ChartData,
        chart_metadata: ChartMetadata,
        chart_description: str,
        original_data: List[Dict[str, Any]],
        known_entities: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate a single chart for accuracy and appropriateness.
        
        Args:
            chart_data: Structured chart data
            chart_metadata: Chart metadata
            chart_description: Textual description of the chart
            original_data: Original data the chart is based on
            known_entities: Dictionary of known entities
            
        Returns:
            ValidationResult with any discrepancies found
        """
        all_results = []
        
        # Validate chart data accuracy
        accuracy_result = self.validate_chart_data_accuracy(
            chart_data=chart_data,
            original_data=original_data,
            chart_type=chart_metadata.chart_type
        )
        all_results.append(accuracy_result)
        
        # Validate chart type appropriateness
        data_size = len(original_data)
        has_time_field = any(
            "time" in field.lower() or "date" in field.lower() or "timestamp" in field.lower()
            for field in original_data[0].keys()
        ) if original_data else False
        
        has_numeric_fields = any(
            isinstance(list(row.values())[i], (int, float))
            for row in original_data
            for i in range(min(3, len(row)))  # Check first few values
        ) if original_data else False
        
        # Determine data structure
        data_structure = "categorical_vs_numerical"
        if has_time_field and has_numeric_fields:
            data_structure = "time_vs_numerical"
        elif has_time_field:
            data_structure = "time_vs_categorical"
        
        # Determine data purpose (default to comparison)
        data_purpose = "comparison"
        if has_time_field:
            data_purpose = "time_series"
        elif "pie" in chart_metadata.chart_type.lower() or "donut" in chart_metadata.chart_type.lower():
            data_purpose = "part_to_whole"
        
        # Check appropriateness
        appropriateness_result = self.validate_chart_type_appropriateness(
            chart_type=chart_metadata.chart_type,
            data_characteristics={
                "purpose": data_purpose,
                "structure": data_structure,
                "size": data_size
            }
        )
        all_results.append(appropriateness_result)
        
        # Validate entity references in chart
        entity_result = self.validate_chart_entity_references(
            chart_metadata=chart_metadata,
            chart_description=chart_description,
            known_entities=known_entities
        )
        all_results.append(entity_result)
        
        # Validate chart labels
        data_fields = list(original_data[0].keys()) if original_data else []
        label_result = self.validate_chart_labels(
            chart_metadata=chart_metadata,
            data_fields=data_fields
        )
        all_results.append(label_result)
        
        # Combine all validation results
        return self.combine_validation_results(all_results)
    
    @output_guardrail
    async def validate(
        self,
        ctx: RunContextWrapper,
        agent: Agent,
        output: VisualizationOutput
    ) -> GuardrailFunctionOutput:
        """
        Validate the Visualization Specialist agent's output.
        
        Args:
            ctx: The run context
            agent: The agent that generated the output
            output: The output to validate
            
        Returns:
            GuardrailFunctionOutput with validation results
        """
        logger.info(f"Validating Visualization Specialist output")
        
        validation_results = []
        
        # Get raw data for validation from the context
        raw_data = {}
        
        # Try to get raw data from data package if available
        try:
            # Extract entity information
            raw_data["entities"] = ctx.context["data"]["raw_data"]["entity"] if "raw_data" in ctx.context["data"] else {}
            raw_data["values"] = []
            
            # Extract numerical values from query results
            if "query_results" in ctx.context["data"]:
                for query_id, result in ctx.context["data"]["query_results"].items():
                    if "data" in result and isinstance(result["data"], list):
                        raw_data[query_id] = result["data"]
                        
                        # Extract values for numerical validation
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
        response_validation = self.validate_visualization_response(
            response=output.response,
            raw_data=raw_data
        )
        validation_results.append(response_validation)
        
        # Validate each chart if available
        if output.charts and output.chart_data and output.chart_metadata and output.chart_descriptions:
            for chart_id, chart in enumerate(output.charts):
                chart_id_str = str(chart_id)
                
                # Check if we have all needed components
                if (chart_id_str in output.chart_data and 
                    chart_id_str in output.chart_metadata and 
                    chart_id < len(output.chart_descriptions)):
                    
                    chart_data = output.chart_data[chart_id_str]
                    chart_metadata = output.chart_metadata[chart_id_str]
                    chart_description = output.chart_descriptions[chart_id]
                    
                    # Find source data for this chart
                    source_data = []
                    source_name = chart_metadata.data_source
                    if source_name and source_name in raw_data:
                        source_data = raw_data[source_name]
                    else:
                        # If no specific source, try using the first available dataset
                        for source, data in raw_data.items():
                            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                                source_data = data
                                break
                    
                    # Validate the chart
                    chart_validation = self.validate_chart(
                        chart_data=chart_data,
                        chart_metadata=chart_metadata,
                        chart_description=chart_description,
                        original_data=source_data,
                        known_entities=raw_data.get("entities", {})
                    )
                    validation_results.append(chart_validation)
        
        # Combine all validation results
        combined_validation = self.combine_validation_results(validation_results)
        
        logger.info(
            f"Validation completed with {len(combined_validation.discrepancies)} discrepancies. "
            f"Tripwire triggered: {combined_validation.tripwire_triggered}"
        )
        
        # Return the guardrail output
        return self.create_guardrail_output(combined_validation) 