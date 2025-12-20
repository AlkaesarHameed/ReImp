-- Claims Processing System - Database Initialization
-- Source: Design Document Section 6.1 - Deployment Architecture
-- Verified: 2025-12-18

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schema
CREATE SCHEMA IF NOT EXISTS claims;

-- Set search path
SET search_path TO claims, public;

-- Create claims table
CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_number VARCHAR(50) UNIQUE NOT NULL,
    patient_id UUID NOT NULL,
    provider_id UUID NOT NULL,
    payer_id UUID NOT NULL,

    -- Claim details
    type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'submitted',
    priority VARCHAR(20) DEFAULT 'normal',

    -- Financial
    total_charge DECIMAL(12, 2) NOT NULL,
    allowed_amount DECIMAL(12, 2),
    paid_amount DECIMAL(12, 2),
    patient_responsibility DECIMAL(12, 2),

    -- Dates
    service_date DATE NOT NULL,
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    adjudication_date TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    tenant_id UUID NOT NULL
);

-- Create claim line items table
CREATE TABLE IF NOT EXISTS claim_line_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,

    -- Procedure details
    procedure_code VARCHAR(20) NOT NULL,
    modifier_codes VARCHAR(20)[],
    description TEXT,

    -- Diagnosis
    diagnosis_codes VARCHAR(20)[] NOT NULL,

    -- Financial
    quantity INTEGER DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    allowed_amount DECIMAL(10, 2),

    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    denial_reason VARCHAR(200),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create patients table
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    member_id VARCHAR(50) NOT NULL,

    -- Demographics
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(20),

    -- Contact (encrypted at application level)
    address_encrypted BYTEA,
    phone_encrypted BYTEA,
    email_encrypted BYTEA,

    -- Insurance
    insurance_id VARCHAR(50),
    group_number VARCHAR(50),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tenant_id UUID NOT NULL,

    UNIQUE(member_id, tenant_id)
);

-- Create providers table
CREATE TABLE IF NOT EXISTS providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    npi VARCHAR(20) UNIQUE NOT NULL,

    -- Provider info
    name VARCHAR(200) NOT NULL,
    organization VARCHAR(200),
    specialty VARCHAR(100),

    -- Contact
    address JSONB,
    phone VARCHAR(20),
    fax VARCHAR(20),

    -- Network status
    network_status VARCHAR(50) DEFAULT 'in_network',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tenant_id UUID NOT NULL
);

-- Create payers table
CREATE TABLE IF NOT EXISTS payers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payer_id VARCHAR(50) UNIQUE NOT NULL,

    name VARCHAR(200) NOT NULL,
    type VARCHAR(50),

    -- EDI info
    edi_payer_id VARCHAR(50),
    submission_method VARCHAR(50) DEFAULT 'electronic',

    -- Contact
    address JSONB,
    phone VARCHAR(20),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'info',

    -- Actor
    user_id UUID,
    username VARCHAR(100),
    ip_address INET,

    -- Resource
    resource_type VARCHAR(100),
    resource_id UUID,

    -- Event details
    action VARCHAR(100),
    success BOOLEAN DEFAULT true,
    message TEXT,
    details JSONB,

    -- Compliance
    compliance_tags VARCHAR(50)[],

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
CREATE INDEX IF NOT EXISTS idx_claims_submission_date ON claims(submission_date);
CREATE INDEX IF NOT EXISTS idx_claims_patient_id ON claims(patient_id);
CREATE INDEX IF NOT EXISTS idx_claims_tenant_id ON claims(tenant_id);
CREATE INDEX IF NOT EXISTS idx_claim_line_items_claim_id ON claim_line_items(claim_id);
CREATE INDEX IF NOT EXISTS idx_patients_member_id ON patients(member_id);
CREATE INDEX IF NOT EXISTS idx_providers_npi ON providers(npi);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables
CREATE TRIGGER update_claims_updated_at
    BEFORE UPDATE ON claims
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_patients_updated_at
    BEFORE UPDATE ON patients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_providers_updated_at
    BEFORE UPDATE ON providers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA claims TO postgres;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA claims TO postgres;
