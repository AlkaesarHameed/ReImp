"""
Person and AssociatedData Models for Document Extraction.

Provides structured storage for extracted demographics and associated data,
enabling efficient querying vs JSONB approach.

Source: Design Document 07-document-extraction-system-design.md Section 3.4
Verified: 2025-12-20
"""

import decimal
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimeStampedModel, UUIDModel

if TYPE_CHECKING:
    from src.models.claim import ClaimDocument
    from src.models.tenant import Tenant


class ExtractionSource(str, Enum):
    """Source of data extraction."""

    OCR = "ocr"
    NER = "ner"
    LLM = "llm"
    COMBINED = "combined"
    MANUAL = "manual"


class AssociatedDataCategory(str, Enum):
    """Categories for associated data."""

    DIAGNOSIS = "diagnosis"
    PROCEDURE = "procedure"
    PROVIDER = "provider"
    FINANCIAL = "financial"
    INSURANCE = "insurance"
    SERVICE = "service"
    OTHER = "other"


class FieldType(str, Enum):
    """Data types for extracted fields."""

    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    CURRENCY = "currency"
    CODE = "code"
    BOOLEAN = "boolean"


class Person(Base, UUIDModel, TimeStampedModel):
    """
    Extracted person demographics from documents.

    Stores structured demographic information extracted via OCR/NER/LLM,
    enabling efficient querying and data validation.

    Evidence: Person demographics structure based on HL7 FHIR Patient resource
    Source: https://www.hl7.org/fhir/patient.html
    Verified: 2025-12-20
    """

    __tablename__ = "persons"

    # Foreign Keys
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("claim_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Source document ID",
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owning tenant ID",
    )

    # Demographics - Name
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Full name as extracted",
    )
    first_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="First/given name",
    )
    middle_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Middle name",
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Last/family name",
    )
    suffix: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Name suffix (Jr., Sr., III, etc.)",
    )

    # Demographics - Personal
    gender: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Gender (male, female, other, unknown)",
    )
    date_of_birth: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        index=True,
        comment="Date of birth",
    )

    # Identifiers
    member_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Insurance member/subscriber ID",
    )
    national_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="National ID (SSN, etc.) - encrypted in production",
    )
    passport_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Passport number",
    )
    driver_license: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Driver's license number",
    )
    medical_record_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Medical record number (MRN)",
    )

    # Contact Information
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Email address",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Phone number",
    )
    phone_secondary: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Secondary phone number",
    )

    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Street address line 1",
    )
    address_line2: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Street address line 2",
    )
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="City",
    )
    state: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="State/Province",
    )
    postal_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Postal/ZIP code",
    )
    country: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default="US",
        comment="Country code (ISO 3166)",
    )

    # Full address (for display)
    address_full: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Full address as extracted (before parsing)",
    )

    # Extraction Metadata
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Overall extraction confidence (0.0 - 1.0)",
    )
    extraction_source: Mapped[ExtractionSource] = mapped_column(
        SQLEnum(ExtractionSource),
        nullable=False,
        default=ExtractionSource.LLM,
        comment="Primary extraction method",
    )
    needs_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Flagged for manual review",
    )
    reviewed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Has been manually reviewed",
    )
    reviewed_by: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        comment="User who reviewed this record",
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When record was reviewed",
    )

    # Per-field confidence scores (stored as JSONB for flexibility)
    field_confidence: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Per-field confidence scores: {field_name: score}",
    )

    # Role in document (patient, subscriber, dependent, etc.)
    person_role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="patient",
        comment="Role in document context",
    )

    # Relationships
    document: Mapped["ClaimDocument"] = relationship(
        back_populates="persons",
        foreign_keys=[document_id],
    )
    associated_data: Mapped[list["AssociatedData"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        order_by="AssociatedData.category, AssociatedData.field_name",
    )

    # Indexes
    __table_args__ = (
        Index("ix_persons_tenant_document", "tenant_id", "document_id"),
        Index("ix_persons_tenant_member", "tenant_id", "member_id"),
        Index("ix_persons_tenant_name", "tenant_id", "last_name", "first_name"),
        Index("ix_persons_tenant_dob", "tenant_id", "date_of_birth"),
        Index("ix_persons_needs_review", "needs_review", "reviewed"),
    )

    def __repr__(self) -> str:
        return f"<Person(id={self.id}, name='{self.full_name}', member_id='{self.member_id}')>"

    @property
    def display_name(self) -> str:
        """Get formatted display name."""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.middle_name:
            parts.append(self.middle_name)
        if self.last_name:
            parts.append(self.last_name)
        if self.suffix:
            parts.append(self.suffix)
        return " ".join(parts) if parts else self.full_name or "Unknown"

    @property
    def formatted_address(self) -> Optional[str]:
        """Get formatted mailing address."""
        if self.address_full:
            return self.address_full

        parts = []
        if self.address_line1:
            parts.append(self.address_line1)
        if self.address_line2:
            parts.append(self.address_line2)

        city_state_zip = []
        if self.city:
            city_state_zip.append(self.city)
        if self.state:
            city_state_zip.append(self.state)
        if self.postal_code:
            city_state_zip.append(self.postal_code)

        if city_state_zip:
            parts.append(", ".join(city_state_zip))

        return "\n".join(parts) if parts else None

    def get_field_confidence(self, field_name: str) -> Optional[float]:
        """Get confidence score for a specific field."""
        if self.field_confidence and field_name in self.field_confidence:
            return self.field_confidence[field_name]
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "gender": self.gender,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "member_id": self.member_id,
            "email": self.email,
            "phone": self.phone,
            "address": self.formatted_address,
            "confidence_score": self.confidence_score,
            "needs_review": self.needs_review,
            "person_role": self.person_role,
            "field_confidence": self.field_confidence,
        }


