-- Flyway Migration: V4
-- Description: Add X12 EDI transaction tables
-- Author: System
-- Date: 2025-12-19
--
-- Source: Design Document 06_high_value_enhancements_design.md
-- Verified: 2025-12-19
--
-- This migration adds tables for:
-- - EDI transactions (837/835 tracking)
-- - EDI transaction claims (claim-level details)
-- - EDI transaction errors (error tracking)
-- - EDI interchange control numbers (unique control number tracking)

-- ============================================================================
-- EDI Transactions Table
-- ============================================================================
-- Stores EDI transaction metadata for 837/835 processing

CREATE TABLE IF NOT EXISTS edi_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Transaction identification
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    control_number VARCHAR(20) NOT NULL,
    functional_group_control VARCHAR(20),
    transaction_set_control VARCHAR(20),

    -- Transaction type and direction
    transaction_type VARCHAR(10) NOT NULL,      -- '837P', '837I', '835', '270', '271'
    direction VARCHAR(10) NOT NULL,             -- 'inbound', 'outbound'

    -- Processing status
    status VARCHAR(20) NOT NULL DEFAULT 'received',

    -- Sender/Receiver
    sender_id VARCHAR(50),
    sender_name VARCHAR(255),
    receiver_id VARCHAR(50),
    receiver_name VARCHAR(255),

    -- Content
    raw_content TEXT,                           -- Original X12 content
    file_size INTEGER,
    segment_count INTEGER,

    -- Processing metadata
    source VARCHAR(50) DEFAULT 'api',           -- 'api', 'sftp', 'edi_gateway'
    claims_count INTEGER DEFAULT 0,

    -- Error tracking
    has_errors BOOLEAN DEFAULT false,
    error_count INTEGER DEFAULT 0,

    -- Performance
    processing_time_ms INTEGER,

    -- Acknowledgment
    ack_status VARCHAR(20),                     -- 'accepted', 'rejected', 'pending'
    ack_transaction_id UUID,                    -- Reference to 999/997 acknowledgment
    ack_generated_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    received_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP WITH TIME ZONE,
    processed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_edi_transaction_type CHECK (transaction_type IN ('837P', '837I', '835', '270', '271', '276', '277', '997', '999')),
    CONSTRAINT chk_edi_direction CHECK (direction IN ('inbound', 'outbound')),
    CONSTRAINT chk_edi_status CHECK (status IN ('received', 'validating', 'validated', 'parsing', 'parsed', 'processing', 'completed', 'failed', 'rejected'))
);

-- Indexes
CREATE INDEX idx_edi_transactions_tenant ON edi_transactions(tenant_id);
CREATE INDEX idx_edi_transactions_type ON edi_transactions(transaction_type);
CREATE INDEX idx_edi_transactions_status ON edi_transactions(status);
CREATE INDEX idx_edi_transactions_direction ON edi_transactions(direction);
CREATE INDEX idx_edi_transactions_control ON edi_transactions(control_number);
CREATE INDEX idx_edi_transactions_received ON edi_transactions(received_at);
CREATE INDEX idx_edi_transactions_source ON edi_transactions(source);

-- Trigger for updated_at
CREATE TRIGGER update_edi_transactions_updated_at BEFORE UPDATE ON edi_transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE edi_transactions IS 'X12 EDI transaction tracking for 837/835 processing';
COMMENT ON COLUMN edi_transactions.transaction_type IS 'X12 transaction type: 837P, 837I, 835, 270, 271';
COMMENT ON COLUMN edi_transactions.direction IS 'Transaction direction: inbound (received), outbound (sent)';

-- ============================================================================
-- EDI Transaction Claims Table
-- ============================================================================
-- Links EDI transactions to individual claims

CREATE TABLE IF NOT EXISTS edi_transaction_claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id UUID NOT NULL REFERENCES edi_transactions(id) ON DELETE CASCADE,
    claim_id UUID REFERENCES claims(id),        -- Null until claim is created

    -- Claim identification from EDI
    patient_control_number VARCHAR(50),
    claim_frequency_code VARCHAR(5),

    -- Position in transaction
    claim_sequence INTEGER NOT NULL,            -- Order within transaction
    hl_id_number VARCHAR(20),                   -- Hierarchical level ID

    -- Claim data (parsed from EDI)
    claim_data JSONB NOT NULL,                  -- Full parsed claim data

    -- Processing status
    status VARCHAR(20) NOT NULL DEFAULT 'parsed',

    -- Validation
    validation_passed BOOLEAN DEFAULT true,
    validation_errors JSONB,

    -- Matching (for deduplication)
    matched_existing_claim_id UUID REFERENCES claims(id),
    match_confidence DECIMAL(3,2),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT uq_edi_transaction_claim_sequence UNIQUE(transaction_id, claim_sequence),
    CONSTRAINT chk_edi_claim_status CHECK (status IN ('parsed', 'validated', 'created', 'matched', 'rejected', 'error'))
);

