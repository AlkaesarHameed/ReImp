-- Python Project Starter - Database Initialization Script
-- PostgreSQL 17 + TimescaleDB + Extensions
-- Version: 1.0 (Baseline Schema)
-- Source: PostgreSQL Extensions Documentation
-- https://www.postgresql.org/docs/17/contrib.html
-- Verified: 2025-11-14
--
-- NOTE: This is V1 (baseline). Incremental changes go in database/migrations/
-- Pattern: Init folder for baseline, Flyway for V2+ migrations

-- ============================================================================
-- Enable Required Extensions
-- ============================================================================

-- TimescaleDB - Time-series database
-- Source: https://docs.timescale.com/
-- Verified: 2025-11-14
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- pgvector - Vector similarity search for embeddings
-- Source: https://github.com/pgvector/pgvector
-- Supports: OpenAI embeddings, Ollama embeddings, etc.
-- Verified: 2025-11-14
CREATE EXTENSION IF NOT EXISTS vector;

-- PostGIS - Geospatial data support
-- Source: https://postgis.net/documentation/
-- Verified: 2025-11-14
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- UUID generation
-- Source: https://www.postgresql.org/docs/17/uuid-ossp.html
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Cryptographic functions
-- Source: https://www.postgresql.org/docs/17/pgcrypto.html
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Full-text search
-- Source: https://www.postgresql.org/docs/17/pgtrgm.html
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Unaccent for text normalization
CREATE EXTENSION IF NOT EXISTS unaccent;

-- ============================================================================
-- Create Schemas (Optional - for organization)
-- ============================================================================
-- Uncomment if you want to organize tables by schema
-- CREATE SCHEMA IF NOT EXISTS auth;      -- Authentication tables
-- CREATE SCHEMA IF NOT EXISTS app;       -- Application tables
-- CREATE SCHEMA IF NOT EXISTS analytics; -- Analytics/metrics tables

-- ============================================================================
-- Core Tables
-- ============================================================================

-- Users Table (Authentication & Profile)
-- JWT-based auth with OAuth2 support
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,  -- bcrypt hash
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    is_superuser BOOLEAN DEFAULT false,

    -- OAuth2 fields
    oauth_provider VARCHAR(50),  -- google, github, etc.
    oauth_id VARCHAR(255),       -- Provider's user ID
    picture_url TEXT,            -- Profile picture

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT chk_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT chk_username_length CHECK (char_length(username) >= 3),
    CONSTRAINT chk_oauth_consistency CHECK (
        (oauth_provider IS NULL AND oauth_id IS NULL) OR
        (oauth_provider IS NOT NULL AND oauth_id IS NOT NULL)
    )
);

-- Index for faster lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_id) WHERE oauth_provider IS NOT NULL;

-- Refresh Tokens Table (JWT)
-- Stores refresh tokens for token rotation
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,  -- Hashed refresh token
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_not_expired CHECK (expires_at > created_at)
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_expires ON refresh_tokens(expires_at) WHERE revoked_at IS NULL;

-- Documents Table (Example with Vector Embeddings)
-- Demonstrates pgvector for semantic search
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,

    -- Vector embedding for semantic search
    -- Dimension: 1536 (OpenAI text-embedding-3-small / Ollama qwen3-embedding)
    -- Source: https://github.com/pgvector/pgvector#getting-started
    embedding vector(1536),

    -- Metadata
    file_path TEXT,  -- MinIO object path
    mime_type VARCHAR(100),
    file_size BIGINT,

    -- Full-text search
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))
    ) STORED,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_documents_user ON documents(user_id);
CREATE INDEX idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_documents_search ON documents USING gin(search_vector);
CREATE INDEX idx_documents_created ON documents(created_at DESC);

