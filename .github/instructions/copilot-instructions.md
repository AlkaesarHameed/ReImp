# GitHub Copilot Repository Instructions

This repository follows strict development standards with pragmatic rigor (v2.2). All code suggestions must align with these principles.

## Development Methodology (v2.2)

Follow the 4-pillar methodology with critical development rules defined in CLAUDE.md:

## Custom Command Files (Claude Code Agent Only)

The Claude Code agent has access to specialized command workflows. While GitHub Copilot cannot use these directly, understanding their purpose helps maintain consistency:

- **@fix.md** - Bug fixing with 5-category taxonomy, environment awareness, and dependency management
- **@design.md** - Design-first architecture and system design
- **@implement.md** - Feature implementation following the 4-pillar methodology
- **@research.md** - Comprehensive technical research with evidence gathering
- **@review.md** - Code review following methodology compliance

**Critical Rules:**
- NO trial-and-error development (research FIRST, implement ONCE)
- NO undocumented assumptions (distinguish acceptable from must-validate)
- Bug classification required (5-category taxonomy: Syntax, Logic, Integration, Architectural, Requirements)
- Research time-boxing (15min → 4hrs → escalation)
- Context-aware rigor (startup vs enterprise, low vs high risk)

**The Four Pillars:**
1. Design-First Development
2. Evidence-Based Development with mandatory citations
3. Test-Driven Implementation
4. Quality-First Delivery with measurable metrics

## Code Generation Standards

### Before Generating Code
- Verify you understand the business requirement
- Check for existing similar implementations in the codebase
- Confirm the latest documentation for all dependencies
- Consider security and performance implications

### Evidence-Based Implementation
- Reference official documentation for all libraries/frameworks (verify version numbers)
- NEVER assume API signatures - verify with official docs
- Include source citations in generated code comments (mandatory for external APIs)
- Time-box research: 15min quick check, 2-4hrs deep research, escalate if unclear
- Document assumptions: distinguish acceptable (e.g., language semantics) from must-validate (e.g., API behavior)
- Citation format: Source URL, verification date, key behavior notes

### Test Requirements (Test-Driven Development)
- Generate tests BEFORE implementation code (mandatory)
- Include unit tests for business logic
- Add integration tests for external dependencies
- Cover edge cases and error conditions
- Minimum 80% code coverage for new code
- Apply rigor based on risk: high-risk = comprehensive, low-risk = pragmatic

## Code Style Preferences

### Documentation (Inline-First Philosophy)
- Self-documenting code first (clear names, structure)
- Add docstrings to public APIs, classes, and complex functions
- Use inline comments for non-obvious logic, edge cases, workarounds
- Include citation comments when implementing from external docs (MANDATORY)
- Keep comments concise and up-to-date with code
- Use markdown documentation ONLY for: ADRs, onboarding, deployment, post-mortems
- NEVER duplicate code details in separate markdown files

### Error Handling
- Handle all error cases explicitly
- Provide meaningful error messages
- Never silently catch and ignore exceptions
- Log errors with sufficient context for debugging

### Security
- Never hardcode secrets or credentials
- Validate all user inputs
- Use parameterized queries for database operations
- Follow OWASP Top 10 guidelines

## Technology-Specific Guidelines

### TypeScript/JavaScript
- Use strict TypeScript mode
- Prefer async/await over callbacks
- Use const by default, let when reassignment needed
- Destructure objects for cleaner code

### Python
- Follow PEP 8 style guide
- Use type hints for function signatures
- Prefer list comprehensions for simple transformations
- Use context managers for resource handling

### React/Next.js
- Use functional components with hooks
- Implement proper error boundaries
- Follow React Server Components patterns for Next.js 15+
- Ensure accessibility (WCAG 2.1 AA)

## Commit Expectations

When generating code for commits:
- Ensure all tests pass
- Run linters and formatters
- Verify type checking passes
- Include relevant documentation updates

## When Uncertain

If implementation details are unclear:
- Time-box investigation: 15min → 4hrs maximum before escalating
- Ask for clarification rather than assuming (cost of asking < cost of wrong assumption)
- Present 2-3 options with pros/cons/evidence when escalating
- Flag potential security or performance concerns
- Indicate where documentation verification is needed
- For production emergencies: apply minimal hotfix, flag `[EMERGENCY_FIX]`, create ticket for proper fix

## Bug Handling (5-Category Taxonomy)

When fixing bugs, classify first:
- **Category 1 (Syntax/Typo)**: Fix immediately + test
- **Category 2 (Logic/Localized)**: Verify isolation, fix with test
- **Category 3 (Integration)**: Analyze data flow across boundaries
- **Category 4 (Architectural)**: NEVER fix locally, full system analysis required
- **Category 5 (Requirements)**: Clarify requirements FIRST

When in doubt, escalate to higher category (treat as more complex).

