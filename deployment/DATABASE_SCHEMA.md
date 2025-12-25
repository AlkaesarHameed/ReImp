# Database Schema Reference

This document describes all database tables and their relationships.

## Overview

The system uses PostgreSQL with the pgvector extension for semantic search capabilities.

**Total Tables:** 17

## Core Tables

### users
User accounts for system access.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | User identifier |
| tenant_id | UUID | FK → tenants.id | Associated tenant |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Email address |
| password_hash | VARCHAR(255) | NOT NULL | Bcrypt hash |
| first_name | VARCHAR(100) | | First name |
| last_name | VARCHAR(100) | | Last name |
| role | VARCHAR(50) | NOT NULL | User role |
| is_active | BOOLEAN | DEFAULT true | Account status |
| mfa_enabled | BOOLEAN | DEFAULT false | MFA status |
| created_at | TIMESTAMP(TZ) | NOT NULL | Creation time |
| updated_at | TIMESTAMP(TZ) | NOT NULL | Last update |
| last_login | TIMESTAMP(TZ) | | Last login time |

### tenants
Multi-tenant organizations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Tenant identifier |
| name | VARCHAR(255) | UNIQUE, NOT NULL | Organization name |
| slug | VARCHAR(100) | UNIQUE, NOT NULL | URL-safe identifier |
| is_active | BOOLEAN | DEFAULT true | Active status |
| settings | JSONB | | Tenant settings |
| created_at | TIMESTAMP(TZ) | NOT NULL | Creation time |
| updated_at | TIMESTAMP(TZ) | NOT NULL | Last update |

### tenant_settings
Per-tenant configuration.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Setting identifier |
| tenant_id | UUID | FK → tenants.id, UNIQUE | Tenant reference |
| theme | VARCHAR(20) | DEFAULT 'default' | UI theme |
| locale | VARCHAR(10) | DEFAULT 'en-US' | Language |
| date_format | VARCHAR(20) | DEFAULT 'YYYY-MM-DD' | Date display |
| currency | VARCHAR(3) | DEFAULT 'USD' | Currency code |
| timezone | VARCHAR(50) | DEFAULT 'UTC' | Timezone |
| max_file_size_mb | INTEGER | DEFAULT 100 | Upload limit |
| allowed_file_types | TEXT[] | | Allowed extensions |
| created_at | TIMESTAMP(TZ) | NOT NULL | Creation time |
| updated_at | TIMESTAMP(TZ) | NOT NULL | Last update |

## Document Tables

### documents
General document storage.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Document identifier |
| tenant_id | UUID | FK → tenants.id | Tenant reference |
| filename | VARCHAR(255) | NOT NULL | Original filename |
| storage_path | VARCHAR(512) | NOT NULL | MinIO path |
| mime_type | VARCHAR(100) | | MIME type |
| file_size | BIGINT | | Size in bytes |
| status | VARCHAR(50) | DEFAULT 'uploaded' | Processing status |
| metadata | JSONB | | Additional metadata |
| created_at | TIMESTAMP(TZ) | NOT NULL | Upload time |
| updated_at | TIMESTAMP(TZ) | NOT NULL | Last update |

### claim_documents
Claim-specific document processing.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Document identifier |
| tenant_id | UUID | FK → tenants.id | Tenant reference |
| claim_id | UUID | FK → claims.id | Linked claim |
| document_type | VARCHAR(50) | NOT NULL | Document category |
| filename | VARCHAR(255) | NOT NULL | Original filename |
| storage_path | VARCHAR(512) | NOT NULL | MinIO path |
| status | VARCHAR(50) | DEFAULT 'uploaded' | Processing status |
| ocr_text | TEXT | | Extracted OCR text |
| ocr_confidence | FLOAT | | OCR confidence score |
| extracted_data | JSONB | | LLM extracted data |
| page_count | INTEGER | | Number of pages |
| processing_errors | JSONB | | Error details |
| created_at | TIMESTAMP(TZ) | NOT NULL | Upload time |
| updated_at | TIMESTAMP(TZ) | NOT NULL | Last update |
| processed_at | TIMESTAMP(TZ) | | Processing completion |

