# Quantum Intelligence Newsletter Generator

Automated quantum networking and QKD newsletter generation system for SandboxAQ internal use.

## Overview

This LangGraph-powered agent automatically:
- Searches for latest quantum networking & QKD research/news
- Validates and deduplicates articles using fuzzy matching
- Tracks company investment updates (EvolutionQ, Qunnect)
- Generates executive summaries using Gemini AI
- Sends formatted HTML newsletters via email
- Maintains persistent deduplication state

**Technology Stack**: LangChain, LangGraph, Google Gemini AI, Tavily Search API

## Prerequisites

- Python 3.13+ (project uses 3.13)
- API Keys:
  - Google Gemini API key
  - Tavily Search API key
  - Gmail App Password (for SMTP)

See [docs/API_KEYS.md](docs/API_KEYS.md) for obtaining credentials.

## Installation

### 1. Clone Repository

```bash
git clone <internal-repo-url>
cd quantum_intel_project
```

### 2. Create Virtual Environment

```bash
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt

# For development/testing:
pip install -r requirements-dev.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

**Required Environment Variables** (see `.env.example`):
- `Gemini_API_Key`: Google Gemini API key
- `TAVILY_API_KEY`: Tavily search API key
- `EMAIL_USER`: Gmail address for sending
- `EMAIL_PASS`: Gmail app password
- `EMAIL_RECIPIENT`: Recipient email address
- `COMPANIES_TO_TRACK`: Comma-separated company list (default: EvolutionQ,Qunnect)

## Usage

### Manual Execution

```bash
# Activate virtual environment
source venv/bin/activate

# Run newsletter generation
python quantum_intel.py
```

### Using Shell Script

```bash
# Run via script
./scripts/run_newsletter.sh
```

### Output Files

After execution:
- `quantum_newsletter_output.md`: Generated newsletter content
- `quantum_newsletter.log`: Detailed execution logs
- `newsletter_stats.json`: Processing statistics
- `sent_articles.txt`: Updated with new article URLs (version controlled)

## Configuration

Customize behavior via environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_ARTICLES` | 10 | Maximum articles per newsletter |
| `SEARCH_TIMEOUT` | 5 | Search API timeout (seconds) |
| `LINK_VALIDATION_TIMEOUT` | 5 | URL validation timeout |
| `COMPANIES_TO_TRACK` | EvolutionQ,Qunnect | Companies for investment updates |
| `PREVIOUS_ARTICLES_FILE` | sent_articles.txt | Deduplication persistence file |
| `OUTPUT_FILE` | quantum_newsletter_output.md | Output filename |

Advanced configuration in `NewsletterConfig` class (quantum_intel.py:47-58).

## Architecture

### LangGraph Workflow

```
search → deduplicate → summarize → investments → compose → send_and_save → update_persistence
```

**Node Functions**:

1. **search**: Tavily API queries across academic, industry, government sources
2. **deduplicate**: URL + fuzzy title matching (85% threshold)
3. **summarize**: Gemini-generated executive summary
4. **investments**: Dynamic company update retrieval
5. **compose**: Markdown newsletter assembly
6. **send_and_save**: Email delivery + file output
7. **update_persistence**: Append new URLs to sent_articles.txt

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design.

## Deduplication Strategy

Two-layer approach:
1. **URL-based**: Checks against `sent_articles.txt` (historical URLs)
2. **Title-based**: Fuzzy matching with 85% similarity threshold (thefuzz library)

This prevents duplicate content even when articles appear on multiple sites.

**Example**: "Quantum Computing Advances in 2026" and "Quantum Computing Advances 2026" are detected as duplicates (90% similarity).

## Testing

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_deduplication.py

# With coverage
pytest --cov=quantum_intel --cov-report=html
```

Test coverage focuses on core functions (validation, deduplication, formatting, persistence). LLM/API integration is mocked.

## Troubleshooting

### Common Issues

**"404 Model Not Found" Error**:
- Verify Gemini model name (currently `gemini-2.5-flash` in line 63)
- Check API key validity at https://makersuite.google.com/app/apikey
- Ensure langchain-google-genai supports the model version

**SMTP Authentication Failed**:
- Use Gmail App Password, not account password
- Enable 2FA and generate app-specific password at https://myaccount.google.com/apppasswords
- Verify EMAIL_USER and EMAIL_PASS in .env

**No Articles Found**:
- Check Tavily API quota/rate limits
- Review search timeout settings (increase SEARCH_TIMEOUT if needed)
- Verify internet connectivity
- Check logs in `quantum_newsletter.log` for specific errors

**Deduplication Too Aggressive**:
- Lower `title_similarity_threshold` in `NewsletterConfig` (line 56)
- Default is 85%; try 80% for less strict matching
- Review `sent_articles.txt` for unexpected entries

**Email Not Sending**:
- Verify SMTP settings (default: smtp.gmail.com:465)
- Check firewall/network restrictions
- Test with: `telnet smtp.gmail.com 465`

See logs in `quantum_newsletter.log` for detailed diagnostics.

## Project Structure

```
quantum_intel_project/
├── quantum_intel.py           # Main application (540 lines)
├── sent_articles.txt          # Deduplication state (version controlled)
├── scripts/
│   └── run_newsletter.sh      # Execution script
├── tests/                     # Unit tests
│   ├── test_validation.py
│   ├── test_deduplication.py
│   ├── test_formatting.py
│   ├── test_config.py
│   ├── test_persistence.py
│   └── fixtures/
│       └── sample_articles.json
├── docs/                      # Additional documentation
│   ├── ARCHITECTURE.md
│   ├── CONTRIBUTING.md
│   └── API_KEYS.md
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
├── .gitignore
├── .env.example
└── LICENSE
```

## Security

⚠️ **CRITICAL**: Never commit `.env` file - contains sensitive API keys and credentials.

**Security Checklist**:
- [ ] `.env` is in `.gitignore`
- [ ] No API keys hardcoded in source files
- [ ] `.env.example` contains only placeholder values
- [ ] Gmail App Password used (not account password)

Report security concerns to your team lead or security contact.

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for internal team guidelines on:
- Development workflow (branches, commits, PRs)
- Code style requirements (PEP 8, black)
- Testing requirements (>80% coverage)
- Environment management
- Documentation standards

## License

Proprietary - SandboxAQ Internal Use Only

See [LICENSE](LICENSE) file for details.

## Support

**Issues**: Create an issue in this repository

**Questions**: Contact the team via [internal communication channel]

**Documentation**: See `docs/` directory for additional guides

---

**Last Updated**: 2026-05-02  
**Maintainer**: SandboxAQ Quantum Intelligence Team
