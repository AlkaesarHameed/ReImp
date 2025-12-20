# ADR-002: Use Poetry for Dependency Management

**Status**: Accepted

**Date**: 2025-11-14

**Deciders**: Project Lead

---

## Context

Python projects require reliable dependency management to ensure:

- Deterministic builds (same dependencies across all environments)
- Easy dependency updates with version locking
- Separation of production and development dependencies
- Virtual environment management
- Package publishing capabilities (if needed)

Traditional approaches (pip + requirements.txt or pip-tools) have limitations in dependency resolution and workflow complexity.

## Decision

We will use **Poetry 2.2+** for dependency management and virtual environment handling.

**Key reasons:**

1. **Deterministic Dependency Resolution**: Resolves all transitive dependencies and locks versions
2. **pyproject.toml Standard**: Uses modern PEP 518 configuration (no setup.py needed)
3. **Automatic Lock File**: `poetry.lock` ensures identical environments across dev/staging/prod
4. **Dependency Groups**: Clean separation of dev/test/docs/prod dependencies
5. **Virtual Environment Management**: Automatic venv creation and activation
6. **Version Bumping**: Built-in semantic versioning support
7. **Ecosystem Adoption**: Industry standard for modern Python projects

## Consequences

### Positive

- **Reproducible Builds**: `poetry.lock` guarantees same dependencies everywhere
- **Simplified Workflow**: Single `poetry install` command for all environments
- **Faster Dependency Resolution**: Poetry's resolver is faster than pip's
- **Type Safety**: pyproject.toml schema validation catches configuration errors
- **Security**: Built-in vulnerability scanning with `poetry audit`
- **Developer Experience**: Clear `poetry add/remove/update` commands
- **Platform Independence**: Works consistently on Linux, macOS, Windows

### Negative

- **Learning Curve**: Developers familiar with pip need to learn Poetry commands
- **Additional Tool**: Requires Poetry installation (not just pip)
- **Lock File Size**: `poetry.lock` can be large for projects with many dependencies
- **Slower Installation**: First-time installs can be slower due to full resolution

### Neutral

- **Lock File in Git**: `poetry.lock` must be committed (adds to repo size)
- **Migration Effort**: Moving from pip requires converting requirements.txt

## Alternatives Considered

### Alternative 1: pip + requirements.txt

**Description**: Standard Python package manager with requirements files

**Pros**:

- Built into Python (no additional install)
- Universal understanding
- Simple workflow

**Cons**:

- No dependency resolution (conflicts discovered at install time)
- Requires manual lock file generation (`pip freeze`)
- No separation of dev/prod dependencies (requires multiple files)
- Manual virtual environment management

**Why rejected**: Lack of deterministic dependency resolution

### Alternative 2: pip-tools (pip-compile)

**Description**: Wrapper around pip providing compilation and locking

**Pros**:

- Deterministic builds with `.txt` lock files
- Compatible with existing pip workflows
- Lightweight layer on top of pip

**Cons**:

- Requires separate tools for dependency resolution and installation
- More complex workflow (compile → sync)
- No virtual environment management
- Less user-friendly than Poetry

**Why rejected**: More complex workflow and lacks integrated venv management

### Alternative 3: Pipenv

**Description**: Official Python.org recommended dependency manager

**Pros**:

- Deterministic with Pipfile.lock
- Virtual environment management
- Security scanning built-in

**Cons**:

- **Development Stalled**: Last major release in 2022, community concerns about maintenance
- Slower dependency resolution than Poetry
- Lock file format less portable
- Smaller ecosystem adoption

**Why rejected**: Maintenance concerns and slower performance

## Implementation Notes

**Current Implementation:**

```bash
# Install dependencies
poetry install                    # All dependencies (including dev)
poetry install --only main       # Production only

# Add dependencies
poetry add fastapi               # Production dependency
poetry add --group dev pytest    # Dev dependency

# Update dependencies
poetry update                    # Update all within constraints
poetry update fastapi            # Update specific package

# Lock dependencies
poetry lock --no-update          # Update lock file without upgrading
```

**Project Configuration** (`pyproject.toml`):

```toml
[tool.poetry]
name = "python-project-starter"
version = "0.1.0"
description = "Production-ready Python FastAPI starter template"
authors = ["Your Name <email@example.com>"]

[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.121.2"
# ... production dependencies

[tool.poetry.group.dev.dependencies]
pytest = "^8.3.4"
ruff = "^0.8.4"
# ... development dependencies
```

**Critical Files:**

- `pyproject.toml`: Dependency specifications (version constraints)
- `poetry.lock`: Locked dependency versions (MUST be committed to git)
- `.venv/`: Virtual environment (gitignored, auto-created by Poetry)

**Migration Strategy** (if moving from pip):

1. Export current dependencies: `pip freeze > requirements-backup.txt`
2. Initialize Poetry: `poetry init`
3. Add dependencies: `poetry add $(cat requirements.txt | grep -v '^#')`
4. Test installation: `poetry install`
5. Verify app works: `poetry run python -m src.api.main`
6. Commit `pyproject.toml` and `poetry.lock`

**Key Rules:**

- ✅ **ALWAYS commit poetry.lock** (applications need deterministic builds)
- ✅ Use `poetry add` to add dependencies (updates both files)
- ✅ Use `poetry update` to upgrade dependencies (not `poetry lock`)
- ✅ Run `poetry check` before committing to validate configuration
- ❌ **NEVER edit poetry.lock manually**
- ❌ **NEVER commit .venv/** directory

## References

- [Poetry Official Documentation](https://python-poetry.org/docs/)
- [PEP 518 - pyproject.toml specification](https://peps.python.org/pep-0518/)
- [Poetry vs pip comparison](https://python-poetry.org/docs/main/basic-usage/)
- [Why commit poetry.lock](https://python-poetry.org/docs/basic-usage/#commit-your-poetrylock-file-to-version-control)

---

## Revision History

| Date       | Author       | Changes                               |
| ---------- | ------------ | ------------------------------------- |
| 2025-11-14 | Project Lead | Initial ADR documenting Poetry choice |
