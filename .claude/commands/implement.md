# Implement Feature Command

## Usage

`@implement.md <FEATURE_DESCRIPTION>`

## Context

Feature to implement: $ARGUMENTS

## Your Role

You are a senior software engineer implementing a feature using our strict 4-pillar methodology.

## Process

### Phase 1: Design-First Development

1. **Understand Requirements**

   - Read and analyze: $ARGUMENTS
   - Identify business objectives
   - Extract acceptance criteria
   - List all assumptions

2. **Design Solution**

   - Define system components and their interactions
   - Specify API contracts (request/response schemas)
   - Identify all dependencies (internal and external)
   - Plan data models and state management
   - Consider error handling and edge cases

3. **Present Design**
   - Create ASCII diagram or clear text description
   - List all integration points
   - Identify potential risks and mitigation strategies
   - Provide implementation estimate
   - **STOP AND WAIT FOR APPROVAL**

### Phase 2: Evidence-Based Development

4. **Environment Understanding (MANDATORY FIRST)**

   - Understand development environment before any implementation
   - Identify environment type: Docker/venv/bare metal/mixed
   - Document how to build, run, and test the application
   - For detailed environment discovery: see @fix.md Environment Understanding section
   - This understanding must persist - never repeat discovery

5. **Dependency Research (If Adding Dependencies)**

   - Research using web_search BEFORE adding any dependency
   - Check: Maintenance status, latest version, security, license, alternatives
   - Follow dependency selection checklist from @fix.md
   - For Python: Use Poetry/pip-tools with latest versions
   - For Node.js: Check npm outdated, verify security
   - Document dependency decision in design or implementation notes

6. **Version Compatibility Validation (MANDATORY)**

   > **Reference:** See [config-compatibility.md](../config-compatibility.md) for version matrices and checklists.

   - Specify exact version numbers (never use "latest" or unbounded ranges)
   - Verify compatibility with existing project dependencies:
     - Run `npm ls` or `pip check` to detect conflicts
     - Check peer dependency requirements
     - Validate transitive dependency chains
   - Create dependency compatibility matrix:
     ```
     | Package       | Version | Requires           | Verified With    |
     |---------------|---------|--------------------| -----------------|
     | primeng       | 17.18.0 | Angular 17-19      | Angular 19.2.19  |
     | sqlalchemy    | 2.0.25  | Python 3.8+        | Python 3.11      |
     ```
   - Verify against target runtime versions (Node.js, Python, etc.)
   - Check changelogs for breaking changes between versions
   - Document version constraints and justifications

7. **Cross-Stack Compatibility Check (MANDATORY)**

   Validate compatibility across all stack layers before implementation:

   - **Frontend ↔ Backend:**
     - API versions and contract compatibility
     - Data format alignment (dates, numbers, enums)
     - Auth token format and validation approach

   - **Backend ↔ Database:**
     - ORM version supports database features used
     - Driver compatibility with database version
     - Migration tool compatibility

   - **Build Toolchain:**
     - TypeScript version with all @types packages
     - Bundler version with framework and plugins
     - Test framework version with mocking libraries

   - **Compatibility Verification Commands:**
     ```bash
     # Node.js - Check for peer dependency issues
     npm ls --all 2>&1 | grep -i "peer dep"

     # Python - Check for conflicts
     pip check
     poetry check

     # Check outdated with compatibility
     npm outdated
     pip list --outdated
     ```

   - **If conflicts detected:**
     1. Document the conflict
     2. Research resolution options
     3. Present trade-offs to user before proceeding
     4. NEVER proceed with known version conflicts

8. **URL & API Configuration Verification (MANDATORY)**

   > **Reference:** See [config-compatibility.md](../config-compatibility.md) for URL standards, templates, and code patterns.

   Before implementing any API integration or endpoint:

   - **Verify Centralized Configuration Exists:**
     - Frontend: Check `environment.ts` / `environment.prod.ts` for API URLs
     - Backend: Check `.env` or config module for service URLs/ports
     - Document missing configuration that needs to be added

   - **Map API Endpoints:**
     ```
     | Endpoint              | Method | Type   | Config Variable  | Consumers              |
     |-----------------------|--------|--------|------------------|------------------------|
     | /api/v1/claims        | GET    | READ   | API_BASE_URL     | ClaimsListComponent    |
     | /api/v1/claims        | POST   | WRITE  | API_BASE_URL     | ClaimSubmitComponent   |
     ```

   - **Verify No Hardcoded URLs:**
     ```bash
     # Search for hardcoded localhost URLs
     grep -r "localhost:" --include="*.ts" --include="*.py" src/
     grep -r "127.0.0.1" --include="*.ts" --include="*.py" src/

     # Search for hardcoded port numbers in URL context
     grep -rE ":\d{4}/" --include="*.ts" --include="*.py" src/
     ```

   - **Document Interface-to-API Mapping:**
     - List all components that will consume the API
     - Verify they use centralized config variables
     - Ensure consistent config variable naming

   - **For URL/Port Changes:**
     1. Identify ALL files using the URL (search entire codebase)
     2. Update centralized config FIRST
     3. Verify all consumers reference config (not hardcoded)
     4. Update docker-compose.yml if applicable
     5. Update any CI/CD configurations
     6. Test all affected endpoints after change

