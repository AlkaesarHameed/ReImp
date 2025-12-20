# ADR-004: Use PostgreSQL + TimescaleDB Stack

**Status**: Accepted

**Date**: 2025-11-14

**Deciders**: Project Lead

---

## Context

This project starter needs a robust database solution supporting:

- **OLTP Workloads**: Traditional relational data (users, sessions, transactions)
- **Time-Series Data**: Metrics, logs, analytics with efficient time-based queries
- **Vector Search**: AI/ML embeddings for semantic search and RAG applications
- **Geospatial Data**: Location-based queries and spatial indexing
- **Scalability**: Handle growth from MVP to production scale
- **Reliability**: ACID compliance, strong consistency guarantees

The database must support modern application patterns including AI/ML integration while maintaining traditional relational database strengths.

## Decision

We will use **PostgreSQL 17** with the following extensions:

1. **TimescaleDB 2.11+** - Time-series data optimization
2. **pgvector 0.5+** - Vector similarity search for AI/ML embeddings
3. **PostGIS 3.4+** - Geospatial data and queries

**Key reasons:**

1. **Single Database System**: All data types in one ACID-compliant system
2. **Best-in-Class Extensions**: Industry-leading extensions for specialized workloads
3. **Operational Simplicity**: One database to monitor, backup, and scale
4. **Cost Efficiency**: Open-source with no licensing fees
5. **Developer Experience**: SQL familiarity, mature tooling, excellent documentation
6. **Production-Proven**: Battle-tested in enterprises (Uber, Netflix, Instagram)
7. **Future-Proof**: Active development, strong community, modern features

## Consequences

### Positive

**PostgreSQL Core:**

- **ACID Compliance**: Strong consistency and reliability guarantees
- **Rich SQL Support**: CTEs, window functions, JSON/JSONB, full-text search
- **Mature Ecosystem**: Extensive tools, libraries, and community knowledge
- **Performance**: Excellent query optimizer and indexing strategies
- **Extensibility**: Plugin architecture for domain-specific functionality

**TimescaleDB:**

- **Time-Series Performance**: 10-100x faster than vanilla PostgreSQL for time-series
- **Automatic Partitioning**: Hypertables automatically partition by time
- **Data Retention**: Easy TTL policies with `drop_chunks()`
- **Compression**: Built-in columnar compression for old data (10x-20x space savings)
- **Continuous Aggregates**: Materialized views automatically refreshed

**pgvector:**

- **Semantic Search**: Enable RAG (Retrieval Augmented Generation) for LLMs
- **Similarity Search**: Find similar items using embeddings
- **Index Support**: HNSW and IVFFlat indexes for fast approximate nearest neighbor
- **Native Integration**: No external vector database needed

**PostGIS:**

- **Geospatial Queries**: Distance, containment, intersection queries
- **Spatial Indexing**: R-tree indexes for fast spatial lookups
- **Standards Compliance**: OGC standards support
- **Rich Functions**: 500+ spatial functions

### Negative

- **Resource Usage**: Extensions increase memory and storage requirements
- **Complexity**: More features to understand and configure
- **Extension Updates**: Must coordinate extension upgrades with PostgreSQL upgrades
- **Vertical Scaling Limits**: Single-node limits (mitigated by read replicas)

### Neutral

- **Not Multi-Model**: Still primarily relational (not graph, document-native)
- **Extension Coupling**: Project relies on specific PostgreSQL extensions

## Alternatives Considered

### Alternative 1: Separate Specialized Databases

**Description**: Use separate databases for each workload

- PostgreSQL for OLTP
- InfluxDB/Prometheus for time-series
- Pinecone/Weaviate for vectors
- MongoDB for documents

**Pros**:

- Best-of-breed for each workload
- Horizontal scaling per service

**Cons**:

- **Operational Complexity**: 4+ databases to manage, monitor, backup
- **Data Consistency**: Cross-database transactions impossible
- **Cost**: Multiple databases = higher infrastructure cost
- **Development Overhead**: Multiple clients, query languages, data models
- **Network Overhead**: Cross-database joins via application layer

