# Contributing to Quantum Intelligence Newsletter

Internal team guidelines for development and collaboration on the Quantum Intelligence Newsletter project.

## Development Workflow

### 1. Branch Strategy

```bash
# Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# or for bug fixes
git checkout -b fix/bug-description
```

### 2. Making Changes

- Write clear, descriptive code with type hints
- Add docstrings for complex functions
- Follow PEP 8 style guide
- Keep functions focused and modular

### 3. Testing

**Before committing:**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=quantum_intel --cov-report=html

# Run specific test file
pytest tests/test_deduplication.py -v
```

**Testing Requirements:**
- All new utility functions must have unit tests
- Maintain >80% coverage for non-LLM code
- Mock external APIs (Tavily, Gemini, SMTP) in tests
- Add test cases for edge cases and error conditions

### 4. Code Quality

```bash
# Format code with black
black quantum_intel.py tests/

# Check linting with flake8
flake8 quantum_intel.py

# Sort imports
isort quantum_intel.py tests/
```

### 5. Committing

**Commit Message Format:**

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `chore`: Maintenance tasks

**Example:**

```
feat: Add support for Arxiv paper tracking

- Integrate Arxiv API for preprint search
- Add new graph node for academic paper filtering
- Update deduplication to handle DOI identifiers
- Add tests for Arxiv integration

Related to internal ticket #123
```

### 6. Pull Requests

**Before creating PR:**
- [ ] All tests pass
- [ ] Code is formatted with black
- [ ] No linting errors
- [ ] Documentation updated (if needed)
- [ ] CHANGELOG.md updated

**PR Template:**

```markdown
## What
Brief description of the change

## Why
Business/technical justification for the change

## How
Implementation approach and key technical decisions

## Testing
How you verified the changes work:
- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] Tested with production-like data

## Risks
Potential issues or breaking changes:
- None / List specific risks

## Checklist
- [ ] Tests pass
- [ ] Code formatted
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

## Code Style

### Python Style Guide

- **Follow PEP 8** for all Python code
- **Line length**: 100 characters (configured in black)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes for strings
- **Type hints**: Use for all function signatures

**Example:**

```python
def validate_url(url: str, timeout: int = 5) -> bool:
    """
    Validate if a URL is accessible and returns a successful status code.
    
    Args:
        url: The URL to validate
        timeout: Timeout in seconds (default: 5)
    
    Returns:
        True if URL is valid and accessible, False otherwise
    """
    try:
        # Implementation
        pass
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False
```

### Docstring Style

Use Google-style docstrings for functions with complex logic:

```python
def complex_function(param1: str, param2: int) -> Dict[str, Any]:
    """
    Brief one-line description.
    
    Longer description if needed, explaining the purpose and behavior.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When param2 is negative
    """
```

For simple functions, a single-line docstring is sufficient.

## Environment Management

### CRITICAL: Never Commit Credentials

**Pre-commit checklist:**
- [ ] `.env` is in `.gitignore` (verify: `git status --ignored | grep .env`)
- [ ] No API keys hardcoded in source files
- [ ] `.env.example` updated with new variables (values as placeholders)
- [ ] No sensitive data in logs or test files

**Search for accidentally committed secrets:**

```bash
# Search for potential API keys
grep -r "AIzaSy" --exclude=.env --exclude=.env.example .
grep -r "tvly-" --exclude=.env --exclude=.env.example .
```

### Virtual Environment

Always work in a virtual environment:

```bash
# Create
python3.13 -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Deactivate
deactivate
```

### Dependency Management

**Adding a new dependency:**

```bash
# Install package
pip install package-name

# Update requirements
pip freeze | grep package-name >> requirements.txt

# Or manually add to requirements.txt with version constraint
echo "package-name>=1.0.0" >> requirements.txt
```

**Update `.env.example` if adding environment variables:**

1. Add to `.env.example` with placeholder value
2. Document in README.md configuration table
3. Add to `NewsletterConfig` class if needed
4. Add test in `test_config.py`

## sent_articles.txt Management

This file **IS version controlled** for team consistency.

### Merge Conflict Resolution

When merging branches with different sent_articles.txt:

```bash
# Keep all unique URLs from both versions
# 1. Get both versions
git show HEAD:sent_articles.txt > sent_mine.txt
git show MERGE_HEAD:sent_articles.txt > sent_theirs.txt

# 2. Combine and deduplicate
cat sent_mine.txt sent_theirs.txt | sort | uniq > sent_articles.txt

# 3. Stage the merged file
git add sent_articles.txt
```

