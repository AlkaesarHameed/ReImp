# ADR-003: Use Flyway for Database Migrations

**Status**: Accepted

**Date**: 2025-11-14

**Deciders**: Project Lead

---

## Context

Database schema evolution requires a migration system to:

- Track schema changes over time
- Apply migrations consistently across environments
- Support rollback for failed migrations
- Handle complex schema transformations
- Work with PostgreSQL extensions (TimescaleDB, pgvector, PostGIS)
- Be language-agnostic for flexibility

Python-based tools like Alembic are common but have limitations for polyglot teams and complex PostgreSQL features.

## Decision

We will use **Flyway** for database migrations instead of Python-native tools like Alembic.

**Key reasons:**

1. **Pure SQL Migrations**: Write migrations in native PostgreSQL SQL (no ORM abstraction)
2. **PostgreSQL Extension Support**: Direct support for TimescaleDB, pgvector, PostGIS
3. **Language Independence**: Works regardless of application language
4. **Version Control**: Simple, ordered migration files (V1, V2, V3...)
5. **Production-Ready**: Battle-tested in enterprise environments
6. **Rollback Support**: SQL-based undo migrations
7. **Idempotency**: Checksums prevent partial application of migrations

## Consequences

### Positive

- **Direct PostgreSQL Control**: Full access to PostgreSQL features and extensions
- **No ORM Coupling**: Migrations independent of SQLAlchemy model changes
- **Polyglot-Friendly**: Can be used from any language (Java, Python, Node.js)
- **Transparency**: Plain SQL is easy to review and understand
- **Extension Support**: Native support for TimescaleDB hypertables, pgvector indexes, PostGIS geometries
- **Enterprise Features**: Callbacks, repeatable migrations, schema validation
- **Docker Integration**: Easy to run migrations in containers

### Negative

- **No Auto-Generation**: Must write migrations manually (no `alembic autogenerate`)
- **Java Dependency**: Requires JVM (though Docker image mitigates this)
- **Learning Curve**: Developers must know SQL (though this is arguably a plus)
- **Less Python-Native**: Doesn't integrate directly with SQLAlchemy models

### Neutral

- **File Organization**: Migration files in `database/migrations/` (not Python code)
- **Execution**: Migrations run via Flyway CLI/Docker, not Python code

## Alternatives Considered

### Alternative 1: Alembic

**Description**: Python-native migration tool, part of SQLAlchemy ecosystem

**Pros**:

- Tight SQLAlchemy integration
- Auto-generation from model changes (`alembic revision --autogenerate`)
- Python-native (no JVM required)
- Popular in Python community

**Cons**:

- **Limited Extension Support**: Struggles with TimescaleDB, pgvector, PostGIS
- **ORM Coupling**: Migrations tied to SQLAlchemy models
- **Complexity**: Auto-generation can miss or incorrectly detect changes
- **Review Burden**: Auto-generated migrations require careful manual review
- **Language Lock-In**: Can only be used from Python

**Why rejected**: Inadequate support for PostgreSQL extensions critical to this project

### Alternative 2: Django Migrations

**Description**: Django's built-in migration system

**Pros**:

- Integrated with Django ORM
- Auto-generation from model changes
- Well-tested and mature

**Cons**:

- **Django Dependency**: Requires Django framework (overkill for FastAPI)
- **ORM Coupling**: Tied to Django ORM
- **Limited PostgreSQL Support**: Not designed for advanced PostgreSQL features

**Why rejected**: Not applicable (not using Django)

### Alternative 3: Liquibase

**Description**: Similar to Flyway, supports XML/YAML/JSON/SQL migrations

**Pros**:

- Database-agnostic (supports many databases)
- Multiple format support
- Enterprise features

**Cons**:

- **Complexity**: XML/YAML adds abstraction overhead
- **Overkill**: Multi-database support not needed (PostgreSQL-only project)
- **Verbosity**: XML/YAML more verbose than raw SQL

**Why rejected**: Complexity and multi-database features unnecessary for PostgreSQL-only project

## Implementation Notes

**Current Implementation:**

**Directory Structure:**

```
database/
├── init/
│   └── V1__initial_schema.sql          # Initial schema
└── migrations/
    ├── V2__add_user_last_login.sql     # Example migration
    └── V3__add_timescale_features.sql  # Future migrations
```

**Migration File Naming Convention:**

```
V{version}__{description}.sql

Examples:
V1__initial_schema.sql
V2__add_user_last_login.sql
V3__add_pgvector_extension.sql
```

**Running Migrations:**

```bash
# Via Make command
make migrations-upgrade    # Apply all pending migrations
make migrations-history    # View migration history

# Via Docker directly
docker run --rm -v $(pwd)/database:/flyway/sql \
  flyway/flyway:11 \
  -url=jdbc:postgresql://localhost:5432/starter_db \
  -user=starter_user \
  -password=password \
  migrate
```

**Creating New Migration:**

1. Create new SQL file: `database/migrations/V{next}__description.sql`
2. Write forward migration SQL
3. Test locally: `make migrations-upgrade`
4. Commit migration file to git
5. CI/CD applies migration automatically

**Example Migration (TimescaleDB Hypertable):**

```sql
-- V3__create_metrics_hypertable.sql
CREATE TABLE metrics (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    metric_name TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('metrics', 'timestamp');

-- Create indexes
CREATE INDEX idx_metrics_name_time ON metrics (metric_name, timestamp DESC);

COMMENT ON TABLE metrics IS 'Time-series metrics using TimescaleDB';
```

**Rollback Strategy:**

Flyway supports undo migrations (requires Teams edition) or manual rollback:

```sql
-- V3__create_metrics_hypertable.sql (forward)
CREATE TABLE metrics (...);

-- U3__create_metrics_hypertable.sql (undo)
DROP TABLE IF EXISTS metrics;
```

For this project: **Manual rollback SQL scripts** stored alongside migrations.

**Key Rules:**

- ✅ **NEVER modify applied migrations** (checksums will fail)
- ✅ Write idempotent migrations when possible (`CREATE IF NOT EXISTS`)
- ✅ Test migrations locally before committing
- ✅ Keep migrations small and focused (one logical change per file)
- ✅ Document complex migrations with SQL comments
- ❌ **NEVER skip version numbers** (V1, V2, V3... sequential)
- ❌ **NEVER reuse version numbers**

**Monitoring:**

- `flyway_schema_history` table tracks all applied migrations
- Alert on migration failures in CI/CD
- Monitor migration execution time (long-running migrations need investigation)

## References

- [Flyway Documentation](https://flywaydb.org/documentation/)
- [Flyway PostgreSQL Support](https://flywaydb.org/documentation/database/postgresql)
- [TimescaleDB Migration Best Practices](https://docs.timescale.com/use-timescale/latest/schema-management/)
- [Why We Use Flyway Over Alembic (Engineering Blog)](https://medium.com/@mariusgheorghies/flyway-vs-alembic-database-migration-tools-comparison)

---

## Revision History

| Date       | Author       | Changes                               |
| ---------- | ------------ | ------------------------------------- |
| 2025-11-14 | Project Lead | Initial ADR documenting Flyway choice |