## Extraction Tables

### persons
Extracted person data from documents.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Person identifier |
| document_id | UUID | FK → claim_documents.id | Source document |
| tenant_id | UUID | FK → tenants.id | Tenant reference |
| full_name | VARCHAR(255) | INDEX | Full name |
| first_name | VARCHAR(100) | | First name |
| middle_name | VARCHAR(100) | | Middle name |
| last_name | VARCHAR(100) | INDEX | Last name |
| suffix | VARCHAR(20) | | Name suffix |
| gender | VARCHAR(20) | | Gender |
| date_of_birth | DATE | INDEX | Birth date |
| member_id | VARCHAR(100) | INDEX | Insurance member ID |
| national_id | VARCHAR(100) | | National ID |
| passport_number | VARCHAR(100) | | Passport number |
| driver_license | VARCHAR(100) | | Driver's license |
| medical_record_number | VARCHAR(100) | INDEX | MRN |
| email | VARCHAR(255) | | Email address |
| phone | VARCHAR(50) | | Primary phone |
| phone_secondary | VARCHAR(50) | | Secondary phone |
| address_line1 | VARCHAR(255) | | Address line 1 |
| address_line2 | VARCHAR(255) | | Address line 2 |
| city | VARCHAR(100) | | City |
| state | VARCHAR(50) | | State/Province |
| postal_code | VARCHAR(20) | | ZIP/Postal code |
| country | VARCHAR(50) | DEFAULT 'US' | Country |
| address_full | TEXT | | Full address text |
| confidence_score | FLOAT | DEFAULT 0.0 | Extraction confidence |
| extraction_source | VARCHAR(20) | DEFAULT 'llm' | Source (llm/ocr/manual) |
| needs_review | BOOLEAN | DEFAULT false | Needs human review |
| reviewed | BOOLEAN | DEFAULT false | Has been reviewed |
| reviewed_by | UUID | | Reviewer user ID |
| reviewed_at | TIMESTAMP(TZ) | | Review timestamp |
| field_confidence | JSONB | | Per-field confidence |
| person_role | VARCHAR(50) | DEFAULT 'patient' | Role (patient/provider) |
| created_at | TIMESTAMP(TZ) | NOT NULL | Creation time |
| updated_at | TIMESTAMP(TZ) | NOT NULL | Last update |

### associated_data
Extracted field data linked to persons.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Data identifier |
| person_id | UUID | FK → persons.id | Parent person |
| document_id | UUID | FK → claim_documents.id | Source document |
| tenant_id | UUID | FK → tenants.id | Tenant reference |
| category | VARCHAR(30) | INDEX, NOT NULL | Data category |
| subcategory | VARCHAR(50) | | Subcategory |
| field_name | VARCHAR(255) | INDEX, NOT NULL | Field name |
| field_value | TEXT | | Text value |
| field_type | VARCHAR(20) | DEFAULT 'text' | Value type |
| code_system | VARCHAR(50) | | Code system (ICD-10, CPT) |
| code_description | VARCHAR(500) | | Code description |
| numeric_value | DECIMAL(12,2) | | Numeric value |
| currency | VARCHAR(3) | | Currency code |
| date_value | DATE | | Date value |
| page_number | INTEGER | | Source page |
| bounding_box | VARCHAR(255) | | OCR bounding box |
| extraction_source | VARCHAR(20) | DEFAULT 'llm' | Source |
| confidence_score | FLOAT | DEFAULT 0.0 | Confidence |
| needs_review | BOOLEAN | DEFAULT false | Needs review |
| display_order | INTEGER | DEFAULT 0 | Display order |
| group_id | VARCHAR(100) | | Grouping ID |
| group_index | INTEGER | | Index within group |
| created_at | TIMESTAMP(TZ) | NOT NULL | Creation time |
| updated_at | TIMESTAMP(TZ) | NOT NULL | Last update |

## Healthcare Tables