-- Indexes
CREATE INDEX idx_edi_transaction_claims_transaction ON edi_transaction_claims(transaction_id);
CREATE INDEX idx_edi_transaction_claims_claim ON edi_transaction_claims(claim_id) WHERE claim_id IS NOT NULL;
CREATE INDEX idx_edi_transaction_claims_pcn ON edi_transaction_claims(patient_control_number);
CREATE INDEX idx_edi_transaction_claims_status ON edi_transaction_claims(status);

-- Trigger for updated_at
CREATE TRIGGER update_edi_transaction_claims_updated_at BEFORE UPDATE ON edi_transaction_claims
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE edi_transaction_claims IS 'Individual claims extracted from EDI transactions';
COMMENT ON COLUMN edi_transaction_claims.claim_data IS 'Full parsed claim data in JSON format';

-- ============================================================================
-- EDI Transaction Errors Table
-- ============================================================================
-- Stores detailed error information for EDI transactions

CREATE TABLE IF NOT EXISTS edi_transaction_errors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id UUID NOT NULL REFERENCES edi_transactions(id) ON DELETE CASCADE,
    transaction_claim_id UUID REFERENCES edi_transaction_claims(id) ON DELETE CASCADE,

    -- Error classification
    error_type VARCHAR(50) NOT NULL,            -- 'syntax', 'validation', 'business', 'system'
    error_code VARCHAR(20),                     -- X12 error code if applicable
    severity VARCHAR(20) NOT NULL DEFAULT 'error',

    -- Error location
    segment_id VARCHAR(10),                     -- Segment that caused error
    element_position INTEGER,                   -- Element within segment
    loop_id VARCHAR(10),
    line_number INTEGER,

    -- Error details
    message TEXT NOT NULL,
    details JSONB,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_edi_error_type CHECK (error_type IN ('syntax', 'validation', 'business', 'system')),
    CONSTRAINT chk_edi_error_severity CHECK (severity IN ('warning', 'error', 'fatal'))
);

-- Indexes
CREATE INDEX idx_edi_transaction_errors_transaction ON edi_transaction_errors(transaction_id);
CREATE INDEX idx_edi_transaction_errors_claim ON edi_transaction_errors(transaction_claim_id) WHERE transaction_claim_id IS NOT NULL;
CREATE INDEX idx_edi_transaction_errors_type ON edi_transaction_errors(error_type);
CREATE INDEX idx_edi_transaction_errors_code ON edi_transaction_errors(error_code) WHERE error_code IS NOT NULL;

COMMENT ON TABLE edi_transaction_errors IS 'Detailed error tracking for EDI transactions';
COMMENT ON COLUMN edi_transaction_errors.error_code IS 'X12 acknowledgment error code (e.g., 1, 2, 3)';

-- ============================================================================
-- EDI Remittances Table
-- ============================================================================
-- Stores generated 835 remittance advices

CREATE TABLE IF NOT EXISTS edi_remittances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id UUID NOT NULL REFERENCES edi_transactions(id) ON DELETE CASCADE,
    claim_id UUID NOT NULL REFERENCES claims(id),

    -- Control numbers
    control_number VARCHAR(20) NOT NULL,
    check_number VARCHAR(50),

    -- Payer/Payee
    payer_id VARCHAR(50) NOT NULL,
    payer_name VARCHAR(255),
    payee_npi VARCHAR(10),
    payee_name VARCHAR(255),

    -- Payment amounts
    total_charged DECIMAL(12,2) NOT NULL,
    total_allowed DECIMAL(12,2) NOT NULL,
    total_paid DECIMAL(12,2) NOT NULL,
    patient_responsibility DECIMAL(12,2) DEFAULT 0,

    -- Payment method
    payment_method VARCHAR(20),                 -- 'ACH', 'CHK', 'NON'
    payment_date DATE,

    -- Content
    raw_content TEXT,                           -- Generated X12 835 content

    -- Delivery status
    delivery_status VARCHAR(20) DEFAULT 'pending',
    delivered_at TIMESTAMP WITH TIME ZONE,
    delivery_method VARCHAR(20),                -- 'api', 'sftp', 'email'

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_edi_remittance_payment_method CHECK (payment_method IN ('ACH', 'CHK', 'NON', 'BOP')),
    CONSTRAINT chk_edi_remittance_delivery_status CHECK (delivery_status IN ('pending', 'sent', 'delivered', 'failed'))
);

-- Indexes
CREATE INDEX idx_edi_remittances_transaction ON edi_remittances(transaction_id);
CREATE INDEX idx_edi_remittances_claim ON edi_remittances(claim_id);
CREATE INDEX idx_edi_remittances_control ON edi_remittances(control_number);
CREATE INDEX idx_edi_remittances_check ON edi_remittances(check_number) WHERE check_number IS NOT NULL;
CREATE INDEX idx_edi_remittances_date ON edi_remittances(payment_date);
CREATE INDEX idx_edi_remittances_status ON edi_remittances(delivery_status);

