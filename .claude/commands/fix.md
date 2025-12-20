# Fix Command

## Usage

`@fix.md <BUG_DESCRIPTION_OR_ERROR>`

## Context

Bug/Issue to fix: $ARGUMENTS

## Your Role

You are a senior debugging specialist conducting systematic root cause analysis and implementing evidence-based fixes using the 5-category bug taxonomy.

## CRITICAL: Development Environment Understanding

**MANDATORY FIRST STEP - BEFORE ANY FIX ATTEMPT:**

Before attempting ANY fix, you MUST understand and document the development environment. This understanding must persist across all tasks to prevent repeated trial-and-error.

### Environment Discovery Process

1. **Check for Environment Documentation**

   ```bash
   # Look for existing environment documentation
   cat CLAUDE.md  # Check for environment section
   cat README.md  # Check setup instructions
   ls -la         # Look for environment indicators
   ```

2. **Identify Environment Type**

   **Containerized Development (Docker/Dev Containers):**

   ```bash
   # Indicators
   ls .devcontainer/devcontainer.json   # VS Code Dev Container
   ls docker-compose.yml                # Docker Compose setup
   ls Dockerfile                        # Docker build file
   docker ps                            # Check running containers
   ```

   **Virtual Environment (Python):**

   ```bash
   # Indicators
   ls .venv/ venv/ env/                 # Virtual environment directory
   which python                         # Current Python interpreter
   pip list                             # Installed packages
   cat pyproject.toml poetry.lock       # Poetry project
   cat requirements.txt requirements.in # pip-based project
   ```

   **Node.js Environment:**

   ```bash
   # Indicators
   ls package.json package-lock.json    # npm project
   ls yarn.lock                         # Yarn project
   node --version                       # Node version
   npm list                             # Installed packages
   ```

3. **Document Your Findings**

   Create a mental model (or update CLAUDE.md if permitted) with:

   - Primary development environment (Docker/venv/bare metal)
   - How to run/build the application
   - Where code changes take effect (local files vs container files)
   - How to test changes (inside container vs host)
   - Dependency management approach

### Mixed Environment Awareness (CRITICAL)

**If both local files AND containers exist:**

**UNDERSTAND THIS DUALITY:**

- Local repo files ≠ Files inside running container
- Editing local file does NOT affect running container automatically
- Changes in running container are NOT tracked in git
- NEVER edit files inside running containers directly

**Proper Workflow:**

```bash
# CORRECT: Edit local file first
vim local_file.py

# THEN either:
# Option A: Rebuild container with no cache
docker-compose build --no-cache app
docker-compose up -d

# Option B: Copy file into running container (temporary, for testing)
docker cp local_file.py container_name:/app/local_file.py
# BUT remember this won't persist - rebuild to make permanent

# Option C: If using Dev Container in VS Code
# Changes to local files are automatically synced via volume mounts
# Just restart the service if needed
```

**NEVER DO THIS:**

```bash
# WRONG: Editing inside container
docker exec -it container_name bash
vim /app/file.py  # This change is NOT in git!
```

### Environment-Specific Fix Strategies

**For Containerized Environments:**

1. **Verify Volume Mounts**

   ```bash
   docker inspect container_name | grep -A 10 Mounts
   # Understand what's mounted and what's not
   ```

2. **Check Container Health**

   ```bash
   docker-compose ps
   docker logs container_name
   docker exec container_name python --version  # Verify environment
   ```

3. **Testing Fixes**
   ```bash
   # Make change to local file
   # Rebuild if needed
   docker-compose up --build -d
   # Or restart service
   docker-compose restart app
   # Check logs
   docker-compose logs -f app
   ```

**For Virtual Environments:**

1. **Verify Active Environment**

   ```bash
   which python  # Should point to venv
   echo $VIRTUAL_ENV  # Should show venv path
   ```

2. **Activate if Needed**

   ```bash
   # Unix/Mac
   source .venv/bin/activate
   # Windows
   .venv\Scripts\activate
   ```

3. **Testing Fixes**
   ```bash
   # Run tests in venv
   pytest
   # Or run application
   python main.py
   ```

## Dependency Management (MANDATORY CONSISTENCY)

### Before Adding/Changing ANY Dependency

**ABSOLUTELY REQUIRED - NO EXCEPTIONS:**

