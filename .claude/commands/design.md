# Design Review Command

## Usage

`@design.md <FEATURE_OR_COMPONENT>`

## Context

Feature/Component to design: $ARGUMENTS

## Your Role

You are a principal software architect conducting a thorough design review.

## Process

### 1. Requirements Analysis

- Extract and clarify business objectives from: $ARGUMENTS
- Define measurable acceptance criteria
- Identify all stakeholders and their needs
- List constraints (technical, business, regulatory)
- Document all assumptions

### 2. Architecture Design

- Define system boundaries
- Specify component interactions (include ASCII diagram)
- Design API contracts:
  - Request/response schemas
  - Error response formats
  - Authentication/authorization requirements
- Plan data models and relationships
- Design state management approach

### 3. Technology Assessment

- Evaluate technology choices against requirements
- Verify compatibility with existing stack
- Check for latest versions and documentation
- Identify any PoC or spike work needed
- List all new dependencies with justification

**Environment Considerations:**

- Development environment requirements (Docker, venv, bare metal)
- Build and deployment pipeline compatibility
- Testing environment setup requirements
- CI/CD integration considerations
- Local vs containerized development trade-offs

**Dependency Evaluation (for each new major dependency):**

- Latest stable version identified (via web_search)
- Maintenance status verified (last commit < 6 months)
- Security assessment (no known CVEs)
- License compatibility confirmed
- 1-2 alternatives evaluated with trade-offs
- Integration complexity assessed
- Learning curve for team considered
- Long-term support and sustainability

### 4. Integration Points

- Identify all external dependencies
- Specify integration patterns
- Define failure handling strategies
- Plan for backward compatibility
- Document migration path if breaking changes

### 5. Security Analysis

- Identify security requirements
- Apply threat modeling (STRIDE)
- Check against OWASP Top 10
- Plan authentication and authorization
- Document sensitive data handling

### 6. Performance & Scalability

- Define performance requirements
- Identify bottlenecks and optimization strategies
- Plan for scalability (horizontal/vertical)
- Consider caching strategies
- Estimate resource requirements

### 7. Risk Assessment

- List technical risks with probability and impact
- Identify dependencies on external teams/systems
- Flag uncertain assumptions
- Propose mitigation strategies
- Define fallback plans

### 8. Implementation Strategy

- Break down into phases/milestones
- Identify MVP scope
- Estimate effort for each phase
- Suggest testing strategy
- Plan rollout approach

## Output Format

1. **Executive Summary** - High-level overview and key decisions
2. **Requirements Specification** - Business objectives and acceptance criteria
3. **Architecture Design** - Components, interactions, and data flow
4. **API Contracts** - Complete interface specifications
5. **Technology Stack** - Choices with justifications
6. **Security Design** - Threat model and controls
7. **Performance Plan** - Requirements and optimization strategy
8. **Risk Register** - Risks with mitigation strategies
9. **Implementation Roadmap** - Phased delivery plan with estimates
10. **Open Questions** - Items requiring clarification or decision

## Validation Checklist

Before presenting design:

- [ ] Business requirements clearly mapped to technical solution
- [ ] All integration points identified and specified
- [ ] Security requirements addressed
- [ ] Performance requirements defined
- [ ] Risks identified with mitigation strategies
- [ ] Implementation broken into manageable phases
- [ ] No major assumptions left unvalidated
- [ ] Technology choices justified with evidence

## Critical Rules

**MANDATORY - NO EXCEPTIONS (v2.1):**

**Bug-Related Design (Enhanced 5-Category System):**

- Classify bug using 5-category taxonomy FIRST:
  - Category 1 (Syntax): No design needed, fix directly
  - Category 2 (Logic/Localized): Lightweight design if truly isolated
  - Category 3 (Integration): Design must analyze data flow across boundaries
  - Category 4 (Architectural): REQUIRES full system design review
  - Category 5 (Requirements): Clarify requirements BEFORE any design
- For Categories 3-5: Design must consider entire system flow, never localized
- When in doubt: escalate to higher category (treat as more complex)

**Research & Evidence:**

- Time-box research: 15 min quick check → 2-4 hrs deep research → escalate if unclear
- ALL assumptions must be explicitly documented (distinguish acceptable vs must-validate)
- NEVER assume user requirements - clarify ambiguities first
- Integration points must be specified with evidence from official docs
- If research > 4 hours without clarity, escalate with specific options

**Design Rigor:**

- NO trial-and-error or iterative approach - design must be complete before implementation
- Design must be reviewed and approved before ANY implementation
- Apply rigor based on context: startup/MVP = lightweight, enterprise = comprehensive
- Security and performance considered upfront, not retrofitted
- Provide alternative approaches when trade-offs exist
- Highlight what you don't know and recommend research/PoC (time-boxed)
- NO feature/UX decisions without explicit user approval