### healthcare_providers
Provider registry.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Provider identifier |
| tenant_id | UUID | FK → tenants.id | Tenant reference |
| npi | VARCHAR(20) | INDEX | NPI number |
| tax_id | VARCHAR(20) | | Tax ID |
| name | VARCHAR(255) | NOT NULL | Provider name |
| specialty | VARCHAR(100) | | Medical specialty |
| address | TEXT | | Address |
| phone | VARCHAR(50) | | Phone number |
| is_in_network | BOOLEAN | DEFAULT true | Network status |
| effective_date | DATE | | Contract start |
| termination_date | DATE | | Contract end |
| created_at | TIMESTAMP(TZ) | NOT NULL | Creation time |
| updated_at | TIMESTAMP(TZ) | NOT NULL | Last update |

### policies
Insurance policies.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Policy identifier |
| tenant_id | UUID | FK → tenants.id | Tenant reference |
| policy_number | VARCHAR(100) | UNIQUE, NOT NULL | Policy number |
| group_number | VARCHAR(100) | | Group number |
| plan_name | VARCHAR(255) | | Plan name |
| plan_type | VARCHAR(50) | | Plan type (HMO, PPO) |
| effective_date | DATE | | Coverage start |
| termination_date | DATE | | Coverage end |
| deductible | DECIMAL(10,2) | | Annual deductible |
| copay | DECIMAL(10,2) | | Standard copay |
| coinsurance_rate | DECIMAL(5,2) | | Coinsurance % |
| out_of_pocket_max | DECIMAL(10,2) | | OOP maximum |
| created_at | TIMESTAMP(TZ) | NOT NULL | Creation time |
| updated_at | TIMESTAMP(TZ) | NOT NULL | Last update |

### members
Policy members.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Member identifier |
| tenant_id | UUID | FK → tenants.id | Tenant reference |
| policy_id | UUID | FK → policies.id | Associated policy |
| member_id | VARCHAR(100) | INDEX, NOT NULL | Member ID |
| first_name | VARCHAR(100) | | First name |
| last_name | VARCHAR(100) | | Last name |
| date_of_birth | DATE | | Birth date |
| gender | VARCHAR(20) | | Gender |
| relationship | VARCHAR(50) | | Relationship to subscriber |
| effective_date | DATE | | Coverage start |
| termination_date | DATE | | Coverage end |
| created_at | TIMESTAMP(TZ) | NOT NULL | Creation time |
| updated_at | TIMESTAMP(TZ) | NOT NULL | Last update |

### claims
Claim records.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Claim identifier |
| tenant_id | UUID | FK → tenants.id | Tenant reference |
| claim_number | VARCHAR(100) | UNIQUE, NOT NULL | Claim number |
| member_id | UUID | FK → members.id | Member reference |
| provider_id | UUID | FK → healthcare_providers.id | Provider reference |
| service_date | DATE | | Date of service |
| diagnosis_codes | TEXT[] | | ICD-10 codes |
| procedure_codes | TEXT[] | | CPT codes |
| billed_amount | DECIMAL(12,2) | | Billed amount |
| allowed_amount | DECIMAL(12,2) | | Allowed amount |
| paid_amount | DECIMAL(12,2) | | Paid amount |
| status | VARCHAR(50) | DEFAULT 'submitted' | Claim status |
| adjudication_date | DATE | | Processing date |
| created_at | TIMESTAMP(TZ) | NOT NULL | Creation time |
| updated_at | TIMESTAMP(TZ) | NOT NULL | Last update |

### fee_schedules
Pricing data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Fee identifier |
| tenant_id | UUID | FK → tenants.id | Tenant reference |
| procedure_code | VARCHAR(20) | INDEX, NOT NULL | CPT code |
| modifier | VARCHAR(10) | | Modifier |
| description | VARCHAR(500) | | Description |
| fee_amount | DECIMAL(10,2) | NOT NULL | Fee amount |
| effective_date | DATE | NOT NULL | Start date |
| termination_date | DATE | | End date |
| created_at | TIMESTAMP(TZ) | NOT NULL | Creation time |
| updated_at | TIMESTAMP(TZ) | NOT NULL | Last update |

## System Tables

