-- Flyway Migration: V5
-- Description: Add eligibility verification tables
-- Author: System
-- Date: 2025-12-19
--
-- Source: Design Document 06_high_value_enhancements_design.md
-- Verified: 2025-12-19
--
-- This migration adds tables for:
-- - Eligibility checks (270/271 transaction tracking)
-- - Eligibility responses (parsed eligibility data)
-- - Eligibility cache (performance optimization)

-- ============================================================================
-- Eligibility Checks Table
-- ============================================================================
-- Stores eligibility verification requests and results

CREATE TABLE IF NOT EXISTS eligibility_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Check identification
    check_id VARCHAR(50) UNIQUE NOT NULL,
    trace_number VARCHAR(50),

    -- Member identification
    member_id VARCHAR(50) NOT NULL,
    subscriber_first_name VARCHAR(100),
    subscriber_last_name VARCHAR(100),
    subscriber_dob DATE,
    group_number VARCHAR(50),

    -- Dependent (if applicable)
    dependent_first_name VARCHAR(100),
    dependent_last_name VARCHAR(100),
    dependent_dob DATE,
    is_dependent_check BOOLEAN DEFAULT false,

    -- Payer
    payer_id VARCHAR(50) NOT NULL,
    payer_name VARCHAR(255),

    -- Provider
    provider_npi VARCHAR(10),
    provider_name VARCHAR(255),

    -- Service details
    service_date DATE NOT NULL,
    service_type_codes JSONB DEFAULT '["30"]',

    -- Request/Response
    request_x12 TEXT,                          -- X12 270 content
    response_x12 TEXT,                         -- X12 271 content
    request_sent_at TIMESTAMP WITH TIME ZONE,
    response_received_at TIMESTAMP WITH TIME ZONE,

    -- Result
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    result_type VARCHAR(30),
    is_eligible BOOLEAN,

    -- Coverage info
    coverage_start DATE,
    coverage_end DATE,
    is_coverage_active BOOLEAN DEFAULT false,
    plan_name VARCHAR(255),

    -- Benefits summary
    deductible DECIMAL(12,2),
    deductible_met DECIMAL(12,2),
    out_of_pocket_max DECIMAL(12,2),
    out_of_pocket_met DECIMAL(12,2),

    -- Errors
    errors JSONB,
    payer_message TEXT,

    -- Performance
    processing_time_ms INTEGER,

    -- Cache info
    cached BOOLEAN DEFAULT false,
    cache_expires_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_eligibility_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'timeout', 'cached')),
    CONSTRAINT chk_eligibility_result_type CHECK (result_type IS NULL OR result_type IN ('eligible', 'not_eligible', 'coverage_terminated', 'member_not_found', 'payer_error', 'unknown'))
);

-- Indexes
CREATE INDEX idx_eligibility_checks_tenant ON eligibility_checks(tenant_id);
CREATE INDEX idx_eligibility_checks_member ON eligibility_checks(member_id);
CREATE INDEX idx_eligibility_checks_payer ON eligibility_checks(payer_id);
CREATE INDEX idx_eligibility_checks_status ON eligibility_checks(status);
CREATE INDEX idx_eligibility_checks_created ON eligibility_checks(created_at);
CREATE INDEX idx_eligibility_checks_eligible ON eligibility_checks(is_eligible) WHERE is_eligible = true;
CREATE INDEX idx_eligibility_checks_cache ON eligibility_checks(cache_expires_at) WHERE cache_expires_at IS NOT NULL;

-- Trigger for updated_at
CREATE TRIGGER update_eligibility_checks_updated_at BEFORE UPDATE ON eligibility_checks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE eligibility_checks IS 'Eligibility verification requests and results (270/271 transactions)';
COMMENT ON COLUMN eligibility_checks.result_type IS 'Result classification: eligible, not_eligible, coverage_terminated, member_not_found, payer_error';

-- ============================================================================
-- Eligibility Benefits Table
-- ============================================================================
-- Stores parsed benefit information from 271 responses

CREATE TABLE IF NOT EXISTS eligibility_benefits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    check_id UUID NOT NULL REFERENCES eligibility_checks(id) ON DELETE CASCADE,

    -- Benefit identification
    service_type_code VARCHAR(10),
    service_type_description VARCHAR(255),

    -- Status from EB01
    status_code VARCHAR(5) NOT NULL,
    status_description VARCHAR(100),

    -- Coverage info
    coverage_level VARCHAR(10),                -- IND, FAM, etc.
    insurance_type VARCHAR(10),
    in_plan_network BOOLEAN,
    authorization_required BOOLEAN DEFAULT false,

    -- Amounts
    monetary_amount DECIMAL(12,2),
    percent DECIMAL(5,2),
    quantity DECIMAL(10,2),
    quantity_qualifier VARCHAR(10),

    -- Time period
    time_period VARCHAR(10),                   -- 22=Year, 24=Lifetime, etc.

    -- Additional info
    procedure_codes JSONB,
    diagnosis_codes JSONB,
    message TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_eligibility_benefits_check ON eligibility_benefits(check_id);
