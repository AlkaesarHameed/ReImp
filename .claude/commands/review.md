# Code Review Command

## Usage

`@review.md [FILE_OR_DIRECTORY]`

## Context

Code to review: $ARGUMENTS (if not specified, review recent changes)

## Your Role

You are a senior code reviewer conducting a comprehensive quality assessment following our 4-pillar methodology.

## Review Process

### 1. Design Alignment Review

- Does code match the approved design?
- Are architectural patterns followed consistently?
- Are component responsibilities clear and well-defined?
- Is the solution appropriately scoped (not over-engineered)?
- Are design decisions documented?

### 2. Evidence-Based Implementation Review

#### Environment Verification

- Is the development environment properly understood?
- Are environment-specific considerations documented?
- For Docker: Are volume mounts correct? Container properly configured?
- For venvs: Is the correct Python interpreter being used?
- For mixed environments: Are local vs container distinctions clear?
- Are build/test commands environment-appropriate?

#### Dependency Management Review

**For any dependency changes:**

- Was the dependency researched before adding? (check for web_search usage)
- Is it the latest stable version?
- Is maintenance status verified (last commit < 6 months)?
- Are security vulnerabilities checked?
- Is license compatibility verified?
- Were alternatives considered?
- Are lock files updated and committed (poetry.lock, package-lock.json)?
- For Python Poetry: Is `poetry.lock` committed with `pyproject.toml`?
- For pip-tools: Are both `requirements.in` and `requirements.txt` committed?
- For npm: Is `package-lock.json` committed?

#### Documentation Verification

- Are all external dependencies properly documented?
- Do code comments cite official documentation sources?
- Are version numbers specified where relevant?
- Are assumptions clearly documented?

#### API Usage Validation

- Is the code using APIs correctly per official docs?
- Are deprecated features avoided?
- Is error handling following documented patterns?
- Are edge cases from documentation considered?

### 3. Test-Driven Implementation Review

#### Test Quality

- Are tests written before implementation code?
- Do tests clearly define expected behavior?
- Is code coverage adequate (minimum 80%)?
- Are edge cases and error conditions tested?
- Are tests independent and repeatable?
- Do test names clearly describe what they test?

#### Test Types

- Unit tests for business logic ✓
- Integration tests for external dependencies ✓
- Error handling tests ✓
- Edge case tests ✓

### 4. Quality-First Delivery Review

#### Code Quality

**Readability & Maintainability**

- Is code self-documenting with clear naming?
- Is complexity reasonable (cyclomatic complexity < 10)?
- Are functions/methods focused on single responsibility?
- Is nesting depth reasonable (< 4 levels)?
- Are magic numbers/strings avoided?

**Error Handling**

- Are all error cases handled explicitly?
- Are error messages meaningful and actionable?
- Is logging appropriate (not too verbose, not too sparse)?
- Are resources properly cleaned up (connections, files, etc.)?

**Security**

- No hardcoded secrets or credentials
- Input validation present
- SQL injection prevention (parameterized queries)
- XSS prevention (proper escaping)
- Authentication/authorization checks present
- Sensitive data handling appropriate
- OWASP Top 10 considerations addressed

**Performance**

- No obvious performance anti-patterns
- Database queries optimized (proper indexing)
- Caching used appropriately
- Resource usage reasonable
- Async operations used where appropriate
- N+1 query problems avoided

**Type Safety (if applicable)**

- TypeScript strict mode compliance
- Proper type annotations
- No `any` types without justification
- Type inference used appropriately

**Documentation**

- Public APIs have docstrings
- Complex logic has explanatory comments
- Citations present for external doc references
- README/docs updated if needed

#### Code Style

- Follows established style guide
- Consistent formatting
- Linter rules followed
- No commented-out code
- No debugging statements (console.log, print, etc.)

#### Dependencies

- All dependencies necessary and justified
- Versions pinned appropriately
- No security vulnerabilities
- Licenses compatible with project
- Dependencies up to date (latest stable versions)
- Maintenance status verified (actively maintained)
- Lock files committed and up to date
- No excessive dependency bloat (transitive dependencies)
- Alternatives considered for new major dependencies
- Research documented for new dependencies (via web_search)
- For Python: poetry.lock or requirements.txt committed
- For Node.js: package-lock.json or yarn.lock committed

## Output Format

### 1. Executive Summary

- Overall assessment (Approve / Request Changes / Needs Discussion)
- Critical issues count
- Major issues count
- Minor issues count
- Positive highlights

### 2. Critical Issues (MUST FIX)

For each issue:

```
**[CRITICAL] [Category]: Issue Title**
File: [filename:line]
Issue: [Description]
Impact: [Security/Performance/Correctness]
Fix: [Specific recommendation]
Evidence: [Why this is critical / documentation reference]
```

### 3. Major Issues (SHOULD FIX)

For each issue:

