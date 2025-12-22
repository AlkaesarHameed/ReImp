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

**Version Compatibility Validation (MANDATORY):**

> **Reference:** See [config-compatibility.md](../config-compatibility.md) for version matrices and compatibility checklists.

For each dependency/tool in design or research results:

- Document exact version to be used (not "latest" - specify actual version number)
- Verify version compatibility with existing project dependencies:
  - Check package.json/requirements.txt/pyproject.toml for conflicts
  - Identify peer dependency requirements
  - Validate transitive dependency compatibility
- Create compatibility matrix for major dependencies:
  ```
  | Dependency    | Version | Requires          | Conflicts With |
  |---------------|---------|-------------------|----------------|
  | Example-lib   | 2.3.1   | Node >= 18        | OldLib < 3.0   |
  ```
- Check for version pinning requirements (exact vs range)
- Verify all dependencies work with target runtime versions (Node, Python, etc.)
- Document minimum and maximum supported versions for flexibility

**Cross-Stack Technology Compatibility (MANDATORY):**

Validate compatibility across the entire technology stack:

- **Frontend ↔ Backend Compatibility:**
  - API contract versions match (OpenAPI spec, GraphQL schema)
  - Authentication/token formats compatible
  - Data serialization formats aligned (JSON, dates, decimals)
  - CORS and security header requirements

- **Backend ↔ Database Compatibility:**
  - ORM/driver version supports database version
  - Query syntax compatibility verified
  - Connection pooling library compatibility
  - Migration tool version compatibility

- **Build Tool Compatibility:**
  - Bundler (Webpack/Vite/esbuild) version with framework
  - TypeScript version with all typed dependencies
  - Linter/formatter versions with parser plugins

- **Runtime Environment Compatibility:**
  - Container base image versions
  - Cloud provider SDK versions with runtime
  - CI/CD tool versions with build scripts

- **Integration Compatibility Matrix:**
  ```
  | Component A      | Component B      | Compatible Versions | Notes           |
  |------------------|------------------|---------------------|-----------------|
  | Angular 19       | PrimeNG          | 17.x, 18.x          | Check changelog |
  | FastAPI 0.100+   | Pydantic         | 2.x only            | Breaking change |
  ```

- **Compatibility Verification Steps:**
  1. Check official compatibility matrices from vendors
  2. Review changelogs for breaking changes between versions
  3. Search for known compatibility issues (GitHub issues, Stack Overflow)
  4. Verify with minimal PoC if compatibility is uncertain
  5. Document any version constraints discovered

### 4. API & URL Configuration Management (MANDATORY)

> **Reference:** See [config-compatibility.md](../config-compatibility.md) for detailed standards, templates, and code examples.

**Centralized Configuration Requirements:**

- All URLs and ports MUST be parameterized (never hardcoded)
- Define centralized configuration location:
  - Frontend: `environment.ts` / `environment.prod.ts` (Angular)
  - Backend: `.env` files, config classes, or settings modules
  - Shared: API contract definitions (OpenAPI spec)
- Create URL/Port mapping registry:
  ```
  | Service        | Port | Base URL              | Config Location              |
  |----------------|------|-----------------------|------------------------------|
  | Frontend       | 4200 | http://localhost:4200 | environment.ts               |
  | Backend API    | 8000 | http://localhost:8000 | .env / config.py             |
  | Auth Service   | 8001 | http://localhost:8001 | .env / config.py             |
  | Database       | 5432 | localhost:5432        | docker-compose.yml / .env    |
  ```

**API Endpoint Mapping:**

- Document all API endpoints with their purposes:
  ```
  | Endpoint Pattern      | Method | Service    | Purpose              |
  |-----------------------|--------|------------|----------------------|
  | /api/v1/users         | GET    | Backend    | List users           |
  | /api/v1/users         | POST   | Backend    | Create user (WRITE)  |
  | /api/v1/auth/token    | POST   | Auth       | Authentication       |
  ```
- Distinguish READ vs WRITE endpoints clearly
- Map each endpoint to its consuming interface/component

**Interface-to-API Mapping:**

- Create mapping of UI components to API endpoints:
  ```
  | Component/Interface    | API Endpoints Used        | Config Reference     |
  |------------------------|---------------------------|----------------------|
  | UserListComponent      | GET /api/v1/users         | API_BASE_URL         |
  | UserFormComponent      | POST /api/v1/users        | API_BASE_URL         |
  | LoginComponent         | POST /api/v1/auth/token   | AUTH_API_URL         |
  ```