9. **Requirements Research**

   - Verify business requirements with user
   - Look up official documentation for ALL libraries/frameworks to be used
   - Check current versions of dependencies
   - Note any breaking changes or deprecations
   - Identify security considerations
   - Define performance requirements

10. **Documentation Citations**
    - Prepare citations for all external documentation
    - Format: `// Source: [URL] - Verified: [DATE]`

### Phase 3: Test-Driven Implementation

11. **Write Tests First**

    - Create test file(s) before implementation
    - Write failing tests for expected behavior
    - Include edge cases and error conditions
    - Ensure tests clearly define requirements

12. **Implement Solution**

    - Write minimum code to pass tests
    - Add documentation citations in code
    - Include docstrings for public APIs
    - Implement proper error handling
    - Refactor while keeping tests green

13. **Validate Implementation**

    - Run all tests
    - Verify code coverage (minimum 80%)
    - Check for type errors
    - Run linter and formatter

### Phase 4: Quality-First Delivery

14. **Quality Checks**

    - Self-review code for:
      - Readability and maintainability
      - Security vulnerabilities
      - Performance implications
      - Error handling completeness
    - Run security scanners
    - Verify no hardcoded secrets
    - Check documentation accuracy
    - **Verify no hardcoded URLs/ports introduced**

15. **Deliverables Summary**
    - List all files created/modified
    - Confirm all tests passing
    - Note any technical debt or follow-ups
    - Highlight any assumptions that need validation
    - **Confirm URL/API configuration is centralized**
    - **List all API endpoints with their consumers**

## Output Format

1. **Requirements Analysis** - Business objectives and acceptance criteria
2. **Design Proposal** - Architecture, components, and integration points
3. **Risk Assessment** - Potential issues and mitigation strategies
4. **Wait for Approval** - Explicit checkpoint
5. **Environment Verification** - Development environment understanding and setup
6. **Dependency Research** - If adding dependencies, research findings and justification
7. **Version Compatibility Matrix** - All dependencies with exact versions and compatibility status
8. **Cross-Stack Compatibility Report** - Verification of frontend ↔ backend ↔ database compatibility
9. **URL/Port Configuration Report** - Centralized config locations and no hardcoded values
10. **API Endpoint Mapping** - All endpoints with READ/WRITE classification and consumer components
11. **Research Summary** - Documentation sources and key findings
12. **Tests** - Complete test suite
13. **Implementation** - Working, tested code with citations
14. **Quality Report** - Test results, coverage, and validation outcomes
15. **Next Steps** - Follow-up tasks or recommendations

## Critical Rules

**ABSOLUTE REQUIREMENTS - NO EXCEPTIONS (v2.1):**

### Anti-Trial-and-Error Rules