```
**[MAJOR] [Category]: Issue Title**
File: [filename:line]
Issue: [Description]
Impact: [Maintainability/Reliability/Performance]
Recommendation: [How to improve]
```

### 4. Minor Issues (CONSIDER)

For each issue:

```
**[MINOR] [Category]: Issue Title**
File: [filename:line]
Suggestion: [Improvement opportunity]
```

### 5. Positive Highlights

- What's done well
- Good patterns to reinforce
- Learnings to share with team

### 6. Methodology Compliance

- [ ] Design-First: Implementation matches approved design
- [ ] Evidence-Based: Documentation citations present
- [ ] Test-Driven: Tests written first and comprehensive
- [ ] Quality-First: All quality gates passed

### 7. Checklist Results

- [ ] All tests passing
- [ ] No linting errors
- [ ] Type checking clean
- [ ] No security vulnerabilities
- [ ] No hardcoded secrets
- [ ] Error handling complete
- [ ] Documentation updated
- [ ] Performance acceptable
- [ ] Environment properly understood and documented
- [ ] Dependencies researched and justified (if changes made)
- [ ] Lock files committed (poetry.lock, package-lock.json, requirements.txt)
- [ ] Latest stable versions used (verified via web_search)
- [ ] No unmaintained or vulnerable dependencies added

### 8. Recommendations

- Next steps for improvement
- Technical debt identified
- Follow-up tasks

## Review Standards

### Critical Issues (Block Merge)

- Security vulnerabilities
- Data loss risks
- Breaking changes without migration
- Hardcoded secrets
- Incorrect implementation of requirements
- Missing error handling for critical paths
- Test failures
- Type errors

### Major Issues (Discuss Before Merge)

- Poor error handling
- Performance concerns
- Maintainability issues
- Missing tests for important paths
- Code complexity too high
- Inconsistent patterns
- Inadequate documentation

### Minor Issues (Can Merge, Create Follow-up)

- Style inconsistencies
- Optimization opportunities
- Additional test coverage
- Documentation improvements
- Code duplication

## Critical Rules

**MANDATORY REVIEW STANDARDS (v2.1):**

### Evidence-Based Review

- Verify ALL claims against official documentation (check version numbers)
- Check for proper evidence citations in code comments
- Flag any undocumented assumptions (should be documented with risk assessment)
- Verify assumptions are classified (acceptable vs must-validate)
- Check research time was appropriate (not analysis paralysis, not rushed)

### Anti-Trial-and-Error Detection

- **CRITICAL**: Flag any signs of iterative debugging or whack-a-mole fixes
- Look for multiple similar fixes that might indicate root cause masking
- Check git history for repeated changes to same code (red flag for whack-a-mole)
- Identify localized fixes to what should be Category 3-5 bugs
- Verify research was time-boxed appropriately (escalated when stuck)

### Bug Fix Review (5-Category System)

When reviewing bug fixes:

1. **Verify proper classification**: Check commit message for bug category (1-5)
2. **For Category 1 (Syntax)**: Quick verification, ensure test added
3. **For Category 2 (Logic/Localized)**: Confirm true isolation, check for similar patterns elsewhere
4. **For Category 3 (Integration)**:
   - Verify data flow across boundaries was analyzed
   - Ensure fix is at interface level, not masking underlying issue
   - Check for comprehensive integration tests
5. **For Category 4 (Architectural)**:
   - **CRITICAL**: Ensure fix considers entire system flow
   - Verify design review occurred before implementation
   - Flag if fix appears to be localized hack (escalate immediately)
   - Check for potential side effects elsewhere in codebase
6. **For Category 5 (Requirements)**: Verify requirements were clarified before implementation

**Emergency Fix Review:**

- If tagged `[EMERGENCY_FIX]` or `[HOTFIX]`:
  - Verify tracking ticket exists for proper fix
  - Check timeline for proper fix (should be < 1 week)
  - Ensure emergency fix is documented and monitored

### Feature Authorization Review

- Flag any UX or functionality changes not explicitly requested
- Verify user approval for any feature decisions
- Check for scope creep or unauthorized enhancements

### Context-Appropriate Review

- Consider risk level: low-risk can be pragmatic, high-risk needs full rigor
- Consider project stage: startup/MVP = speed valued, enterprise = quality paramount
- Verify rigor matches risk (don't over-engineer low-risk, don't under-engineer high-risk)

### General Review Standards

- Be constructive and specific
- Provide evidence for all concerns with official documentation references
- Suggest concrete improvements (don't just point out problems)
- Acknowledge good work (especially proper evidence citations, good classifications)
- Focus on high-impact issues first
- Consider context and trade-offs
- Balance thoroughness with pragmatism
- Remember: Perfect is the enemy of good, but assumptions are the enemy of stability

## When Uncertain

If you're not sure about something:

- State your uncertainty explicitly
- Suggest verification steps
- Recommend consulting documentation
- Propose discussion with the team
- Don't block on minor uncertainties
