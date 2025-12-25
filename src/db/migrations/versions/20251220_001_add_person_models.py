"""Add Person and AssociatedData tables for document extraction.

Revision ID: 20251220_001
Revises:
Create Date: 2025-12-20

Source: Design Document 07-document-extraction-system-design.md Section 3.4
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = "20251220_001"
down_revision = "20251218_000"  # Depends on initial schema
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create persons and associated_data tables."""

    # NOTE: Using String columns instead of PostgreSQL ENUMs to avoid
    # SQLAlchemy asyncpg compatibility issues with enum creation.
    # The Python models still use Enum types for validation.

    # Create persons table
    op.create_table(
        "persons",
        # Primary key
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # Foreign keys
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claim_documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Demographics - Name
        sa.Column("full_name", sa.String(255), nullable=True, index=True),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("middle_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True, index=True),
        sa.Column("suffix", sa.String(20), nullable=True),
        # Demographics - Personal
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("date_of_birth", sa.Date, nullable=True, index=True),
        # Identifiers
        sa.Column("member_id", sa.String(100), nullable=True, index=True),
        sa.Column("national_id", sa.String(100), nullable=True),
        sa.Column("passport_number", sa.String(100), nullable=True),
        sa.Column("driver_license", sa.String(100), nullable=True),
        sa.Column("medical_record_number", sa.String(100), nullable=True, index=True),
        # Contact
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("phone_secondary", sa.String(50), nullable=True),
        # Address
        sa.Column("address_line1", sa.String(255), nullable=True),
        sa.Column("address_line2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(50), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("country", sa.String(50), nullable=True, server_default="US"),
        sa.Column("address_full", sa.Text, nullable=True),
        # Extraction metadata
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("extraction_source", sa.String(20), nullable=False, server_default="llm"),
        sa.Column("needs_review", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("reviewed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("field_confidence", postgresql.JSONB, nullable=True),
        sa.Column("person_role", sa.String(50), nullable=False, server_default="patient"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create indexes for persons
    op.create_index(
        "ix_persons_tenant_document",
        "persons",
        ["tenant_id", "document_id"],
    )
    op.create_index(
        "ix_persons_tenant_member",
        "persons",
        ["tenant_id", "member_id"],
    )
    op.create_index(
        "ix_persons_tenant_name",
        "persons",
        ["tenant_id", "last_name", "first_name"],
    )
    op.create_index(
        "ix_persons_tenant_dob",
        "persons",
        ["tenant_id", "date_of_birth"],
    )
    op.create_index(
        "ix_persons_needs_review",
        "persons",
        ["needs_review", "reviewed"],
    )

    # Create associated_data table
    op.create_table(
        "associated_data",
        # Primary key
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # Foreign keys
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("persons.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claim_documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Data classification
        sa.Column("category", sa.String(30), nullable=False, index=True),
        sa.Column("subcategory", sa.String(50), nullable=True),
        # Field data
        sa.Column("field_name", sa.String(255), nullable=False, index=True),
        sa.Column("field_value", sa.Text, nullable=True),
        sa.Column("field_type", sa.String(20), nullable=False, server_default="text"),
        # Code fields
        sa.Column("code_system", sa.String(50), nullable=True),
        sa.Column("code_description", sa.String(500), nullable=True),
        # Numeric/currency fields
        sa.Column("numeric_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        # Date fields
        sa.Column("date_value", sa.Date, nullable=True),
        # Source tracking
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("bounding_box", sa.String(255), nullable=True),
        sa.Column("extraction_source", sa.String(20), nullable=False, server_default="llm"),
        # Confidence
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("needs_review", sa.Boolean, nullable=False, server_default="false"),
        # Ordering
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("group_id", sa.String(100), nullable=True),
        sa.Column("group_index", sa.Integer, nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create indexes for associated_data
    op.create_index(
        "ix_associated_data_tenant_person",
        "associated_data",
        ["tenant_id", "person_id"],
    )
    op.create_index(
        "ix_associated_data_tenant_document",
        "associated_data",
        ["tenant_id", "document_id"],
    )
    op.create_index(
        "ix_associated_data_category_field",
        "associated_data",
        ["category", "field_name"],
    )
    op.create_index(
        "ix_associated_data_code",
        "associated_data",
        ["code_system", "field_value"],
    )
    op.create_index(
        "ix_associated_data_group",
        "associated_data",
        ["group_id", "group_index"],
    )


def downgrade() -> None:
    """Drop persons and associated_data tables."""

    # Drop tables (order matters due to foreign keys)
    op.drop_table("associated_data")
    op.drop_table("persons")