class AssociatedData(Base, UUIDModel, TimeStampedModel):
    """
    Associated information linked to a person.

    Stores non-demographic extracted data (diagnoses, procedures, financial info)
    in a flexible key-value structure with category organization.

    Evidence: Flexible data structure for varied document types
    Source: Design Document 07-document-extraction-system-design.md Section 3.4.3
    Verified: 2025-12-20
    """

    __tablename__ = "associated_data"

    # Foreign Keys
    person_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated person ID",
    )
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("claim_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Source document ID",
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owning tenant ID",
    )

    # Data Classification
    category: Mapped[AssociatedDataCategory] = mapped_column(
        SQLEnum(AssociatedDataCategory),
        nullable=False,
        index=True,
        comment="Data category",
    )
    subcategory: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Subcategory for additional grouping",
    )

    # Field Data
    field_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Field name/label",
    )
    field_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Extracted field value",
    )
    field_type: Mapped[FieldType] = mapped_column(
        SQLEnum(FieldType),
        nullable=False,
        default=FieldType.TEXT,
        comment="Data type of the field",
    )

    # For code fields (ICD-10, CPT, etc.)
    code_system: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Code system (ICD10, CPT, HCPCS, etc.)",
    )
    code_description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Description/display text for code",
    )

    # For numeric/currency fields
    numeric_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Parsed numeric value",
    )
    currency: Mapped[Optional[str]] = mapped_column(
        String(3),
        nullable=True,
        comment="Currency code for monetary values",
    )

    # For date fields
    date_value: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Parsed date value",
    )

    # Source Tracking
    page_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Page where data was found",
    )
    bounding_box: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Bounding box coordinates (JSON: [x1,y1,x2,y2])",
    )
    extraction_source: Mapped[ExtractionSource] = mapped_column(
        SQLEnum(ExtractionSource),
        nullable=False,
        default=ExtractionSource.LLM,
        comment="How this data was extracted",
    )

    # Confidence
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Extraction confidence (0.0 - 1.0)",
    )
    needs_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Flagged for manual review",
    )

    # Ordering
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Display order within category",
    )

    # For grouped data (e.g., line items)
    group_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Group identifier for related fields",
    )
    group_index: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Index within group (e.g., line item number)",
    )

    # Relationships
    person: Mapped["Person"] = relationship(back_populates="associated_data")

    # Indexes
    __table_args__ = (
        Index("ix_associated_data_tenant_person", "tenant_id", "person_id"),
        Index("ix_associated_data_tenant_document", "tenant_id", "document_id"),
        Index("ix_associated_data_category_field", "category", "field_name"),
        Index("ix_associated_data_code", "code_system", "field_value"),
        Index("ix_associated_data_group", "group_id", "group_index"),
    )

    def __repr__(self) -> str:
        return f"<AssociatedData(id={self.id}, category='{self.category}', field='{self.field_name}')>"

    @property
    def typed_value(self):
        """Get value in appropriate Python type."""
        if self.field_type == FieldType.NUMBER:
            return self.numeric_value
        elif self.field_type == FieldType.CURRENCY:
            return self.numeric_value
        elif self.field_type == FieldType.DATE:
            return self.date_value
        elif self.field_type == FieldType.BOOLEAN:
            return self.field_value.lower() in ("true", "yes", "1") if self.field_value else None
        else:
            return self.field_value

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "person_id": str(self.person_id),
            "category": self.category.value,
            "subcategory": self.subcategory,
            "field_name": self.field_name,
            "field_value": self.field_value,
            "field_type": self.field_type.value,
            "code_system": self.code_system,
            "code_description": self.code_description,
            "numeric_value": float(self.numeric_value) if self.numeric_value else None,
            "date_value": self.date_value.isoformat() if self.date_value else None,
            "confidence_score": self.confidence_score,
            "needs_review": self.needs_review,
            "page_number": self.page_number,
        }


# =============================================================================
# Helper Functions
# =============================================================================