CREATE INDEX idx_eligibility_benefits_service ON eligibility_benefits(service_type_code);
CREATE INDEX idx_eligibility_benefits_status ON eligibility_benefits(status_code);

COMMENT ON TABLE eligibility_benefits IS 'Parsed benefit details from eligibility responses';
COMMENT ON COLUMN eligibility_benefits.status_code IS 'EB01 status code: 1=Active, 6=Inactive, A=Coinsurance, B=Copay, C=Deductible, etc.';

-- ============================================================================
-- Eligibility Dates Table
-- ============================================================================
-- Stores date information from 271 responses

CREATE TABLE IF NOT EXISTS eligibility_dates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    check_id UUID NOT NULL REFERENCES eligibility_checks(id) ON DELETE CASCADE,

    -- Date info
    qualifier VARCHAR(10) NOT NULL,            -- DTP01
    date_value DATE,
    date_range_start DATE,
    date_range_end DATE,
    description VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_eligibility_dates_check ON eligibility_dates(check_id);
CREATE INDEX idx_eligibility_dates_qualifier ON eligibility_dates(qualifier);

COMMENT ON TABLE eligibility_dates IS 'Date information from eligibility responses (DTP segments)';

-- ============================================================================
-- Eligibility Cache Table
-- ============================================================================
-- Stores cached eligibility results for performance

CREATE TABLE IF NOT EXISTS eligibility_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Cache key components
    member_id VARCHAR(50) NOT NULL,
    payer_id VARCHAR(50) NOT NULL,
    service_date DATE NOT NULL,
    cache_key VARCHAR(255) UNIQUE NOT NULL,

    -- Cached result
    is_eligible BOOLEAN NOT NULL,
    result_type VARCHAR(30),
    result_data JSONB NOT NULL,

    -- TTL
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_eligibility_cache_tenant ON eligibility_cache(tenant_id);
CREATE INDEX idx_eligibility_cache_key ON eligibility_cache(cache_key);
CREATE INDEX idx_eligibility_cache_expires ON eligibility_cache(expires_at);
CREATE INDEX idx_eligibility_cache_member_payer ON eligibility_cache(member_id, payer_id, service_date);

-- Trigger for updated_at
CREATE TRIGGER update_eligibility_cache_updated_at BEFORE UPDATE ON eligibility_cache
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE eligibility_cache IS 'Cached eligibility results for performance optimization';

-- ============================================================================
-- Payer Eligibility Configuration Table
-- ============================================================================
-- Stores payer-specific eligibility configuration

CREATE TABLE IF NOT EXISTS payer_eligibility_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Payer identification
    payer_id VARCHAR(50) NOT NULL,
    payer_name VARCHAR(255),

    -- Connection settings
    endpoint_url VARCHAR(500),
    connection_type VARCHAR(20) DEFAULT 'mock', -- 'mock', 'direct', 'clearinghouse'

    -- Credentials (encrypted)
    api_key_encrypted TEXT,
    username_encrypted TEXT,
    password_encrypted TEXT,

    -- Timeouts
    timeout_seconds INTEGER DEFAULT 30,
    retry_count INTEGER DEFAULT 3,

    -- Response handling
    supports_batch BOOLEAN DEFAULT false,
    batch_size_limit INTEGER DEFAULT 100,

    -- Status
    is_active BOOLEAN DEFAULT true,
    last_successful_check TIMESTAMP WITH TIME ZONE,
    last_failed_check TIMESTAMP WITH TIME ZONE,
    failure_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT uq_payer_eligibility_config UNIQUE(tenant_id, payer_id),
    CONSTRAINT chk_payer_connection_type CHECK (connection_type IN ('mock', 'direct', 'clearinghouse', 'api'))
);

-- Indexes
CREATE INDEX idx_payer_eligibility_config_tenant ON payer_eligibility_config(tenant_id);
CREATE INDEX idx_payer_eligibility_config_payer ON payer_eligibility_config(payer_id);
CREATE INDEX idx_payer_eligibility_config_active ON payer_eligibility_config(is_active) WHERE is_active = true;

-- Trigger for updated_at
CREATE TRIGGER update_payer_eligibility_config_updated_at BEFORE UPDATE ON payer_eligibility_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE payer_eligibility_config IS 'Per-payer eligibility verification configuration';
COMMENT ON COLUMN payer_eligibility_config.connection_type IS 'Connection type: mock (testing), direct (to payer), clearinghouse, api';

-- ============================================================================
-- Function: Clean Expired Eligibility Cache
-- ============================================================================
-- Removes expired cache entries

CREATE OR REPLACE FUNCTION clean_expired_eligibility_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM eligibility_cache
    WHERE expires_at < CURRENT_TIMESTAMP;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION clean_expired_eligibility_cache IS 'Clean expired eligibility cache entries. Should be called periodically.';

-- ============================================================================
-- Verification
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Migration V5 completed: Eligibility verification tables created';
    RAISE NOTICE 'Tables: eligibility_checks, eligibility_benefits, eligibility_dates, eligibility_cache, payer_eligibility_config';
    RAISE NOTICE 'Functions: clean_expired_eligibility_cache';
END $$;
