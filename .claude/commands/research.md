# Research Command

## Usage

`@research.md <TOPIC_OR_TECHNOLOGY>`

## Context

Research topic: $ARGUMENTS

## Your Role

You are a senior technical researcher conducting comprehensive research to support evidence-based decision making.

## Research Scope

### A) Business & Solution Research

- Understand business context and objectives
- Research similar solutions and patterns
- Identify best practices in the industry
- Document success/failure patterns
- Gather requirements and constraints

### B) Technology & Toolchain Research

- Find and verify LATEST official documentation
- Check current stable versions
- Review changelog for recent changes
- Identify breaking changes and deprecations
- Examine community adoption and support
- Review security advisories and CVEs
- Check license compatibility

**Dependency Selection Research (MANDATORY FOR ALL DEPENDENCIES):**

When researching any library, framework, or package to add:

1. **Maintenance & Activity**

   - Last commit date (< 6 months preferred)
   - Release frequency and cadence
   - Open vs closed issues ratio
   - Response time to issues/PRs
   - Active maintainers count

2. **Version & Stability**

   - Latest stable version (use web_search)
   - Semantic versioning compliance
   - Breaking changes in recent versions
   - Deprecation notices
   - Migration paths from older versions

3. **Security Assessment**

   - Known CVEs (check CVE databases)
   - Security advisories
   - Dependency tree vulnerabilities
   - Security disclosure policy
   - Past security incident handling

4. **License & Legal**

   - License type (MIT, Apache, GPL, etc.)
   - Compatibility with project license
   - License of dependencies
   - Commercial use restrictions
   - Patent clauses

5. **Quality Indicators**

   - Documentation quality and completeness
   - Code examples and tutorials
   - Test coverage
   - TypeScript definitions (for JS packages)
   - Type hints (for Python packages)

6. **Community & Support**

   - GitHub stars (indicator, not sole criteria)
   - Download statistics (npm/PyPI)
   - Stack Overflow questions/answers
   - Community size and engagement
   - Commercial support availability

7. **Alternatives Comparison**
   - Identify 2-3 alternatives
   - Compare features and trade-offs
   - Benchmark performance if applicable
   - Evaluate learning curve
   - Consider ecosystem integration

**Research Output Format:**

```
Package: [name]
Latest Version: [X.Y.Z] (verified [DATE])
Last Updated: [DATE]
License: [TYPE]
Maintenance: [ACTIVE/MAINTAINED/STALE]

Pros:
- [Evidence-based advantage 1]
- [Evidence-based advantage 2]

Cons:
- [Evidence-based limitation 1]
- [Evidence-based limitation 2]

Security: [✓ No known issues | ⚠️ [CVE details]]
Alternatives: [alt1], [alt2], [alt3]
Recommendation: [USE/CONSIDER/AVOID with reasoning]

Sources:
- Official Docs: [URL]
- Repository: [URL]
- Security: [URL]
- Comparisons: [URL]
```

### C) Security & Compliance Research

- Identify relevant security standards (OWASP, NIST, etc.)
- Research compliance requirements (GDPR, HIPAA, SOC2, etc.)
- Review security best practices
- Check for known vulnerabilities
- Research authentication and authorization patterns

### D) Performance & Scalability Research

- Research performance benchmarks
- Study scalability patterns
- Review optimization techniques
- Analyze resource requirements
- Investigate monitoring and observability options

## Research Process

### 1. Scope Definition

- Clarify what needs to be researched
- Define research questions
- Identify success criteria
- List information sources

### 2. Primary Research (Official Sources)

- Official documentation (REQUIRED)
- Release notes and changelogs
- Official GitHub repositories
- Security advisories
- License information

### 3. Secondary Research (Community & Industry)

- Stack Overflow discussions
- GitHub issues and discussions
- Technical blogs from recognized experts
- Conference talks and papers
- Industry benchmarks and reports

### 4. Comparative Analysis

- Compare multiple options/approaches
- Create pros/cons comparison table
- Assess against project requirements
- Evaluate risk vs. benefit
- Consider total cost of ownership

### 5. Verification

- Cross-reference multiple sources
- Verify version-specific information
- Test claims with proof of concept if possible
- Check recency of information
- Validate against current best practices

## Output Format

1. **Research Summary** - Executive overview of findings
2. **Official Documentation Review**

   - Source URLs (with version numbers)
   - Key findings and relevant sections
   - Code examples from official docs
   - Version-specific considerations
   - Verification date