## Development Environment Awareness (Rule 0.5)

**MANDATORY - UNDERSTAND ENVIRONMENT BEFORE ANY WORK:**

Before suggesting code changes for ANY task (implementation, debugging, testing), understand the development environment. This understanding should be consistent to prevent trial-and-error.

### Environment Discovery

1. **Check for environment documentation first**
   - Review CLAUDE.md, README.md for setup instructions
   - Look for `.devcontainer/`, `docker-compose.yml`, `Dockerfile`
   - Check for `.venv/`, `venv/`, `pyproject.toml`, `package.json`

2. **Identify environment type(s)**
   - Containerized (Docker, Dev Containers)
   - Virtual environment (Python venv, Poetry)
   - Node.js (npm, yarn)
   - Mixed environments (both local and containers)

3. **Understand key facts**
   - How to build/run the application
   - Where code changes take effect (local vs container)
   - How to execute tests
   - How to install dependencies

### Mixed Environment Critical Understanding

When both local files AND containers exist:

**UNDERSTAND THIS DUALITY:**
- Local repo files ≠ Files inside running container
- Editing local file does NOT affect running container automatically
- Changes in running container are NOT tracked in git
- **NEVER suggest editing files directly inside running containers**

**Correct Workflow:**
1. Edit local files in the repository
2. Either: Rebuild container (`docker-compose build --no-cache`)
3. Or: Copy file to container temporarily for testing (`docker cp`)
4. Always remember: Container changes are ephemeral, repo changes persist

### Environment-Specific Best Practices

**For Docker/Container Environments:**
- Verify volume mounts before suggesting changes
- Understand difference between `docker-compose up --build` (incremental) vs `--build --no-cache` (full rebuild)
- Use `docker exec` for investigation only, never for permanent changes

**For Python Virtual Environments:**
- Verify active environment before suggesting package installations
- Use `which python` to confirm correct interpreter
- Ensure venv is activated before running Python commands

**For Node.js Environments:**
- Check `node --version` and `npm --version` match project requirements
- Always include `package-lock.json` or `yarn.lock` in commits

## Dependency Management Consistency (Rule 0.6)

**MANDATORY - BEFORE SUGGESTING ANY DEPENDENCY ADDITION/CHANGE:**

### Python Dependency Management

**For Poetry Projects (Preferred):**
```bash
# Add dependency - Poetry resolves versions
poetry add package_name

# Update all dependencies to latest compatible versions
poetry update

# Show outdated packages
poetry show --outdated

# CRITICAL: Always commit poetry.lock with pyproject.toml
```

**For pip-tools Projects:**
```bash
# Edit requirements.in (NOT requirements.txt)
# Then compile with --upgrade to get latest versions
pip-compile --upgrade requirements.in

# For complete refresh
pip-compile --upgrade --rebuild requirements.in

# Install compiled requirements
pip-sync requirements.txt

# CRITICAL: Commit both requirements.in and requirements.txt
```

**For Basic pip Projects:**
```bash
# Migrate to Poetry or pip-tools when possible
# If stuck with basic pip:
pip install package_name==<LATEST_VERSION>
pip freeze > requirements.txt
```

### Node.js Dependency Management

```bash
# Check for outdated packages
npm outdated

# Update within semver constraints
npm update

# Update to latest (after research!)
npm install package_name@latest

# Check security vulnerabilities
npm audit
npm audit fix  # Review changes carefully

# CRITICAL: Always commit package-lock.json
```

### Dependency Selection Criteria (MANDATORY Checklist)

Before suggesting any dependency, verify:

- [ ] Last commit < 6 months ago (actively maintained)
- [ ] Latest stable version identified
- [ ] No known security vulnerabilities (check CVEs)
- [ ] License compatible with project
- [ ] Good documentation and examples available
- [ ] Evaluated 2-3 alternatives with pros/cons
- [ ] Not excessive transitive dependencies
- [ ] Community adoption verified (but not sole criteria)

### Red Flags - REJECT These Dependencies

❌ Last commit > 1 year ago (unmaintained)
❌ Open security vulnerabilities without patches
❌ Incompatible license (e.g., GPL in commercial project)
❌ Excessive dependencies (adds 50+ packages)
❌ Alpha/beta/RC versions for production
❌ No documentation or examples
❌ Deprecated by maintainers

## Integration with Coding Agent

For complex features requiring the coding agent:
1. Agent will design the solution first (with bug classification if applicable)
2. Present design for approval
3. Research with time-boxing (15min → 4hrs → escalate)
4. Implement with tests (TDD)
5. Validate quality gates

Copilot should generate code that aligns with this workflow.

---

**Version**: 2.2
**Last Updated**: 2025-11-14
**Note**: This file supplements CLAUDE.md. For complete methodology details including emergency protocols, success metrics, and context considerations, refer to CLAUDE.md.