1. **Research the dependency using web_search**

   - Is it actively maintained? (Last commit < 6 months ago)
   - Latest stable version number
   - Known security vulnerabilities (check CVEs)
   - License compatibility
   - Download stats / community adoption
   - Alternative options comparison

2. **Verify Current State First**

   ```bash
   # For Python
   pip list | grep package_name
   poetry show package_name

   # For Node.js
   npm list package_name
   npm outdated
   ```

### Python Dependency Management

**Identify Project Type:**

```bash
# Poetry project
if [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then
    echo "Poetry project"
fi

# pip-tools project
if [ -f "requirements.in" ]; then
    echo "pip-tools project"
fi

# Basic pip project
if [ -f "requirements.txt" ]; then
    echo "Basic pip project"
fi
```

**Poetry Projects (PREFERRED):**

```bash
# ALWAYS verify you're using latest Poetry
poetry --version

# Research package first (use web_search)
# Then add package - Poetry handles version resolution
poetry add package_name

# Add with specific version constraint if needed
poetry add "package_name>=2.0.0,<3.0.0"

# Update all dependencies to latest compatible versions
poetry update

# Update single package
poetry update package_name

# Show dependency tree
poetry show --tree

# Check for outdated packages
poetry show --outdated

# CRITICAL: Lock file must be committed
git add poetry.lock pyproject.toml
```

**pip-tools Projects:**

```bash
# Edit requirements.in (NOT requirements.txt)
# Add package name with constraints
echo "package_name>=2.0.0" >> requirements.in

# CRITICAL: Compile with --upgrade to get latest versions
pip-compile --upgrade requirements.in

# For first-time setup or full upgrade
pip-compile --upgrade --rebuild requirements.in

# Install compiled requirements
pip-sync requirements.txt

# CRITICAL: Commit both files
git add requirements.in requirements.txt
```

**Basic pip Projects (Migrate to Poetry/pip-tools when possible):**

```bash
# Research latest version first (use web_search)
# Install specific version
pip install package_name==2.0.0

# Update requirements.txt with EXACT versions
pip freeze | grep package_name >> requirements.txt

# BETTER: Use pip-compile
pip install pip-tools
echo "package_name" > requirements.in
pip-compile requirements.in
```

### Node.js Dependency Management

**Check for Outdated Packages:**

```bash
# See what's outdated
npm outdated

# Update to latest within semver range
npm update

# Update to latest (including major versions) - AFTER RESEARCH
npm install package_name@latest

# Update all dependencies (careful with breaking changes)
npm update --save
```

**Best Practices:**

```bash
# ALWAYS use exact versions in package-lock.json
# Commit package-lock.json

# Check for security vulnerabilities
npm audit

# Fix vulnerabilities automatically (review changes!)
npm audit fix

# See dependency tree
npm list --depth=0
```

### Dependency Selection Criteria

**MANDATORY Checklist (use web_search for verification):**

- [ ] **Maintenance Status**: Last commit < 6 months ago
- [ ] **Version**: Latest stable version identified
- [ ] **Security**: No known CVEs or vulnerabilities
- [ ] **License**: Compatible with project (check LICENSE file)
- [ ] **Popularity**: Good download stats / GitHub stars (not sole criteria)
- [ ] **Documentation**: Well-documented with examples
- [ ] **Dependencies**: Not too many transitive dependencies
- [ ] **Alternatives**: Evaluated 2-3 alternatives with pros/cons
- [ ] **Team Approval**: If adding new major dependency

**Red Flags to REJECT:**

- ❌ Last commit > 1 year ago (unmaintained)
- ❌ Open security vulnerabilities without patches
- ❌ Incompatible license (GPL in commercial project, etc.)
- ❌ Excessive dependencies (adds 50+ packages)
- ❌ Alpha/beta versions for production use
- ❌ No documentation or examples
- ❌ Deprecated by maintainers

## Bug Fixing Process (5-Category Taxonomy)

### Step 1: Bug Classification (MANDATORY)

**Before ANY code changes, classify the bug:**

```
1. SYNTAX/TYPO - truly localized, zero system implications
2. LOGIC (Localized) - contained in single function, clearly isolated
3. INTEGRATION - multiple components, data flow issues
4. ARCHITECTURAL - system-wide implications, design assumptions
5. REQUIREMENTS - behavior itself is wrong or unclear
```

**Use this decision tree:**