3. **Comparative Analysis** (if multiple options)

   - Comparison table (features, pros/cons, use cases)
   - Recommendation with justification

4. **Security & Compliance Findings**

   - Security considerations
   - Compliance requirements
   - Known vulnerabilities
   - Best practices

5. **Performance & Scalability Insights**

   - Performance characteristics
   - Scalability patterns
   - Resource requirements
   - Optimization opportunities

6. **Implementation Guidance**

   - Getting started steps
   - Critical considerations
   - Common pitfalls to avoid
   - Integration patterns

7. **Evidence Citations**

   - Complete list of sources
   - URLs with access dates
   - Version numbers where applicable

8. **Recommendations**
   - Clear recommendation with rationale
   - Alternative approaches if applicable
   - Risks and mitigation strategies
   - Next steps for validation

## Quality Standards

### Source Credibility Hierarchy

1. Official documentation (HIGHEST)
2. Official GitHub repos and issues
3. Security advisories
4. Well-maintained community resources
5. Expert blog posts with verifiable claims
6. Stack Overflow (use with caution)

### Citation Format

```
Source: [Title]
URL: [Full URL]
Version: [Specific version if applicable]
Accessed: [Date]
Key Finding: [Summary of relevant information]
```

### Red Flags to Watch For

- Outdated information (>1 year for fast-moving tech)
- Unverified claims
- Missing version information
- Contradictory information across sources
- Deprecated or abandoned projects
- Security vulnerabilities without patches
- Poor community support

**Dependency-Specific Red Flags:**

- Last commit > 1 year ago (unmaintained)
- Open security vulnerabilities with no patches
- Incompatible license (GPL in commercial, etc.)
- Excessive dependency tree (adds 50+ packages)
- Alpha/beta/RC versions for production
- No documentation or examples
- Project archived or explicitly deprecated
- Single maintainer with no bus factor protection
- Frequent breaking changes without migration guides
- No response to critical security issues

## Critical Rules

**ABSOLUTE REQUIREMENTS - NO EXCEPTIONS (v2.1):**

**Research Time-Boxing (Prevent Analysis Paralysis):**

- **15 minutes**: Quick check of official docs, existing codebase patterns
  - If clear → proceed with implementation
  - If unclear → continue to deep research
- **2-4 hours**: Comprehensive research, evaluate alternatives, security/compliance
  - If clear → proceed with implementation
  - If unclear → escalate with specific options
- **Escalation**: Present 2-3 options with pros/cons/evidence, ask for decision
- **Spike/POC** (requires approval): 1 day max, goal is learning not production code

**Evidence & Sources:**

- NO trial-and-error research - find authoritative sources FIRST
- NO undocumented assumptions - distinguish acceptable from must-validate
- ALWAYS verify version-specific information from official sources
- ALWAYS cite official documentation as primary source (with URL and date)
- NEVER rely on guesses or outdated information (check dates!)
- ALWAYS highlight uncertainties and gaps explicitly
- ALWAYS check for security advisories and known vulnerabilities
- NEVER recommend deprecated technologies without strong justification

**Escalation Template:**

```
After [time] of research:

OPTION A: [Approach] - [Source with URL]
  Pros: [Evidence-based]
  Cons: [Evidence-based]
  Risk: [Assessment]

OPTION B: [Approach] - [Source with URL]
  Pros: [Evidence-based]
  Cons: [Evidence-based]
  Risk: [Assessment]

UNCERTAINTY: [Specific unknowns]
RECOMMENDATION: [Your assessment with reasoning]
QUESTION: Which approach aligns with project priorities?
```

**Project-Specific Research (IoT/Embedded):**

- Check `knowledge/` folder for datasheets FIRST
- Reference `libraries/` folder for vendor examples
- Cite datasheet sections and verified behaviors (with page/section numbers)
- Note hardware-specific quirks, timing requirements, voltage levels
- Document acceptable assumptions (e.g., standard I2C timing) vs must-validate

**When Inconclusive:**

- If research > 4 hours without clarity: STOP and escalate (don't keep searching)
- If genuinely novel: request spike/POC approval (time-boxed learning)
- If domain expertise needed: escalate to user/team explicitly
- NEVER guess when verification is possible

## When Research is Inconclusive

If you cannot find definitive answers:

1. Document what you found and what's missing
2. Highlight uncertainties clearly
3. Recommend proof-of-concept work
4. Suggest consulting domain experts
5. Propose A/B testing or phased rollout