-- Geospatial Example Table (PostGIS)
-- Demonstrates location-based features
CREATE TABLE IF NOT EXISTS locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    address TEXT,

    -- Geospatial point (longitude, latitude)
    -- Source: https://postgis.net/docs/geometry.html
    coordinates geography(POINT, 4326),

    -- Metadata
    place_type VARCHAR(50),  -- office, home, etc.
    is_public BOOLEAN DEFAULT false,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Spatial index for proximity queries
CREATE INDEX idx_locations_coordinates ON locations USING GIST(coordinates);
CREATE INDEX idx_locations_user ON locations(user_id);

-- Time-Series Example Table (TimescaleDB)
-- Demonstrates metrics/events tracking
CREATE TABLE IF NOT EXISTS metrics (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,

    -- Dimensions for grouping
    tags JSONB DEFAULT '{}',

    PRIMARY KEY (time, user_id, metric_name)
);

-- Convert to hypertable (TimescaleDB feature)
-- Source: https://docs.timescale.com/api/latest/hypertable/create_hypertable/
SELECT create_hypertable('metrics', 'time', if_not_exists => TRUE);

-- Indexes for time-series queries
CREATE INDEX idx_metrics_user_time ON metrics(user_id, time DESC);
CREATE INDEX idx_metrics_name_time ON metrics(metric_name, time DESC);
CREATE INDEX idx_metrics_tags ON metrics USING gin(tags);

-- Background Tasks Table (Celery/Task Tracking)
-- Tracks async job status
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    task_name VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) UNIQUE,  -- Celery task ID
    status VARCHAR(50) DEFAULT 'pending',  -- pending, running, completed, failed

    -- Task details
    args JSONB,
    kwargs JSONB,
    result JSONB,
    error TEXT,

    -- Progress tracking
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX idx_tasks_user ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status) WHERE status IN ('pending', 'running');
CREATE INDEX idx_tasks_created ON tasks(created_at DESC);

-- ============================================================================
-- Functions & Triggers
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables with updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_locations_updated_at BEFORE UPDATE ON locations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Initial Data (Optional)
-- ============================================================================

-- Create default admin user (password: admin123 - CHANGE IN PRODUCTION!)
-- Password hash generated with: bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt())
INSERT INTO users (
    email,
    username,
    hashed_password,
    full_name,
    is_active,
    is_verified,
    is_superuser
) VALUES (
    'admin@example.com',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lKnBx5XKcVKe',  -- admin123
    'System Administrator',
    true,
    true,
    true
) ON CONFLICT (email) DO NOTHING;

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE users IS 'User accounts with JWT authentication and OAuth2 support';
COMMENT ON TABLE refresh_tokens IS 'JWT refresh tokens for secure token rotation';
COMMENT ON TABLE documents IS 'Documents with vector embeddings for semantic search (pgvector)';
COMMENT ON TABLE locations IS 'Geospatial data with PostGIS support';
COMMENT ON TABLE metrics IS 'Time-series metrics using TimescaleDB hypertables';
COMMENT ON TABLE tasks IS 'Background task tracking for Celery jobs';

COMMENT ON COLUMN documents.embedding IS 'Vector embedding (1536 dimensions) for semantic similarity search';
COMMENT ON COLUMN locations.coordinates IS 'PostGIS geography point (longitude, latitude) in WGS84';
COMMENT ON COLUMN metrics.tags IS 'JSONB tags for flexible metric dimensions';

-- ============================================================================
-- Verification
-- ============================================================================

-- Verify extensions are loaded
DO $$
BEGIN
    RAISE NOTICE 'Installed Extensions:';
    RAISE NOTICE '  - TimescaleDB: %', (SELECT extversion FROM pg_extension WHERE extname = 'timescaledb');
    RAISE NOTICE '  - pgvector: %', (SELECT extversion FROM pg_extension WHERE extname = 'vector');
    RAISE NOTICE '  - PostGIS: %', (SELECT extversion FROM pg_extension WHERE extname = 'postgis');
END $$;

-- Show created tables
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