-- Trigger for updated_at
CREATE TRIGGER update_edi_remittances_updated_at BEFORE UPDATE ON edi_remittances
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE edi_remittances IS 'Generated X12 835 remittance advices';
COMMENT ON COLUMN edi_remittances.payment_method IS 'Payment method: ACH, CHK (check), NON (non-payment), BOP';

-- ============================================================================
-- EDI Control Numbers Table
-- ============================================================================
-- Tracks interchange control numbers for uniqueness

CREATE TABLE IF NOT EXISTS edi_control_numbers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Control number tracking
    control_type VARCHAR(20) NOT NULL,          -- 'ISA', 'GS', 'ST'
    direction VARCHAR(10) NOT NULL,
    partner_id VARCHAR(50),                     -- Trading partner ID

    -- Counter
    last_number BIGINT NOT NULL DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT uq_edi_control_numbers UNIQUE(tenant_id, control_type, direction, partner_id),
    CONSTRAINT chk_edi_control_type CHECK (control_type IN ('ISA', 'GS', 'ST')),
    CONSTRAINT chk_edi_control_direction CHECK (direction IN ('inbound', 'outbound'))
);

-- Trigger for updated_at
CREATE TRIGGER update_edi_control_numbers_updated_at BEFORE UPDATE ON edi_control_numbers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE edi_control_numbers IS 'Control number sequence tracking for unique ISA/GS/ST control numbers';

-- ============================================================================
-- Function: Get Next Control Number
-- ============================================================================
-- Atomically increments and returns the next control number

CREATE OR REPLACE FUNCTION get_next_edi_control_number(
    p_tenant_id UUID,
    p_control_type VARCHAR(20),
    p_direction VARCHAR(10),
    p_partner_id VARCHAR(50) DEFAULT NULL
) RETURNS BIGINT AS $$
DECLARE
    v_next_number BIGINT;
BEGIN
    -- Insert or update the control number record
    INSERT INTO edi_control_numbers (tenant_id, control_type, direction, partner_id, last_number)
    VALUES (p_tenant_id, p_control_type, p_direction, COALESCE(p_partner_id, ''), 1)
    ON CONFLICT (tenant_id, control_type, direction, partner_id)
    DO UPDATE SET
        last_number = edi_control_numbers.last_number + 1,
        updated_at = CURRENT_TIMESTAMP
    RETURNING last_number INTO v_next_number;

    RETURN v_next_number;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_next_edi_control_number IS 'Atomically get next EDI control number for ISA/GS/ST segments';

-- ============================================================================
-- EDI Trading Partners Table
-- ============================================================================
-- Configuration for EDI trading partners

CREATE TABLE IF NOT EXISTS edi_trading_partners (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Partner identification
    partner_id VARCHAR(50) NOT NULL,
    partner_name VARCHAR(255) NOT NULL,
    partner_type VARCHAR(20) NOT NULL,          -- 'payer', 'provider', 'clearinghouse'

    -- ISA identifiers
    isa_qualifier VARCHAR(2) NOT NULL DEFAULT 'ZZ',
    isa_id VARCHAR(15) NOT NULL,

    -- GS identifiers
    gs_id VARCHAR(15) NOT NULL,

    -- Supported transactions
    supported_transactions JSONB DEFAULT '["837P", "835"]',

    -- Connection settings
    connection_type VARCHAR(20) DEFAULT 'sftp', -- 'sftp', 'as2', 'api'
    connection_settings JSONB,

    -- Status
    is_active BOOLEAN DEFAULT true,
    is_production BOOLEAN DEFAULT false,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT uq_edi_trading_partner UNIQUE(tenant_id, partner_id),
    CONSTRAINT chk_edi_partner_type CHECK (partner_type IN ('payer', 'provider', 'clearinghouse', 'vendor')),
    CONSTRAINT chk_edi_connection_type CHECK (connection_type IN ('sftp', 'as2', 'api', 'manual'))
);

-- Indexes
CREATE INDEX idx_edi_trading_partners_tenant ON edi_trading_partners(tenant_id);
CREATE INDEX idx_edi_trading_partners_active ON edi_trading_partners(is_active) WHERE is_active = true;
CREATE INDEX idx_edi_trading_partners_type ON edi_trading_partners(partner_type);

-- Trigger for updated_at
CREATE TRIGGER update_edi_trading_partners_updated_at BEFORE UPDATE ON edi_trading_partners
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE edi_trading_partners IS 'EDI trading partner configuration for X12 transactions';
COMMENT ON COLUMN edi_trading_partners.isa_qualifier IS 'ISA05/ISA07 qualifier (e.g., ZZ, 01, 30)';
COMMENT ON COLUMN edi_trading_partners.isa_id IS 'ISA06/ISA08 sender/receiver ID';

-- ============================================================================
-- Verification
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Migration V4 completed: EDI tables created';
    RAISE NOTICE 'Tables: edi_transactions, edi_transaction_claims, edi_transaction_errors, edi_remittances, edi_control_numbers, edi_trading_partners';
    RAISE NOTICE 'Functions: get_next_edi_control_number';
END $$;