```
Is it a typo/syntax error?
├─ YES → Category 1
└─ NO ↓

Is expected behavior unclear or disputed?
├─ YES → Category 5 (clarify requirements first)
└─ NO ↓

Does it involve multiple components/services?
├─ YES → Likely Category 3 or 4
└─ NO ↓

Can you verify fix affects only one function with zero side effects?
├─ YES, CERTAIN → Category 2
└─ UNCERTAIN → Category 3 (analyze deeper)

Does it involve system-wide state, concurrency, or architecture?
├─ YES → Category 4
└─ NO → Re-evaluate, likely Category 3
```

**When uncertain: Escalate to higher category (treat as more complex)**

### Step 2: Category-Specific Approach

#### Category 1: Syntax/Typo Bugs

**Characteristics:**

- Missing semicolon, typo in variable name, incorrect import path
- Zero impact beyond the immediate syntax error

**Process:**

```bash
1. Identify syntax error
2. Fix immediately
3. Add regression test
4. Verify no side effects
5. Commit with clear message

# Example commit message:
fix: correct typo in variable name `usre` -> `user`

Category: 1 (Syntax)
Risk: Minimal
Test: Added unit test to catch similar typos
```

**Time Investment:** < 15 minutes

#### Category 2: Logic Bugs (Localized)

**Characteristics:**

- Off-by-one error, incorrect conditional, wrong calculation
- Contained within single function
- Clear isolation boundaries

**Process:**

```bash
1. Verify TRUE isolation (no side effects elsewhere)
2. Write failing test that demonstrates bug
3. Fix the logic
4. Verify test passes
5. Check for similar patterns in codebase
6. Commit with classification

# Example commit message:
fix: correct off-by-one error in pagination logic

Category: 2 (Logic - Localized)
Risk: Low
Isolation: Confirmed - only affects calculatePageOffset()
Similar Patterns: Checked 3 other pagination functions - all correct
Test: test_pagination_boundary_conditions added
```

**⚠️ CRITICAL VERIFICATION:**

- Grep codebase for similar patterns
- Check all callers of the function
- Verify assumptions about function isolation

**Time Investment:** 30 min - 2 hours

#### Category 3: Integration Bugs

**Characteristics:**

- API contract mismatch between services
- State synchronization issues
- Data transformation errors across boundaries
- Often MISCLASSIFIED as Category 2

**⚠️ WARNING: These are the MOST DANGEROUS to fix incorrectly**

- Commonly mistaken for localized logic bugs
- Fixing locally creates whack-a-mole cascade
- Requires understanding data flow across boundaries

**Process:**

```bash
1. STOP - Do not apply localized fix
2. Map data flow across ALL boundaries
3. Identify the interface/contract that's broken
4. Create design document for proper fix
5. Get design approval
6. Implement fix at INTERFACE level, not locally
7. Add comprehensive integration tests
8. Commit with full analysis

# Example commit message:
fix: resolve user data sync issue between auth and profile services

Category: 3 (Integration)
Risk: Medium-High
Root Cause: Auth service returns snake_case, profile expects camelCase
Analysis: Traced data flow through 3 services
Fix Location: Added transformation layer at service boundary
Tests: Integration test suite for auth->profile->frontend flow
Verified: All 5 data transformation points now consistent
```

**MANDATORY Steps:**

1. Diagram the data flow (can be ASCII art in notes)
2. Identify ALL transformation points
3. Fix at the boundary/interface
4. Never mask with localized transformations

**Time Investment:** 4-8 hours (includes design review)

#### Category 4: Architectural/Behavioral Bugs

**Characteristics:**

- Race conditions, incorrect state machine
- Wrong architectural pattern
- System-wide implications

**🔴 CRITICAL: NEVER fix these locally**

**Process:**

```bash
1. STOP - This requires full system analysis
2. Document current behavior across entire system
3. Identify the architectural assumption that's wrong
4. Create comprehensive design for fix
5. Get formal design approval
6. Implementation may require refactoring
7. Extensive testing including failure scenarios
8. Phased rollout if possible

# Example commit message:
refactor: fix race condition in order processing pipeline

Category: 4 (Architectural)
Risk: High
Root Cause: Assumed synchronous processing, but webhooks are async
System Impact: 5 services affected
Design Doc: docs/ADR-0042-async-order-processing.md
Implementation: Added event sourcing with idempotency
Tests: Added chaos testing and race condition detection
Rollout: Phased over 2 weeks with feature flag
```

