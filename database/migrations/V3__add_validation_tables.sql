-- Flyway Migration: V3
-- Description: Add validation engine tables
-- Author: System
-- Date: 2025-12-19
--
-- Source: Design Document 04_validation_engine_comprehensive_design.md
-- Verified: 2025-12-19
--
-- This migration adds tables for:
-- - LLM settings (per-tenant, per-task configuration)
-- - Validation results (historical validation records)
-- - Claim rejections (with detailed reasoning)
-- - Rejection evidence (supporting evidence for rejections)
-- - LLM usage logs (token tracking and cost estimation)

-- ============================================================================
-- LLM Settings Table
-- ============================================================================
-- Stores per-tenant, per-task LLM configuration
-- Supports multiple providers with fallback

CREATE TABLE IF NOT EXISTS llm_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Task configuration
    task_type VARCHAR(50) NOT NULL,  -- 'extraction', 'validation', 'necessity'

    -- Primary provider configuration
    provider VARCHAR(50) NOT NULL,   -- 'azure', 'openai', 'anthropic', 'ollama'
    model_name VARCHAR(100) NOT NULL,
    api_endpoint VARCHAR(500),

    -- Model parameters
    temperature DECIMAL(3,2) DEFAULT 0.1,
    max_tokens INTEGER DEFAULT 4096,

    -- Fallback configuration
    fallback_provider VARCHAR(50),
    fallback_model VARCHAR(100),

    -- Rate limiting
    rate_limit_rpm INTEGER DEFAULT 60,
    rate_limit_tpm INTEGER DEFAULT 100000,

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT uq_llm_settings_tenant_task UNIQUE(tenant_id, task_type),
    CONSTRAINT chk_llm_settings_provider CHECK (provider IN ('azure', 'openai', 'anthropic', 'ollama', 'vllm')),
    CONSTRAINT chk_llm_settings_task CHECK (task_type IN ('extraction', 'validation', 'necessity', 'fwa'))
);

-- Indexes
CREATE INDEX idx_llm_settings_tenant ON llm_settings(tenant_id);
CREATE INDEX idx_llm_settings_active ON llm_settings(is_active) WHERE is_active = true;

-- Trigger for updated_at
CREATE TRIGGER update_llm_settings_updated_at BEFORE UPDATE ON llm_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE llm_settings IS 'Per-tenant LLM configuration for validation tasks';
COMMENT ON COLUMN llm_settings.task_type IS 'Type of task: extraction, validation, necessity, fwa';
COMMENT ON COLUMN llm_settings.provider IS 'LLM provider: azure, openai, anthropic, ollama, vllm';

-- ============================================================================
-- Validation Results Table
-- ============================================================================
-- Stores historical validation results for audit and analysis

CREATE TABLE IF NOT EXISTS validation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,

    -- Rule identification
    rule_id VARCHAR(20) NOT NULL,    -- 'rule_1', 'rule_2', etc.
    rule_name VARCHAR(100) NOT NULL,

    -- Validation outcome
    status VARCHAR(20) NOT NULL,     -- 'passed', 'failed', 'warning', 'skipped'
    confidence DECIMAL(3,2),

    -- Details (JSONB for flexible structure)
    details JSONB,
    evidence JSONB,

    -- Performance
    execution_time_ms INTEGER,

    -- Metadata
    validated_by VARCHAR(50),        -- 'system', 'llm:gpt-4', etc.

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_validation_status CHECK (status IN ('passed', 'failed', 'warning', 'skipped', 'error'))
);

-- Indexes
CREATE INDEX idx_validation_results_claim ON validation_results(claim_id);
CREATE INDEX idx_validation_results_rule ON validation_results(rule_id);
CREATE INDEX idx_validation_results_status ON validation_results(status);
CREATE INDEX idx_validation_results_created ON validation_results(created_at);

COMMENT ON TABLE validation_results IS 'Historical validation results for claims';
COMMENT ON COLUMN validation_results.rule_id IS 'Validation rule identifier (rule_1 through rule_13)';

-- ============================================================================
-- Claim Rejections Table
-- ============================================================================
-- Stores rejection decisions with detailed reasoning

CREATE TABLE IF NOT EXISTS claim_rejections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,

    -- Rejection identification
    rejection_id VARCHAR(50) UNIQUE NOT NULL,
    rejection_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Classification
    category VARCHAR(50) NOT NULL,   -- 'fraud', 'coding', 'documentation', 'coverage', 'eligibility'
    subcategory VARCHAR(50),

    -- Risk assessment
    risk_score DECIMAL(3,2),
    risk_level VARCHAR(20),          -- 'low', 'medium', 'high', 'critical'

    -- Reasoning
    summary TEXT NOT NULL,
    reasoning JSONB NOT NULL,        -- Structured reasoning with evidence

    -- Triggered rules
    triggered_rules JSONB,           -- Array of rule_ids that triggered

    -- Appeal information
    appeal_deadline TIMESTAMP WITH TIME ZONE,
    appeal_status VARCHAR(20) DEFAULT 'none',
    appeal_notes TEXT,

    -- Audit
    created_by UUID REFERENCES users(id),
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_rejection_category CHECK (category IN ('fraud', 'coding', 'documentation', 'coverage', 'eligibility', 'medical_necessity', 'other')),
    CONSTRAINT chk_rejection_appeal_status CHECK (appeal_status IN ('none', 'pending', 'under_review', 'approved', 'denied'))
);

