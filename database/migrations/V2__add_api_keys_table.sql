-- Flyway Migration: V2
-- Description: Add API keys table for user authentication
-- Author: System
-- Date: 2025-11-14
--
-- Naming Convention: V{version}__{description}.sql
-- Source: https://flywaydb.org/documentation/concepts/migrations#naming
-- Verified: 2025-11-14
--
-- This is an example migration showing how to add new tables
-- after the baseline schema (V1) has been initialized.

-- ============================================================================
-- API Keys Table
-- ============================================================================
-- Allows users to generate API keys for programmatic access
-- Supports key rotation and scoped permissions

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Key details
    key_name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,  -- Hashed API key
    key_prefix VARCHAR(10) NOT NULL,        -- First 8 chars for identification

    -- Permissions & Scopes
    scopes TEXT[] DEFAULT '{}',             -- Array of permission scopes
    is_active BOOLEAN DEFAULT true,

    -- Usage tracking
    last_used_at TIMESTAMP WITH TIME ZONE,
    usage_count BIGINT DEFAULT 0,

    -- Expiration
    expires_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_key_name_length CHECK (char_length(key_name) >= 3),
    CONSTRAINT chk_key_prefix_length CHECK (char_length(key_prefix) = 8),
    CONSTRAINT chk_expires_future CHECK (expires_at IS NULL OR expires_at > created_at)
);

-- Indexes for performance
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash) WHERE is_active = true;
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX idx_api_keys_expires ON api_keys(expires_at) WHERE expires_at IS NOT NULL AND is_active = true;

-- Trigger for updated_at
CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE api_keys IS 'User-generated API keys for programmatic access';
COMMENT ON COLUMN api_keys.key_hash IS 'Bcrypt hash of the API key (never store plain text)';
COMMENT ON COLUMN api_keys.key_prefix IS 'First 8 characters of key for user identification';
COMMENT ON COLUMN api_keys.scopes IS 'Array of permission scopes (e.g., read:users, write:documents)';

-- ============================================================================
-- Verification
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Migration V2 completed: api_keys table created';
END $$;