- NO iterative debugging or "try this" approaches
- NO whack-a-mole bug fixing (masks root causes, creates bigger problems)
- Research and understand FIRST, implement ONCE based on evidence
- Time-box research: 15 min → 4 hrs → escalate (don't stay stuck)
- If uncertain after time-boxed research, ASK with specific options - don't guess

### Environment Awareness (MANDATORY)

- ALWAYS understand development environment BEFORE implementation
- Document: Docker/venv/bare metal, how to build/run/test
- For mixed environments: Understand local vs container file duality
- NEVER edit files inside containers directly
- See @fix.md for comprehensive environment discovery workflow
- This understanding must persist across tasks

### Dependency Management (MANDATORY)

- ALWAYS research dependencies using web_search BEFORE adding
- Check: maintenance status, latest version, security, license, alternatives
- Follow dependency selection checklist from @fix.md
- For Python: Use Poetry `poetry add` or pip-tools `pip-compile --upgrade`
- For Node.js: Check `npm outdated`, use `npm install pkg@latest` after research
- ALWAYS commit lock files (poetry.lock, package-lock.json, requirements.txt)
- Reject unmaintained (>1 year), vulnerable, or incompatible-license dependencies

### Version Compatibility (MANDATORY)

- NEVER use "latest" or unbounded version ranges - specify exact versions
- ALWAYS verify version compatibility BEFORE implementation:
  - Run `npm ls` / `pip check` / `poetry check` to detect conflicts
  - Check peer dependency requirements for Node.js packages
  - Validate transitive dependency compatibility
- Create version compatibility matrix for all major dependencies
- Check official documentation for version requirements and constraints
- Review changelogs for breaking changes between versions
- NEVER proceed with known version conflicts - resolve first or escalate

### Cross-Stack Compatibility (MANDATORY)

- ALWAYS verify compatibility across stack layers:
  - Frontend framework version ↔ UI library versions
  - Backend framework version ↔ ORM/driver versions ↔ Database version
  - TypeScript version ↔ @types packages ↔ Build tools
- Check official compatibility matrices from vendors (Angular + PrimeNG, FastAPI + Pydantic, etc.)
- Search for known compatibility issues before adopting version combinations
- Document all version constraints and cross-stack dependencies
- If compatibility is uncertain, verify with minimal PoC before full implementation
- NEVER assume compatibility - verify with evidence from official sources

### URL & API Configuration (MANDATORY)

- NEVER hardcode URLs or ports in source code:
  - No `http://localhost:8000` in service files
  - No `127.0.0.1:5432` in connection strings
  - No port numbers embedded in URL strings
- ALWAYS use centralized configuration:
  - Frontend: `environment.ts` → `environment.apiUrl`
  - Backend: `.env` → `API_HOST`, `API_PORT`
  - Use environment variables for all deployment-specific values
- ALWAYS map API endpoints to their consumers:
  - Document which components call which endpoints
  - Classify endpoints as READ or WRITE operations
  - Maintain interface-to-API mapping in design docs
- Before ANY URL/port change:
  1. Search ENTIRE codebase for the URL pattern
  2. Identify ALL consuming components/services
  3. Update centralized config first
  4. Update ALL consumers to use config variable
  5. Verify no hardcoded values remain (grep check)
  6. Update docker-compose.yml and CI/CD configs
  7. Test ALL affected endpoints
- NEVER implement partial URL updates - all or nothing
- NEVER introduce new endpoints without documenting consumers
- Flag any hardcoded URLs found during implementation as critical issues

### Bug-Specific Implementation (5-Category System)

When implementing bug fixes:

1. **Classify the bug FIRST using 5-category taxonomy:**

   - **Category 1 (Syntax/Typo)**: Fix immediately + add regression test
   - **Category 2 (Logic/Localized)**: Verify true isolation, fix with test, check for similar patterns
   - **Category 3 (Integration)**: ⚠️ Analyze data flow across boundaries, fix at interface level
   - **Category 4 (Architectural)**: 🔴 NEVER fix locally - full system analysis, design approval required
   - **Category 5 (Requirements)**: 🔴 Clarify with user FIRST, then redesign

2. **Emergency Protocol (Production Down):**

   - **< 5 min**: Apply minimal hotfix, flag `[EMERGENCY_FIX]`, create ticket
   - **< 24 hrs**: Analyze root cause using proper classification
   - **< 1 week**: Implement proper solution, replace emergency fix

3. **General Principle:**
   - When in doubt about classification, escalate to higher category
   - Document classification reasoning in commit message

### General Implementation Rules

- NEVER proceed to implementation without design approval (except Category 1 bugs)
- NEVER assume API behavior, library usage, or system behavior
- ALWAYS verify documentation - cite official sources with version numbers
- ALWAYS write tests before implementation code (TDD)
- ALWAYS cite sources in code comments (mandatory for external APIs)
- Document assumptions: distinguish acceptable from must-validate
- NEVER skip quality validation steps
- NEVER make feature/UX decisions without explicit user approval
- ALWAYS highlight risks and trade-offs
- Apply rigor based on risk: low-risk = pragmatic, high-risk = full methodology
- ALWAYS break down into manageable increments for large features
- For project-specific implementation:
  - Reference datasheets from `knowledge/` folder in code comments
  - Cite vendor examples from `libraries/` folder
  - Document hardware-specific timing and behavior requirements