### Best Practices

- **Pull before running locally** to get latest article list
- **Commit after running** if new articles were added
- **Keep sorted** for easier diff review (optional)

## LLM Prompt Changes

When modifying prompts in `quantum_intel.py`:

**Locations of prompts:**
- Line 99-106: Snippet cleaning prompt
- Line 200-206: Company update prompt
- Line 340-350: Executive summary prompt

**Guidelines:**
1. **Document reasoning** in commit message
2. **Test with multiple runs** (LLM output varies)
3. **Update expected behavior** in ARCHITECTURE.md if significant
4. **Consider token usage** (longer prompts = higher cost)
5. **Preserve prompt structure** (role, context, instructions)

**Example commit:**

```
refactor: Improve executive summary prompt clarity

- Restructured prompt to emphasize trend identification
- Added explicit word count constraint (150 words)
- Removed redundant "focus on" instructions
- Tested across 5 runs for consistency

Rationale: Previous prompts sometimes exceeded 200 words
```

## Configuration Changes

When adding new environment variables:

1. **Add to `NewsletterConfig` class** (quantum_intel.py:47-58)
2. **Update `.env.example`** with placeholder
3. **Document in README.md** configuration table
4. **Add test in `test_config.py`**
5. **Update API_KEYS.md** if it's a credential

**Example:**

```python
# In NewsletterConfig
class NewsletterConfig:
    def __init__(self):
        # ... existing config ...
        self.new_setting = os.getenv("NEW_SETTING", "default_value")
```

## Release Process

### Version Numbers

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Creating a Release

1. **Update CHANGELOG.md:**

```markdown
## [1.1.0] - 2026-05-15

### Added
- New feature X

### Changed
- Improved feature Y

### Fixed
- Bug Z
```

2. **Update version in code** (add to quantum_intel.py header):

```python
__version__ = "1.1.0"
```

3. **Commit and tag:**

```bash
git add CHANGELOG.md quantum_intel.py
git commit -m "chore: Bump version to 1.1.0"
git tag v1.1.0
git push origin main --tags
```

4. **Notify team** via [internal communication channel]

## Troubleshooting Checklist

Before asking for help, verify:

1. **Check logs:**
   ```bash
   tail -f quantum_newsletter.log
   ```

2. **Verify environment variables:**
   ```bash
   # In Python
   import os
   from dotenv import load_dotenv
   load_dotenv()
   print(os.getenv("Gemini_API_Key"))  # Should print key (first few chars)
   ```

3. **Fresh virtual environment:**
   ```bash
   deactivate
   rm -rf venv
   python3.13 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Search existing issues:**
   - Check repository Issues tab
   - Search internal documentation

## Code Review Guidelines

### For Reviewers

Check for:
- [ ] **Test coverage** for new logic
- [ ] **No hardcoded credentials**
- [ ] **Error handling** for external APIs
- [ ] **Documentation updates** (README, docstrings)
- [ ] **Performance implications** (timeout values, API calls)
- [ ] **Type hints** for function signatures
- [ ] **Logging** for important operations

### For Authors

- Respond to feedback promptly
- Mark conversations as resolved after addressing
- Request re-review after substantial changes
- Don't take feedback personally - we're all learning

## Common Patterns

### Adding a New Company to Track

1. Update `.env`:
   ```
   COMPANIES_TO_TRACK=EvolutionQ,Qunnect,NewCompany
   ```

2. No code changes needed (config.companies_to_track reads from env)

3. Test manually to verify company update retrieval works

### Adding a New Search Query Category

Edit `retrieve_articles()` function (line 225-239):

```python
queries = [
    # ... existing queries ...
    f"new category keywords {date_filter}",
]
```

### Adjusting Deduplication Threshold

Edit `NewsletterConfig` class (line 56):

```python
self.title_similarity_threshold = 80  # Lowered from 85 for less strict matching
```

Document reasoning in commit message.

## Getting Help

- **Questions**: [Internal Slack channel / email]
- **Bug reports**: Create GitHub Issue with:
  - Steps to reproduce
  - Expected vs actual behavior
  - Relevant logs
  - Environment details (OS, Python version)
- **Feature requests**: Discuss with team before implementing

## License

All contributions are subject to SandboxAQ's proprietary license. See [LICENSE](../LICENSE) file.

---

**Last Updated**: 2026-05-02  
**Maintainers**: SandboxAQ Quantum Intelligence Team
