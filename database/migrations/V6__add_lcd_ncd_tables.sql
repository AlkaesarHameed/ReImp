-- Flyway Migration: V6
-- Description: Add LCD/NCD medical necessity tables
-- Author: System
-- Date: 2025-12-19
--
-- Source: Design Document 06_high_value_enhancements_design.md
-- Verified: 2025-12-19
--
-- This migration adds tables for:
-- - Coverage policies (LCD/NCD)
-- - Medical necessity checks
-- - Coverage determination results

-- ============================================================================
-- Coverage Policies Table
-- ============================================================================
-- Stores LCD (Local Coverage Determination) and NCD (National Coverage Determination) policies

CREATE TABLE IF NOT EXISTS coverage_policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Policy identification
    policy_id VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,

    -- Policy type
    coverage_type VARCHAR(10) NOT NULL,          -- LCD, NCD
    status VARCHAR(20) NOT NULL DEFAULT 'active',

    -- Dates
    effective_date DATE,
    termination_date DATE,
    last_updated DATE,

    -- MAC information (for LCDs)
    mac_region VARCHAR(20),                       -- MAC_A through MAC_L
    contractor_name VARCHAR(255),

    -- Policy content
    summary TEXT,
    full_text TEXT,

    -- Coverage details (JSONB for flexibility)
    covered_codes JSONB DEFAULT '[]',             -- CPT/HCPCS codes
    covered_diagnoses JSONB DEFAULT '[]',         -- ICD-10 codes with wildcards
    required_conditions JSONB DEFAULT '[]',       -- Clinical conditions
    documentation_requirements JSONB DEFAULT '[]', -- Required documentation
    frequency_limits TEXT,                        -- Coverage frequency

    -- Additional metadata
    source_url VARCHAR(500),
    cms_publication_id VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_coverage_type CHECK (coverage_type IN ('LCD', 'NCD')),
    CONSTRAINT chk_policy_status CHECK (status IN ('active', 'inactive', 'draft', 'retired'))
);

-- Indexes
CREATE INDEX idx_coverage_policies_type ON coverage_policies(coverage_type);
CREATE INDEX idx_coverage_policies_status ON coverage_policies(status);
CREATE INDEX idx_coverage_policies_mac ON coverage_policies(mac_region);
CREATE INDEX idx_coverage_policies_effective ON coverage_policies(effective_date);
CREATE INDEX idx_coverage_policies_codes ON coverage_policies USING GIN (covered_codes);
CREATE INDEX idx_coverage_policies_diagnoses ON coverage_policies USING GIN (covered_diagnoses);

-- Full text search index
CREATE INDEX idx_coverage_policies_text ON coverage_policies
    USING GIN (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(summary, '')));

-- Trigger for updated_at
CREATE TRIGGER update_coverage_policies_updated_at BEFORE UPDATE ON coverage_policies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE coverage_policies IS 'LCD and NCD coverage determination policies from CMS';
COMMENT ON COLUMN coverage_policies.coverage_type IS 'Policy type: LCD (Local) or NCD (National)';
COMMENT ON COLUMN coverage_policies.mac_region IS 'Medicare Administrative Contractor region (for LCDs)';

-- ============================================================================
-- Medical Necessity Checks Table
-- ============================================================================
-- Stores medical necessity validation requests and results

CREATE TABLE IF NOT EXISTS medical_necessity_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Check identification
    check_id VARCHAR(50) UNIQUE NOT NULL,
    claim_id VARCHAR(50),

    -- Input
    procedure_codes JSONB NOT NULL,               -- List of CPT/HCPCS codes
    diagnosis_codes JSONB NOT NULL,               -- List of ICD-10 codes
    service_date DATE,
    mac_region VARCHAR(20),

    -- Result
    is_medically_necessary BOOLEAN NOT NULL,
    overall_status VARCHAR(30) NOT NULL,          -- approved, denied, review_needed, etc.

    -- Summary
    covered_procedures JSONB DEFAULT '[]',
    non_covered_procedures JSONB DEFAULT '[]',
    procedures_needing_review JSONB DEFAULT '[]',

    -- Issues and recommendations
    issues JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',

    -- Stats
    policies_checked INTEGER DEFAULT 0,

    -- Performance
    processing_time_ms INTEGER,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_necessity_status CHECK (overall_status IN (
        'approved', 'denied', 'review_needed', 'partial', 'no_policy_found', 'error'
    ))
);

-- Indexes
CREATE INDEX idx_necessity_checks_tenant ON medical_necessity_checks(tenant_id);
CREATE INDEX idx_necessity_checks_claim ON medical_necessity_checks(claim_id);
CREATE INDEX idx_necessity_checks_status ON medical_necessity_checks(overall_status);
CREATE INDEX idx_necessity_checks_necessary ON medical_necessity_checks(is_medically_necessary);
CREATE INDEX idx_necessity_checks_created ON medical_necessity_checks(created_at);
CREATE INDEX idx_necessity_checks_procedures ON medical_necessity_checks USING GIN (procedure_codes);