def create_person_from_extracted_data(
    document_id: UUID,
    tenant_id: UUID,
    extracted_data: dict,
    confidence_scores: Optional[dict] = None,
) -> Person:
    """
    Create a Person record from extracted JSONB data.

    Args:
        document_id: Source document ID
        tenant_id: Tenant ID
        extracted_data: Dictionary with patient/demographics data
        confidence_scores: Optional per-field confidence scores

    Returns:
        Person instance (not yet added to session)
    """
    patient = extracted_data.get("patient", {})
    overall_confidence = extracted_data.get("overall_confidence", 0.0)

    # Parse name
    full_name = patient.get("name", "")
    name_parts = full_name.split() if full_name else []

    first_name = name_parts[0] if len(name_parts) > 0 else None
    last_name = name_parts[-1] if len(name_parts) > 1 else None
    middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else None

    # Parse date of birth
    dob = None
    dob_str = patient.get("date_of_birth")
    if dob_str:
        try:
            from datetime import datetime as dt
            dob = dt.fromisoformat(dob_str).date()
        except (ValueError, TypeError):
            pass

    # Determine if needs review
    needs_review = overall_confidence < 0.70

    return Person(
        document_id=document_id,
        tenant_id=tenant_id,
        full_name=full_name or None,
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        gender=patient.get("gender"),
        date_of_birth=dob,
        member_id=patient.get("member_id"),
        address_full=patient.get("address"),
        confidence_score=overall_confidence,
        extraction_source=ExtractionSource.LLM,
        needs_review=needs_review,
        field_confidence=confidence_scores,
        person_role="patient",
    )


def create_associated_data_from_extracted(
    person_id: UUID,
    document_id: UUID,
    tenant_id: UUID,
    extracted_data: dict,
) -> list[AssociatedData]:
    """
    Create AssociatedData records from extracted JSONB data.

    Args:
        person_id: Associated person ID
        document_id: Source document ID
        tenant_id: Tenant ID
        extracted_data: Dictionary with all extracted data

    Returns:
        List of AssociatedData instances (not yet added to session)
    """
    records = []
    display_order = 0

    # Diagnoses
    for idx, dx in enumerate(extracted_data.get("diagnoses", [])):
        records.append(AssociatedData(
            person_id=person_id,
            document_id=document_id,
            tenant_id=tenant_id,
            category=AssociatedDataCategory.DIAGNOSIS,
            field_name="diagnosis_code",
            field_value=dx.get("code"),
            field_type=FieldType.CODE,
            code_system="ICD10",
            code_description=dx.get("description"),
            confidence_score=dx.get("confidence", 0.0),
            needs_review=dx.get("confidence", 0.0) < 0.70,
            display_order=display_order,
            group_id=f"diagnosis_{idx}",
            group_index=idx,
        ))
        display_order += 1

    # Procedures
    for idx, proc in enumerate(extracted_data.get("procedures", [])):
        records.append(AssociatedData(
            person_id=person_id,
            document_id=document_id,
            tenant_id=tenant_id,
            category=AssociatedDataCategory.PROCEDURE,
            field_name="procedure_code",
            field_value=proc.get("code"),
            field_type=FieldType.CODE,
            code_system="CPT",
            code_description=proc.get("description"),
            confidence_score=proc.get("confidence", 0.0),
            needs_review=proc.get("confidence", 0.0) < 0.70,
            display_order=display_order,
            group_id=f"procedure_{idx}",
            group_index=idx,
        ))

        # Add charged amount if present
        if proc.get("charged_amount"):
            try:
                amount = Decimal(str(proc["charged_amount"]))
                records.append(AssociatedData(
                    person_id=person_id,
                    document_id=document_id,
                    tenant_id=tenant_id,
                    category=AssociatedDataCategory.PROCEDURE,
                    field_name="charged_amount",
                    field_value=str(amount),
                    field_type=FieldType.CURRENCY,
                    numeric_value=amount,
                    currency="USD",
                    confidence_score=proc.get("confidence", 0.0),
                    display_order=display_order + 1,
                    group_id=f"procedure_{idx}",
                    group_index=idx,
                ))
            except (ValueError, TypeError, decimal.InvalidOperation):
                pass

        display_order += 2

    # Provider
    provider = extracted_data.get("provider", {})
    if provider:
        for field_name, field_value in provider.items():
            if field_value:
                records.append(AssociatedData(
                    person_id=person_id,
                    document_id=document_id,
                    tenant_id=tenant_id,
                    category=AssociatedDataCategory.PROVIDER,
                    field_name=field_name,
                    field_value=str(field_value),
                    field_type=FieldType.TEXT,
                    confidence_score=extracted_data.get("overall_confidence", 0.0),
                    display_order=display_order,
                ))
                display_order += 1

    # Financial
    financial = extracted_data.get("financial", {})
    if financial:
        for field_name, field_value in financial.items():
            if field_value:
                field_type = FieldType.CURRENCY if "amount" in field_name or "charged" in field_name else FieldType.TEXT
                numeric_val = None
                if field_type == FieldType.CURRENCY:
                    try:
                        numeric_val = Decimal(str(field_value))
                    except (ValueError, TypeError):
                        pass

                records.append(AssociatedData(
                    person_id=person_id,
                    document_id=document_id,
                    tenant_id=tenant_id,
                    category=AssociatedDataCategory.FINANCIAL,
                    field_name=field_name,
                    field_value=str(field_value),
                    field_type=field_type,
                    numeric_value=numeric_val,
                    currency="USD" if numeric_val else None,
                    confidence_score=extracted_data.get("overall_confidence", 0.0),
                    display_order=display_order,
                ))
                display_order += 1

    return records