### roles
User role definitions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Role identifier |
| tenant_id | UUID | FK → tenants.id | Tenant reference |
| name | VARCHAR(100) | NOT NULL | Role name |
| description | TEXT | | Role description |
| permissions | TEXT[] | | Permission list |
| created_at | TIMESTAMP(TZ) | NOT NULL | Creation time |
| updated_at | TIMESTAMP(TZ) | NOT NULL | Last update |

### llm_settings
Per-tenant LLM configuration.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Setting identifier |
| tenant_id | UUID | FK → tenants.id, UNIQUE | Tenant reference |
| primary_provider | VARCHAR(50) | DEFAULT 'openai' | Primary LLM |
| fallback_provider | VARCHAR(50) | DEFAULT 'ollama' | Fallback LLM |
| model_name | VARCHAR(100) | | Model name |
| temperature | FLOAT | DEFAULT 0.7 | Temperature |
| max_tokens | INTEGER | DEFAULT 4096 | Token limit |
| custom_prompt | TEXT | | Custom system prompt |
| created_at | TIMESTAMP(TZ) | NOT NULL | Creation time |
| updated_at | TIMESTAMP(TZ) | NOT NULL | Last update |

### validation_results
Claim validation outcomes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Result identifier |
| tenant_id | UUID | FK → tenants.id | Tenant reference |
| claim_id | UUID | FK → claims.id | Claim reference |
| rule_id | VARCHAR(100) | | Rule identifier |
| rule_name | VARCHAR(255) | | Rule name |
| status | VARCHAR(50) | | Pass/Fail/Warning |
| message | TEXT | | Result message |
| details | JSONB | | Additional details |
| created_at | TIMESTAMP(TZ) | NOT NULL | Validation time |

### edi_transactions
EDI processing logs.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Transaction identifier |
| tenant_id | UUID | FK → tenants.id | Tenant reference |
| transaction_type | VARCHAR(20) | NOT NULL | EDI type (837, 835) |
| direction | VARCHAR(20) | NOT NULL | Inbound/Outbound |
| trading_partner | VARCHAR(100) | | Partner ID |
| filename | VARCHAR(255) | | File name |
| status | VARCHAR(50) | DEFAULT 'pending' | Status |
| error_message | TEXT | | Error details |
| raw_content | TEXT | | Raw EDI content |
| parsed_data | JSONB | | Parsed data |
| created_at | TIMESTAMP(TZ) | NOT NULL | Creation time |
| processed_at | TIMESTAMP(TZ) | | Processing time |

### audit_logs
System audit trail.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Log identifier |
| tenant_id | UUID | FK → tenants.id | Tenant reference |
| user_id | UUID | FK → users.id | User reference |
| action | VARCHAR(100) | NOT NULL | Action performed |
| resource_type | VARCHAR(100) | | Resource type |
| resource_id | UUID | | Resource ID |
| details | JSONB | | Action details |
| ip_address | VARCHAR(45) | | Client IP |
| user_agent | VARCHAR(500) | | User agent |
| created_at | TIMESTAMP(TZ) | NOT NULL | Action time |

---

## Indexes

Key indexes for query performance:

| Table | Index Name | Columns |
|-------|------------|---------|
| persons | ix_persons_tenant_document | tenant_id, document_id |
| persons | ix_persons_tenant_member | tenant_id, member_id |
| persons | ix_persons_tenant_name | tenant_id, last_name, first_name |
| persons | ix_persons_tenant_dob | tenant_id, date_of_birth |
| persons | ix_persons_needs_review | needs_review, reviewed |
| associated_data | ix_associated_data_tenant_person | tenant_id, person_id |
| associated_data | ix_associated_data_tenant_document | tenant_id, document_id |
| associated_data | ix_associated_data_category_field | category, field_name |
| associated_data | ix_associated_data_code | code_system, field_value |
| associated_data | ix_associated_data_group | group_id, group_index |

---

## Entity Relationship Diagram

```
tenants ─┬─< users
         ├─< tenant_settings
         ├─< roles
         ├─< documents
         ├─< claim_documents ──< persons ──< associated_data
         ├─< healthcare_providers
         ├─< policies ──< members
         ├─< claims ──< validation_results
         ├─< fee_schedules
         ├─< llm_settings
         ├─< edi_transactions
         └─< audit_logs
```