-- Trigger for updated_at
CREATE TRIGGER update_necessity_checks_updated_at BEFORE UPDATE ON medical_necessity_checks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE medical_necessity_checks IS 'Medical necessity validation results against LCD/NCD policies';
COMMENT ON COLUMN medical_necessity_checks.overall_status IS 'Result: approved, denied, review_needed, partial, no_policy_found, error';

-- ============================================================================
-- Coverage Determinations Table
-- ============================================================================
-- Stores individual procedure coverage determinations

CREATE TABLE IF NOT EXISTS coverage_determinations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    check_id UUID NOT NULL REFERENCES medical_necessity_checks(id) ON DELETE CASCADE,

    -- Procedure
    procedure_code VARCHAR(10) NOT NULL,

    -- Policy match
    policy_id UUID REFERENCES coverage_policies(id),

    -- Determination
    is_covered BOOLEAN NOT NULL,
    status VARCHAR(30) NOT NULL,                  -- covered, not_covered, review_needed, etc.

    -- Coverage details
    covered_diagnoses JSONB DEFAULT '[]',         -- Matching diagnoses
    required_conditions JSONB DEFAULT '[]',
    documentation_requirements JSONB DEFAULT '[]',
    frequency_limits TEXT,

    -- Message
    message TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_determination_status CHECK (status IN (
        'covered', 'not_covered', 'diagnosis_mismatch', 'frequency_exceeded',
        'documentation_required', 'review_needed', 'no_policy'
    ))
);

-- Indexes
CREATE INDEX idx_determinations_check ON coverage_determinations(check_id);
CREATE INDEX idx_determinations_procedure ON coverage_determinations(procedure_code);
CREATE INDEX idx_determinations_policy ON coverage_determinations(policy_id);
CREATE INDEX idx_determinations_status ON coverage_determinations(status);
CREATE INDEX idx_determinations_covered ON coverage_determinations(is_covered);

COMMENT ON TABLE coverage_determinations IS 'Individual procedure coverage determinations';
COMMENT ON COLUMN coverage_determinations.status IS 'Determination status: covered, not_covered, diagnosis_mismatch, etc.';

-- ============================================================================
-- Policy Update History Table
-- ============================================================================
-- Tracks policy updates for audit purposes

CREATE TABLE IF NOT EXISTS policy_update_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_id UUID NOT NULL REFERENCES coverage_policies(id) ON DELETE CASCADE,

    -- Change info
    change_type VARCHAR(20) NOT NULL,             -- created, updated, retired
    change_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(100),

    -- Previous values (for updates)
    previous_status VARCHAR(20),
    previous_covered_codes JSONB,
    previous_covered_diagnoses JSONB,

    -- Notes
    change_reason TEXT,

    -- Constraints
    CONSTRAINT chk_policy_change_type CHECK (change_type IN ('created', 'updated', 'retired', 'reactivated'))
);

-- Indexes
CREATE INDEX idx_policy_history_policy ON policy_update_history(policy_id);
CREATE INDEX idx_policy_history_date ON policy_update_history(change_date);
CREATE INDEX idx_policy_history_type ON policy_update_history(change_type);

COMMENT ON TABLE policy_update_history IS 'Audit log for coverage policy changes';

-- ============================================================================
-- Function: Check Procedure Coverage
-- ============================================================================
-- Helper function to check if a procedure is covered by any policy