**MANDATORY Requirements:**

- Architecture Decision Record (ADR)
- Full system flow documentation
- Design review with stakeholders
- Comprehensive test suite
- Rollback plan

**Time Investment:** 1-3 days (or more for complex systems)

#### Category 5: Requirements Bugs

**Characteristics:**

- Feature doesn't match actual user need
- Business logic is incorrect
- "Correct" behavior itself is disputed

**🔴 CRITICAL: Clarify requirements BEFORE any code**

**Process:**

```bash
1. STOP - Do not write any code
2. Document current behavior
3. Document expected behavior (gather evidence)
4. Identify the gap or misunderstanding
5. Consult with user/stakeholders
6. Get written clarification
7. THEN proceed to design -> implement

# Example commit message:
fix: update discount calculation to match business rules

Category: 5 (Requirements)
Risk: High (was implementing wrong behavior)
Clarification: Meeting with Product team 2024-11-14
Previous Understanding: Discount on pre-tax amount
Correct Understanding: Discount on post-tax amount for UAE compliance
Requirements Doc: Updated docs/business-rules/discounts.md
Tests: Updated to match corrected requirements
```

**MANDATORY Steps:**

- Get written requirements clarification
- Update requirements documentation
- Review with stakeholders before implementing

**Time Investment:** Varies (includes stakeholder meetings)

### Step 3: Root Cause Analysis (Categories 2-5)

**MANDATORY Before Fixing:**

```bash
# 1. Reproduce the bug consistently
# Write exact steps to reproduce

# 2. Gather evidence
# - Error messages and stack traces
# - Logs from all relevant services
# - Database state before/after
# - Network traffic if applicable

# 3. Form hypothesis about root cause
# - What component is actually failing?
# - Why is it failing?
# - When did it start? (check git history)

# 4. Verify hypothesis
# - Add logging to confirm
# - Write test that demonstrates the issue
# - Check if fix would affect other areas

# 5. Document findings
# - Update ticket/issue with analysis
# - Note any related issues found
# - List all affected components
```

**Anti-Patterns to AVOID:**

❌ **Trial-and-Error Fixing:**

```python
# BAD: Trying random fixes
if user:  # Maybe this will work?
    pass
elif user is not None:  # Or this?
    pass
# This masks the real issue!
```

❌ **Localized Fix for Integration Bug:**

```python
# BAD: Band-aid on Category 3 bug
def get_user():
    user = api.get_user()
    # Hack to fix None issue - but WHY is it None?
    if user is None:
        user = {"id": 0}  # This masks the real problem!
    return user
```

❌ **Assuming Behavior Without Research:**

```python
# BAD: Assuming library behavior
# Assuming cache.get() returns None on miss
# But maybe it raises KeyError? Check docs!
user = cache.get(user_id) or default_user
```

✅ **Correct Approach:**

```python
# GOOD: Research, understand, then fix properly
# Source: Redis-py docs v4.5.0 - get() returns None on miss
# https://redis-py.readthedocs.io/en/stable/
user = cache.get(user_id)
if user is None:
    user = db.get_user(user_id)
    cache.set(user_id, user, timeout=3600)
return user
```

### Step 4: Implementation Guidelines

**For ALL Categories:**

1. **Write Test First (TDD)**

   ```python
   def test_bug_fix():
       """
       Reproduces bug #1234: User data not syncing

       Category: 3 (Integration)
       Root Cause: Auth returns snake_case, profile expects camelCase
       """
       # Setup that reproduces bug
       auth_data = {"user_id": 1, "user_name": "alice"}

       # This should work but fails before fix
       profile = ProfileService.sync_from_auth(auth_data)

       assert profile.userId == 1  # Should map correctly
       assert profile.userName == "alice"
   ```

2. **Implement Fix with Evidence**

   ```python
   def sync_from_auth(auth_data: dict) -> Profile:
       """
       Sync profile from auth service data.

       Auth service returns snake_case (user_id, user_name)
       Profile uses camelCase (userId, userName)

       Source: Auth API docs v2.0 - /docs/api/auth#user-object
       Date: 2024-11-14
       """
       # Transform at boundary (Category 3 fix)
       profile_data = {
           "userId": auth_data["user_id"],
           "userName": auth_data["user_name"],
       }
       return Profile(**profile_data)
   ```

