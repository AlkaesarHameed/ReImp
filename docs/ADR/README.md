# Architecture Decision Records (ADRs)

## What are ADRs?

Architecture Decision Records (ADRs) document important architectural decisions made in this project. Each ADR captures the context, decision, and consequences of a significant choice.

## Why ADRs?

- **Knowledge Transfer**: Help new team members understand why decisions were made
- **Historical Context**: Preserve reasoning for future reference
- **Design Alignment**: Ensure all stakeholders understand architectural direction
- **Audit Trail**: Track evolution of system architecture over time
- **Avoid Revisiting**: Prevent rehashing decisions already made

## When to Create an ADR

Create an ADR when making decisions about:

- **Technology Stack**: Frameworks, libraries, languages
- **Architecture Patterns**: Microservices, monolith, event-driven, etc.
- **Data Storage**: Database choices, caching strategies
- **Security**: Authentication, authorization, encryption approaches
- **Infrastructure**: Deployment, hosting, CI/CD
- **API Design**: REST vs GraphQL, versioning strategies
- **Code Organization**: Project structure, module boundaries

**Don't create ADRs for:**

- Implementation details (those go in code comments)
- Minor library choices
- Temporary workarounds
- Day-to-day development decisions

## ADR Naming Convention

```
ADR-XXX-short-title.md
```

- `XXX`: Sequential number (001, 002, 003, ...)
- `short-title`: Kebab-case description

**Examples:**

- `ADR-001-use-fastapi.md`
- `ADR-002-poetry-dependency-management.md`
- `ADR-003-flyway-migrations.md`

## ADR Lifecycle

1. **Proposed**: Initial draft, under discussion
2. **Accepted**: Decision approved and being implemented
3. **Superseded**: Replaced by newer ADR (reference replacement)
4. **Deprecated**: No longer applicable but kept for history

## How to Use the Template

1. Copy [template.md](./template.md)
2. Rename with next sequential number and descriptive title
3. Fill in all sections:
   - **Status**: Proposed, Accepted, Superseded, Deprecated
   - **Context**: What is the issue motivating this decision?
   - **Decision**: What decision are we making?
   - **Consequences**: What are the positive and negative outcomes?
   - **Alternatives Considered**: What other options were evaluated?
   - **References**: Sources, documentation, research
4. Commit and open PR for team review

## ADR Index

| ADR                                              | Title                                | Status   | Date       |
| ------------------------------------------------ | ------------------------------------ | -------- | ---------- |
| [001](./ADR-001-use-fastapi.md)                  | Use FastAPI as Web Framework         | Accepted | 2025-11-14 |
| [002](./ADR-002-poetry-dependency-management.md) | Use Poetry for Dependency Management | Accepted | 2025-11-14 |
| [003](./ADR-003-flyway-migrations.md)            | Use Flyway for Database Migrations   | Accepted | 2025-11-14 |
| [004](./ADR-004-postgresql-timescale-stack.md)   | Use PostgreSQL + TimescaleDB Stack   | Accepted | 2025-11-14 |
| [005](./ADR-005-test-organization.md)            | Test Organization Structure          | Accepted | 2025-11-14 |

## Further Reading

- [ADR Organization on GitHub](https://adr.github.io/)
- [Documenting Architecture Decisions by Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [ADR Tools](https://github.com/npryce/adr-tools)

---

Last Updated: 2025-11-14