CREATE OR REPLACE FUNCTION check_procedure_coverage(
    p_procedure_code VARCHAR,
    p_mac_region VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    policy_id UUID,
    policy_code VARCHAR,
    title VARCHAR,
    coverage_type VARCHAR,
    covered_diagnoses JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cp.id,
        cp.policy_id,
        cp.title,
        cp.coverage_type,
        cp.covered_diagnoses
    FROM coverage_policies cp
    WHERE
        cp.status = 'active'
        AND cp.covered_codes ? p_procedure_code
        AND (p_mac_region IS NULL OR cp.mac_region = p_mac_region OR cp.coverage_type = 'NCD')
        AND (cp.effective_date IS NULL OR cp.effective_date <= CURRENT_DATE)
        AND (cp.termination_date IS NULL OR cp.termination_date >= CURRENT_DATE);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION check_procedure_coverage IS 'Find all active policies covering a procedure code';

-- ============================================================================
-- Function: Get Medical Necessity Statistics
-- ============================================================================
-- Returns medical necessity check statistics for a tenant

CREATE OR REPLACE FUNCTION get_necessity_stats(
    p_tenant_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    total_checks BIGINT,
    approved_count BIGINT,
    denied_count BIGINT,
    review_count BIGINT,
    approval_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total_checks,
        COUNT(*) FILTER (WHERE overall_status = 'approved')::BIGINT as approved_count,
        COUNT(*) FILTER (WHERE overall_status = 'denied')::BIGINT as denied_count,
        COUNT(*) FILTER (WHERE overall_status = 'review_needed')::BIGINT as review_count,
        CASE
            WHEN COUNT(*) > 0
            THEN ROUND(COUNT(*) FILTER (WHERE overall_status = 'approved')::NUMERIC / COUNT(*)::NUMERIC * 100, 2)
            ELSE 0
        END as approval_rate
    FROM medical_necessity_checks
    WHERE
        tenant_id = p_tenant_id
        AND created_at >= CURRENT_TIMESTAMP - (p_days || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_necessity_stats IS 'Get medical necessity check statistics for a tenant';

-- ============================================================================
-- Sample Data: Common LCD/NCD Policies
-- ============================================================================
-- Insert sample policies for testing (these would be loaded from CMS in production)

INSERT INTO coverage_policies (
    policy_id, title, coverage_type, status, effective_date,
    covered_codes, covered_diagnoses, required_conditions,
    documentation_requirements, frequency_limits, summary
) VALUES
-- NCD for MRI (sample)
(
    'NCD-220.2',
    'Magnetic Resonance Imaging (MRI)',
    'NCD',
    'active',
    '2020-01-01',
    '["70551", "70552", "70553", "71550", "71551", "71552", "73221", "73222", "73223"]',
    '["G43*", "R51*", "S06*", "C71*", "G35*", "M54*", "M79*"]',
    '["Documented neurological symptoms", "Prior conservative treatment failure for musculoskeletal"]',
    '["Clinical notes documenting symptoms", "Prior imaging results if applicable"]',
    'No specific frequency limits; medical necessity required for each study',
    'Coverage for MRI services when medically necessary for diagnosis'
),
-- NCD for CT Scans (sample)
(
    'NCD-220.1',
    'Computed Tomography (CT)',
    'NCD',
    'active',
    '2019-06-01',
    '["70450", "70460", "70470", "71250", "71260", "71270", "74150", "74160", "74170"]',
    '["R10*", "R07*", "C34*", "C78*", "J18*", "K80*", "S06*"]',
    '["Clinical indication for imaging", "Symptoms requiring diagnostic evaluation"]',
    '["Order documenting clinical indication", "Prior relevant imaging"]',
    NULL,
    'Coverage for CT imaging when clinically indicated'
),
-- LCD for Physical Therapy (sample)
(
    'L35036',
    'Outpatient Physical Therapy Services',
    'LCD',
    'active',
    '2021-03-15',
    '["97110", "97112", "97116", "97140", "97530", "97535", "97542"]',
    '["M54*", "M25*", "S83*", "S93*", "G81*", "Z96*", "M17*"]',
    '["Functional limitation documented", "Reasonable expectation of improvement", "Skilled services required"]',
    '["Plan of care", "Objective functional measurements", "Progress notes"]',
    'Re-evaluation required every 10 visits or 30 days',
    'Coverage for outpatient physical therapy with documented medical necessity'
),
-- LCD for Cardiac Rehabilitation (sample)
(
    'L33224',
    'Cardiac Rehabilitation Services',
    'LCD',
    'active',
    '2022-01-01',
    '["93797", "93798"]',
    '["I21*", "I25*", "Z95.1", "Z95.5", "I42*", "Z94.1"]',
    '["Qualifying cardiac event within 12 months", "Physician referral", "Stable cardiac status"]',
    '["Referring physician order", "Cardiac event documentation", "Risk stratification"]',
    '36 sessions over 36 weeks; additional sessions require documentation',
    'Coverage for cardiac rehabilitation following qualifying cardiac events'
),
-- LCD for Laboratory Services (sample)
(
    'L36093',
    'Comprehensive Metabolic Panel',
    'LCD',
    'active',
    '2020-07-01',
    '["80053"]',
    '["E11*", "E10*", "N18*", "I10*", "K76*", "E78*", "R73*"]',
    '["Monitoring of chronic condition", "Initial evaluation of symptoms"]',
    '["Clinical indication in order"]',
    'Once per year for monitoring; more frequent if clinically indicated',
    'Coverage for comprehensive metabolic panel with appropriate diagnosis'
)
ON CONFLICT (policy_id) DO NOTHING;

-- ============================================================================
-- Verification
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Migration V6 completed: LCD/NCD medical necessity tables created';
    RAISE NOTICE 'Tables: coverage_policies, medical_necessity_checks, coverage_determinations, policy_update_history';
    RAISE NOTICE 'Functions: check_procedure_coverage, get_necessity_stats';
    RAISE NOTICE 'Sample policies inserted for testing';
END $$;