- Identify all consumers of each API endpoint
- Document data flow from UI → API → Database

**URL Change Impact Analysis:**

- Before any URL/port change, identify ALL affected locations:
  - Frontend service files
  - Environment configuration files
  - API client/interceptor configurations
  - Docker compose files
  - CI/CD pipeline configurations
  - Documentation and README files
- Create change propagation checklist for each URL

### 5. Integration Points

- Identify all external dependencies
- Specify integration patterns
- Define failure handling strategies
- Plan for backward compatibility
- Document migration path if breaking changes

### 6. Security Analysis

- Identify security requirements
- Apply threat modeling (STRIDE)
- Check against OWASP Top 10
- Plan authentication and authorization
- Document sensitive data handling

### 7. Performance & Scalability

- Define performance requirements
- Identify bottlenecks and optimization strategies
- Plan for scalability (horizontal/vertical)
- Consider caching strategies
- Estimate resource requirements

### 8. Risk Assessment

- List technical risks with probability and impact
- Identify dependencies on external teams/systems
- Flag uncertain assumptions
- Propose mitigation strategies
- Define fallback plans

### 9. Implementation Strategy

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
6. **Version Compatibility Matrix** - All dependencies with exact versions and compatibility verification
7. **Cross-Stack Compatibility Report** - Frontend ↔ Backend ↔ Database compatibility validation
8. **URL/Port Configuration Registry** - Centralized mapping of all services, ports, and configuration locations
9. **API Endpoint Mapping** - All endpoints with READ/WRITE classification and consuming components
10. **Security Design** - Threat model and controls
11. **Performance Plan** - Requirements and optimization strategy
12. **Risk Register** - Risks with mitigation strategies (including version conflicts)
13. **Implementation Roadmap** - Phased delivery plan with estimates
14. **Open Questions** - Items requiring clarification or decision

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
- [ ] **All dependency versions explicitly specified (no "latest")**
- [ ] **Version compatibility matrix completed for major dependencies**
- [ ] **Cross-stack compatibility verified (frontend ↔ backend ↔ database)**
- [ ] **No version conflicts identified in transitive dependencies**
- [ ] **Runtime environment compatibility confirmed**
- [ ] **All URLs and ports are parameterized (no hardcoded values)**
- [ ] **Centralized configuration location defined for all URLs/ports**
- [ ] **API endpoint mapping completed with READ/WRITE classification**
- [ ] **Interface-to-API mapping documented for all components**
- [ ] **URL change impact analysis completed (all consumers identified)**

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

**Version & Stack Compatibility (MANDATORY):**

- NEVER specify "latest" versions - always document exact version numbers
- ALWAYS create version compatibility matrix for major dependencies
- Verify cross-stack compatibility BEFORE finalizing design:
  - Frontend ↔ Backend ↔ Database version alignment
  - Build tools ↔ Framework ↔ TypeScript compatibility
  - Runtime environment ↔ Dependencies compatibility
- Check official compatibility matrices from vendors
- Search for known compatibility issues before recommending version combinations
- Document version constraints as part of technology decisions
- Flag potential version conflicts as risks with mitigation strategies
- NEVER finalize design with unverified version compatibility

**URL & API Configuration Management (MANDATORY):**

- NEVER hardcode URLs or ports - always parameterize in centralized config
- ALWAYS define configuration hierarchy:
  - Environment variables (.env) for deployment-specific values
  - Configuration files (environment.ts, config.py) for application defaults
  - Constants files for API path patterns only (not hosts/ports)
- ALWAYS create URL/Port registry mapping all services to their config locations
- ALWAYS classify API endpoints as READ or WRITE operations
- ALWAYS map each UI component/service to its API endpoints
- Before ANY URL/port change:
  1. Search entire codebase for all usages (grep for URL patterns)
  2. Identify all consuming components/services
  3. Update ALL locations - no partial updates allowed
  4. Verify no hardcoded values remain after change
- NEVER design APIs without documenting their consumers
- NEVER introduce new endpoints without updating interface mappings
- Flag URL/port conflicts as critical risks requiring immediate resolution

**Design Rigor:**

- NO trial-and-error or iterative approach - design must be complete before implementation
- Design must be reviewed and approved before ANY implementation
- Apply rigor based on context: startup/MVP = lightweight, enterprise = comprehensive
- Security and performance considered upfront, not retrofitted
- Provide alternative approaches when trade-offs exist
- Highlight what you don't know and recommend research/PoC (time-boxed)
- NO feature/UX decisions without explicit user approval