-- Indexes
CREATE INDEX idx_claim_rejections_claim ON claim_rejections(claim_id);
CREATE INDEX idx_claim_rejections_category ON claim_rejections(category);
CREATE INDEX idx_claim_rejections_date ON claim_rejections(rejection_date);
CREATE INDEX idx_claim_rejections_risk ON claim_rejections(risk_level);
CREATE INDEX idx_claim_rejections_appeal ON claim_rejections(appeal_status) WHERE appeal_status != 'none';

-- Trigger for updated_at
CREATE TRIGGER update_claim_rejections_updated_at BEFORE UPDATE ON claim_rejections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE claim_rejections IS 'Claim rejection decisions with detailed reasoning';
COMMENT ON COLUMN claim_rejections.reasoning IS 'Structured JSON with evidence and reasoning chain';

-- ============================================================================
-- Rejection Evidence Table
-- ============================================================================
-- Stores individual pieces of evidence for rejections

CREATE TABLE IF NOT EXISTS rejection_evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rejection_id UUID NOT NULL REFERENCES claim_rejections(id) ON DELETE CASCADE,

    -- Evidence classification
    signal_type VARCHAR(50) NOT NULL,  -- 'metadata_mismatch', 'code_conflict', etc.
    severity VARCHAR(20) NOT NULL,     -- 'low', 'medium', 'high', 'critical'
    confidence DECIMAL(3,2) NOT NULL,

    -- Evidence details
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    details JSONB NOT NULL,

    -- Source reference
    document_id UUID,
    document_name VARCHAR(255),
    page_number INTEGER,
    reference_source VARCHAR(255),     -- 'CMS', 'NCCI', 'LCD/NCD', etc.

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_evidence_severity CHECK (severity IN ('low', 'medium', 'high', 'critical'))
);

-- Indexes
CREATE INDEX idx_rejection_evidence_rejection ON rejection_evidence(rejection_id);
CREATE INDEX idx_rejection_evidence_type ON rejection_evidence(signal_type);
CREATE INDEX idx_rejection_evidence_severity ON rejection_evidence(severity);

COMMENT ON TABLE rejection_evidence IS 'Individual evidence items supporting claim rejections';
COMMENT ON COLUMN rejection_evidence.signal_type IS 'Type of fraud/validation signal detected';

-- ============================================================================
-- LLM Usage Logs Table
-- ============================================================================
-- Tracks LLM usage for cost estimation and monitoring

CREATE TABLE IF NOT EXISTS llm_usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Request context
    task_type VARCHAR(50) NOT NULL,
    claim_id UUID REFERENCES claims(id),

    -- Provider/Model
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,

    -- Token counts
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,

    -- Cost estimation (USD)
    estimated_cost_usd DECIMAL(10,6) DEFAULT 0,

    -- Performance
    latency_ms INTEGER,
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_llm_usage_tenant ON llm_usage_logs(tenant_id);
CREATE INDEX idx_llm_usage_created ON llm_usage_logs(created_at);
CREATE INDEX idx_llm_usage_claim ON llm_usage_logs(claim_id) WHERE claim_id IS NOT NULL;
CREATE INDEX idx_llm_usage_task ON llm_usage_logs(task_type);

-- Partitioning hint (for future implementation)
COMMENT ON TABLE llm_usage_logs IS 'LLM usage tracking for cost estimation. Consider partitioning by created_at for large deployments.';

-- ============================================================================
-- Validation Cache Table (Optional)
-- ============================================================================
-- For persistent caching of validation results across restarts

CREATE TABLE IF NOT EXISTS validation_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    cache_value JSONB NOT NULL,

    -- TTL
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for expiration cleanup
CREATE INDEX idx_validation_cache_expires ON validation_cache(expires_at);

-- Trigger for updated_at
CREATE TRIGGER update_validation_cache_updated_at BEFORE UPDATE ON validation_cache
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE validation_cache IS 'Persistent cache for validation results';

-- ============================================================================
-- Verification
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Migration V3 completed: Validation engine tables created';
    RAISE NOTICE 'Tables: llm_settings, validation_results, claim_rejections, rejection_evidence, llm_usage_logs, validation_cache';
END $$;