**Why rejected**: Operational complexity outweighs benefits for most applications

### Alternative 2: MongoDB

**Description**: Document database with time-series and vector search features

**Pros**:

- Schema flexibility
- Native JSON support
- Horizontal sharding built-in

**Cons**:

- **Weaker Consistency**: Eventually consistent by default
- **Less Mature Extensions**: Time-series and vector features newer than PostgreSQL
- **SQL Limitations**: Less powerful query language than PostgreSQL
- **Ecosystem**: Smaller ecosystem than PostgreSQL

**Why rejected**: ACID compliance and SQL power more valuable than schema flexibility

### Alternative 3: MySQL

**Description**: Popular open-source relational database

**Pros**:

- Wide adoption
- Good performance for read-heavy workloads
- Mature replication

**Cons**:

- **Limited Extensions**: No equivalent to TimescaleDB, pgvector
- **Weaker SQL**: Less advanced SQL features than PostgreSQL
- **JSON Support**: Inferior to PostgreSQL's JSONB
- **Less Extensible**: Fewer extension options

**Why rejected**: Lacks critical extensions (TimescaleDB, pgvector)

## Implementation Notes

**Current Implementation:**

**Docker Compose Configuration:**

```yaml
services:
  db:
    image: timescale/timescaledb-ha:pg17
    environment:
      POSTGRES_USER: starter_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: starter_db
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d
```

**Initial Schema (V1)** enables extensions:

```sql
-- V1__initial_schema.sql
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;

-- Users table (standard relational)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- Example time-series table
CREATE TABLE metrics (
    timestamp TIMESTAMPTZ NOT NULL,
    metric_name TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('metrics', 'timestamp');
```

**Connection String:**

```python
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/starter_db"
```

**SQLAlchemy Configuration:**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
)

async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
```

**Key Patterns:**

**Time-Series with TimescaleDB:**

```python
# Efficient time-range queries
SELECT time_bucket('1 hour', timestamp) as hour,
       avg(value) as avg_value
FROM metrics
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY hour
ORDER BY hour DESC;
```

**Vector Search with pgvector:**

```python
# Semantic search using embeddings
SELECT id, title, content,
       embedding <-> %(query_embedding)s AS distance
FROM documents
ORDER BY distance
LIMIT 10;
```

**Geospatial with PostGIS:**

```python
# Find nearby locations
SELECT name, ST_Distance(location, ST_SetSRID(ST_MakePoint(-74.006, 40.7128), 4326)) as distance
FROM locations
WHERE ST_DWithin(location, ST_SetSRID(ST_MakePoint(-74.006, 40.7128), 4326), 1000)
ORDER BY distance;
```

**Maintenance Strategy:**

- **Backups**: Daily pg_dump + WAL archiving for point-in-time recovery
- **Monitoring**: Track query performance, connection pool, disk usage
- **Retention**: TimescaleDB `drop_chunks()` for automatic data expiration
- **Compression**: Enable TimescaleDB compression for older time-series data
- **Vacuuming**: Auto-vacuum configured for steady-state performance

**Scaling Strategy:**

1. **Vertical Scaling**: Start with single node, scale up as needed
2. **Read Replicas**: Add replicas for read-heavy workloads
3. **Connection Pooling**: PgBouncer for connection management at scale
4. **Partitioning**: TimescaleDB handles time-based partitioning automatically
5. **Caching**: Redis for frequently accessed data

## References

- [PostgreSQL 17 Documentation](https://www.postgresql.org/docs/17/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [PostGIS Documentation](https://postgis.net/documentation/)
- [Uber's PostgreSQL Journey](https://www.uber.com/blog/postgres-to-mysql-migration/)
- [Instagram's PostgreSQL Scale](https://instagram-engineering.com/sharding-ids-at-instagram-1cf5a71e5a5c)

---

## Revision History

| Date       | Author       | Changes                                                |
| ---------- | ------------ | ------------------------------------------------------ |
| 2025-11-14 | Project Lead | Initial ADR documenting PostgreSQL + extensions choice |