3. **Verify Fix Quality**

   ```bash
   # Run tests
   pytest tests/test_bug_1234.py -v

   # Check coverage
   pytest --cov=module tests/test_bug_1234.py

   # Verify no side effects
   pytest  # Run full test suite

   # Check for similar issues
   grep -r "auth_data\[" .  # Find other similar code
   ```

### Step 5: Emergency Bug Fix Protocol

**Only for production-down scenarios:**

**IMMEDIATE (< 5 minutes):**

```bash
# Apply minimal hotfix
git checkout -b hotfix/production-down
# Make minimal change to restore service
git commit -m "[EMERGENCY_FIX] Restore service by disabling feature X"
git push && deploy

# IMMEDIATELY create ticket
# Title: "Proper fix for [EMERGENCY_FIX] - Issue #1234"
```

**SHORT-TERM (< 24 hours):**

```bash
# Analyze using proper classification
# Determine if emergency fix masked Category 3-4 bug
# Schedule proper fix
```

**MEDIUM-TERM (< 1 week):**

```bash
# Implement proper solution
# Replace emergency fix
# Update monitoring
```

## Output Format

### 1. Initial Assessment

```
Bug Category: [1-5]
Risk Level: [Minimal/Low/Medium-High/High]
Estimated Time: [X hours/days]
Environment Type: [Docker/venv/bare metal]
Dependencies Involved: [List if applicable]
```

### 2. Environment Verification

```
✓ Development environment understood
✓ Dependency management approach identified
✓ Test execution method confirmed
✓ Deployment method documented
```

### 3. Root Cause Analysis (Categories 2-5)

```
Reproduction Steps:
1. [Exact steps]

Evidence Gathered:
- [Logs, errors, traces]

Hypothesis:
- [What's actually broken and why]

Verification:
- [How hypothesis was confirmed]

Components Affected:
- [List all affected areas]
```

### 4. Proposed Solution

```
Fix Strategy:
- [Category-appropriate approach]

Design Changes (if applicable):
- [Any design modifications needed]

Testing Strategy:
- [How fix will be tested]

Rollout Plan (for Category 4):
- [Phased approach if needed]
```

### 5. Implementation

```
# Code changes with evidence citations
# Tests written first
# Comprehensive comments
```

### 6. Verification Results

```
✓ All tests passing
✓ No side effects detected
✓ Similar patterns checked
✓ Documentation updated
✓ Commit message includes classification
```

## Quality Checklist

Before committing ANY fix:

- [ ] Bug properly classified (1-5)
- [ ] Root cause analysis completed (Categories 2-5)
- [ ] Development environment understood
- [ ] Dependencies researched if adding/changing
- [ ] Tests written FIRST (TDD)
- [ ] Fix implemented with evidence citations
- [ ] All tests passing (including full suite)
- [ ] No side effects verified
- [ ] Similar patterns in codebase checked
- [ ] Documentation updated if needed
- [ ] Commit message includes classification and reasoning

## Red Flags - STOP and Escalate

Stop immediately and escalate if you observe:

🚨 **Whack-a-Mole Pattern:**

- Same bug reappearing in different places
- Multiple "fixes" needed for same issue
- New bugs appearing after fix

🚨 **Uncertainty:**

- Can't classify bug confidently
- Root cause unclear after 4 hours research
- Multiple theories about what's wrong

🚨 **System-Wide Impact:**

- Fix would affect >3 components
- Architectural assumptions involved
- Breaking changes required

🚨 **Requirements Confusion:**

- Expected behavior is disputed
- Multiple stakeholders with different views
- No clear specification

## Critical Reminders

1. **Environment First**: Always understand dev environment before fixing
2. **Classify First**: Never start fixing without classification
3. **Research Dependencies**: Use web_search before adding ANY dependency
4. **No Trial-and-Error**: Research → Understand → Fix ONCE
5. **When in Doubt**: Higher category (treat as more complex)
6. **Mixed Environments**: Never edit files inside containers
7. **Latest Versions**: Always research current stable versions
8. **Evidence Required**: All fixes must cite sources
9. **Test First**: Write failing test before fixing
10. **Ask Don't Assume**: Cost of asking < cost of wrong fix

---

**Remember: Fast trial-and-error feels productive but creates bigger problems. Proper analysis and fixing takes longer upfront but saves time overall and prevents bug cascades.**
