"""
Export Formatters for Document Extraction Data.

Provides JSON and CSV formatting for extracted document data,
supporting the /export endpoint.

Source: Design Document 07-document-extraction-system-design.md Section 4.4
Verified: 2025-12-20
"""

import csv
import io
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Iterator, Optional
from uuid import UUID


class ExportFormat(str, Enum):
    """Supported export formats."""

    JSON = "json"
    CSV = "csv"


@dataclass
class ExportOptions:
    """Export configuration options."""

    format: ExportFormat = ExportFormat.JSON
    include_confidence: bool = True
    include_metadata: bool = True
    flatten_nested: bool = True  # For CSV, flatten nested structures
    date_format: str = "%Y-%m-%d"
    decimal_places: int = 2


class JSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for document data.

    Handles UUID, Decimal, datetime, date, and Enum types.
    """

    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


def format_as_json(
    extracted_data: dict,
    options: Optional[ExportOptions] = None,
) -> str:
    """
    Format extracted data as JSON.

    Args:
        extracted_data: Dictionary of extracted document data
        options: Export options

    Returns:
        JSON string
    """
    options = options or ExportOptions(format=ExportFormat.JSON)

    # Build export structure
    export_data = _build_export_structure(extracted_data, options)

    return json.dumps(export_data, cls=JSONEncoder, indent=2)


def format_as_csv(
    extracted_data: dict,
    options: Optional[ExportOptions] = None,
) -> str:
    """
    Format extracted data as CSV.

    Flattens the hierarchical structure into rows with:
    section, category, field_name, field_value, confidence

    Args:
        extracted_data: Dictionary of extracted document data
        options: Export options

    Returns:
        CSV string
    """
    options = options or ExportOptions(format=ExportFormat.CSV)

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    headers = ["section", "category", "field_name", "field_value"]
    if options.include_confidence:
        headers.append("confidence")
    writer.writerow(headers)

    # Write rows
    for row in _flatten_to_rows(extracted_data, options):
        writer.writerow(row)

    return output.getvalue()


def _build_export_structure(
    extracted_data: dict,
    options: ExportOptions,
) -> dict:
    """Build the export structure from extracted data."""
    export = {}

    # Demographics section
    if "patient" in extracted_data:
        patient = extracted_data["patient"]
        export["demographics"] = {
            "full_name": patient.get("name"),
            "date_of_birth": patient.get("date_of_birth"),
            "gender": patient.get("gender"),
            "member_id": patient.get("member_id"),
            "address": patient.get("address"),
        }

        if options.include_confidence:
            # Add per-field confidence if available
            confidence = extracted_data.get("confidence_scores", {})
            export["demographics_confidence"] = {
                "full_name": confidence.get("patient_name", confidence.get("name")),
                "date_of_birth": confidence.get("date_of_birth"),
                "member_id": confidence.get("member_id"),
            }

    # Provider section
    if "provider" in extracted_data:
        provider = extracted_data["provider"]
        export["provider"] = {
            "name": provider.get("name"),
            "npi": provider.get("npi"),
            "tax_id": provider.get("tax_id"),
            "specialty": provider.get("specialty"),
        }

    # Diagnoses section
    if "diagnoses" in extracted_data:
        export["diagnoses"] = []
        for dx in extracted_data["diagnoses"]:
            diagnosis = {
                "code": dx.get("code"),
                "description": dx.get("description"),
                "is_primary": dx.get("is_primary", False),
            }
            if options.include_confidence:
                diagnosis["confidence"] = dx.get("confidence")
            export["diagnoses"].append(diagnosis)

    # Procedures section
    if "procedures" in extracted_data:
        export["procedures"] = []
        for proc in extracted_data["procedures"]:
            procedure = {
                "code": proc.get("code"),
                "description": proc.get("description"),
                "modifiers": proc.get("modifiers"),
                "quantity": proc.get("quantity"),
                "charged_amount": proc.get("charged_amount"),
                "service_date": proc.get("service_date"),
            }
            if options.include_confidence:
                procedure["confidence"] = proc.get("confidence")
            export["procedures"].append(procedure)

    # Financial section
    if "financial" in extracted_data:
        export["financial"] = extracted_data["financial"]

    # Service dates
    if "dates" in extracted_data:
        export["service_dates"] = extracted_data["dates"]

    # Identifiers
    if "identifiers" in extracted_data:
        export["identifiers"] = extracted_data["identifiers"]

    # Metadata
    if options.include_metadata:
        export["_metadata"] = {
            "overall_confidence": extracted_data.get("overall_confidence"),
            "claim_type": extracted_data.get("claim_type"),
            "exported_at": datetime.utcnow().isoformat(),
        }

    return export


def _flatten_to_rows(
    extracted_data: dict,
    options: ExportOptions,
) -> Iterator[list]:
    """
    Flatten extracted data to CSV rows.

    Yields rows of: [section, category, field_name, field_value, confidence?]
    """
    # Patient/Demographics
    if "patient" in extracted_data:
        patient = extracted_data["patient"]
        confidence = extracted_data.get("confidence_scores", {})

        for field, value in patient.items():
            if value is not None:
                row = ["demographics", "patient", field, _format_value(value)]
                if options.include_confidence:
                    row.append(_format_confidence(confidence.get(field)))
                yield row

    # Provider
    if "provider" in extracted_data:
        provider = extracted_data["provider"]
        overall_conf = extracted_data.get("overall_confidence", 0.0)

        for field, value in provider.items():
            if value is not None:
                row = ["provider", "rendering", field, _format_value(value)]
                if options.include_confidence:
                    row.append(_format_confidence(overall_conf))
                yield row

    # Diagnoses
    if "diagnoses" in extracted_data:
        for idx, dx in enumerate(extracted_data["diagnoses"], 1):
            is_primary = dx.get("is_primary", idx == 1)
            category = "primary" if is_primary else "secondary"

            row = [
                "diagnosis",
                category,
                "code",
                dx.get("code", ""),
            ]
            if options.include_confidence:
                row.append(_format_confidence(dx.get("confidence")))
            yield row

            if dx.get("description"):
                row = [
                    "diagnosis",
                    category,
                    "description",
                    dx.get("description", ""),
                ]
                if options.include_confidence:
                    row.append(_format_confidence(dx.get("confidence")))
                yield row

    # Procedures
    if "procedures" in extracted_data:
        for idx, proc in enumerate(extracted_data["procedures"], 1):
            category = f"line_{idx}"

            # Code
            row = ["procedure", category, "code", proc.get("code", "")]
            if options.include_confidence:
                row.append(_format_confidence(proc.get("confidence")))
            yield row

            # Description
            if proc.get("description"):
                row = ["procedure", category, "description", proc.get("description", "")]
                if options.include_confidence:
                    row.append(_format_confidence(proc.get("confidence")))
                yield row

            # Modifiers
            if proc.get("modifiers"):
                modifiers = ",".join(proc["modifiers"]) if isinstance(proc["modifiers"], list) else proc["modifiers"]
                row = ["procedure", category, "modifiers", modifiers]
                if options.include_confidence:
                    row.append(_format_confidence(proc.get("confidence")))
                yield row

            # Quantity
            if proc.get("quantity"):
                row = ["procedure", category, "quantity", str(proc["quantity"])]
                if options.include_confidence:
                    row.append(_format_confidence(proc.get("confidence")))
                yield row

            # Charged amount
            if proc.get("charged_amount"):
                row = ["procedure", category, "charged_amount", str(proc["charged_amount"])]
                if options.include_confidence:
                    row.append(_format_confidence(proc.get("confidence")))
                yield row

            # Service date
            if proc.get("service_date"):
                row = ["procedure", category, "service_date", proc["service_date"]]
                if options.include_confidence:
                    row.append(_format_confidence(proc.get("confidence")))
                yield row

    # Financial
    if "financial" in extracted_data:
        financial = extracted_data["financial"]
        overall_conf = extracted_data.get("overall_confidence", 0.0)

        for field, value in financial.items():
            if value is not None:
                row = ["financial", "totals", field, _format_value(value)]
                if options.include_confidence:
                    row.append(_format_confidence(overall_conf))
                yield row

    # Service dates
    if "dates" in extracted_data:
        dates = extracted_data["dates"]
        overall_conf = extracted_data.get("overall_confidence", 0.0)

        for field, value in dates.items():
            if value is not None:
                row = ["service", "dates", field, _format_value(value)]
                if options.include_confidence:
                    row.append(_format_confidence(overall_conf))
                yield row

    # Identifiers
    if "identifiers" in extracted_data:
        identifiers = extracted_data["identifiers"]
        overall_conf = extracted_data.get("overall_confidence", 0.0)

        for field, value in identifiers.items():
            if value is not None:
                row = ["identifier", "claim", field, _format_value(value)]
                if options.include_confidence:
                    row.append(_format_confidence(overall_conf))
                yield row


def _format_value(value: Any) -> str:
    """Format a value for CSV output."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(float(value))
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return str(value)


def _format_confidence(value: Optional[float]) -> str:
    """Format confidence score for CSV output."""
    if value is None:
        return ""
    return f"{value:.2f}"


def generate_filename(
    document_id: str,
    format: ExportFormat,
    prefix: str = "document",
) -> str:
    """
    Generate a filename for the export.

    Args:
        document_id: Document ID
        format: Export format
        prefix: Filename prefix

    Returns:
        Filename with extension
    """
    # Use first 8 chars of UUID for readability
    short_id = document_id[:8] if len(document_id) > 8 else document_id
    extension = "json" if format == ExportFormat.JSON else "csv"
    return f"{prefix}_{short_id}.{extension}"


def get_content_type(format: ExportFormat) -> str:
    """
    Get the Content-Type header for the export format.

    Args:
        format: Export format

    Returns:
        MIME type string
    """
    if format == ExportFormat.JSON:
        return "application/json"
    return "text/csv"
