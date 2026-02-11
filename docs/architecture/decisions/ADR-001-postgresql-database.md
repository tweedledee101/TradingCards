# ADR-001: Use PostgreSQL as Primary Database

**Date:** 2025-02-11  
**Status:** Accepted  
**Deciders:** Development Team

## Context

We need a database to store:
- Trading card catalog (structured data)
- Sales transactions (time-series data)
- Pre-computed trend metrics
- Social signals and metadata

Requirements:
- Handle time-series queries efficiently
- Support complex aggregations
- ACID compliance for financial data
- JSON support for flexible metadata
- Mature ecosystem and tooling

## Decision

We will use **PostgreSQL 14+** as our primary database.

## Alternatives Considered

### 1. MySQL
**Pros:**
- Widely used, good documentation
- Fast for simple queries

**Cons:**
- Weaker JSON support
- Less robust for complex analytics
- Window functions less mature

### 2. MongoDB
**Pros:**
- Flexible schema
- Good for rapid prototyping

**Cons:**
- No ACID guarantees (critical for sales data)
- Harder to enforce data integrity
- Complex aggregations less efficient
- Overkill for our structured data

### 3. TimescaleDB (PostgreSQL extension)
**Pros:**
- Optimized for time-series
- Built on PostgreSQL

**Cons:**
- Additional complexity
- May not need it at current scale
- Can migrate later if needed

## Rationale

PostgreSQL chosen because:

1. **Time-Series Support:** Excellent for date-range queries on sales data
2. **Window Functions:** Essential for calculating moving averages, price changes
3. **JSON Fields:** Flexible for storing scraped metadata
4. **ACID Compliance:** Critical for financial transaction data
5. **Mature Ecosystem:** SQLAlchemy, psycopg2, extensive tooling
6. **Indexing:** Supports partial indexes, GiST, GIN for optimization
7. **Future-Proof:** Can add TimescaleDB extension if needed

## Consequences

**Positive:**
- Robust data integrity
- Powerful query capabilities
- Well-documented, large community
- Easy to find developers with PostgreSQL experience

**Negative:**
- Slightly more complex setup than MySQL
- Requires proper indexing strategy for performance
- Need to manage connection pooling

**Neutral:**
- Will need to learn PostgreSQL-specific features (vs MySQL)
- Hosting costs similar to other RDBMS options

## Implementation Notes

- Use SQLAlchemy ORM for database interactions
- Implement connection pooling from day one
- Create indexes on: (card_id, sale_date), (hotness_score DESC)
- Consider partitioning `sales` table by date if > 10M rows

## Related Decisions

- ADR-002: Use SQLAlchemy ORM (planned)
- ADR-003: Database hosting strategy (planned)
