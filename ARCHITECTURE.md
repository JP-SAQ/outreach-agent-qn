# Quantum Intelligence Newsletter - Architecture

System design and technical architecture documentation for the Quantum Intelligence Newsletter Generator.

## System Overview

The Quantum Intelligence Newsletter is an **autonomous LangGraph-based agent** that automatically discovers, curates, and distributes quantum networking and QKD research news. The system uses a graph-based workflow orchestration pattern to manage complex multi-step processes including web search, content validation, deduplication, summarization, and delivery.

**Key Characteristics:**
- **Autonomous**: Runs without human intervention
- **Intelligent**: Uses LLM for content understanding and generation
- **Persistent**: Maintains state across runs to prevent duplicates
- **Resilient**: Error handling and logging throughout
- **Configurable**: Environment-based configuration for flexibility

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Orchestration** | LangGraph | Workflow state management and execution |
| **LLM** | Google Gemini 2.5 Flash | Content summarization and cleaning |
| **Search** | Tavily Search API | Web search for quantum news |
| **String Matching** | thefuzz + Levenshtein | Fuzzy title deduplication |
| **Email** | Python smtplib | Newsletter delivery |
| **Config** | python-dotenv | Environment variable management |
| **HTTP** | requests | URL validation |
| **Language** | Python 3.13 | Core implementation |

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Quantum Intel Agent                         │
│                                                                  │
│  ┌──────────┐    ┌────────────┐    ┌─────────────┐            │
│  │  Search  │───▶│ Deduplicate │───▶│ Summarize   │            │
│  └──────────┘    └────────────┘    └─────────────┘            │
│       │                                     │                    │
│       │                                     ▼                    │
│       │          ┌────────────┐    ┌─────────────┐            │
│       └─────────▶│ Investments │───▶│   Compose   │            │
│                  └────────────┘    └─────────────┘            │
│                                             │                    │
│                                             ▼                    │
│                  ┌────────────┐    ┌─────────────┐            │
│                  │   Update   │◀───│ Send & Save │            │
│                  │Persistence │    └─────────────┘            │
│                  └────────────┘                                 │
└─────────────────────────────────────────────────────────────────┘
           │                              │
           ▼                              ▼
    ┌──────────────┐            ┌──────────────────┐
    │ External APIs │            │   Output Files   │
    │ - Tavily      │            │ - Newsletter MD  │
    │ - Gemini      │            │ - Stats JSON     │
    │ - Gmail SMTP  │            │ - Log files      │
    └──────────────┘            │ - sent_articles  │
                                 └──────────────────┘
```

## LangGraph Workflow

### State Definition

```python
class AgentState(TypedDict):
    messages: List[BaseMessage]          # Communication messages
    new_articles: List[Dict]             # Raw articles from search
    deduped_articles: List[Dict]         # Deduplicated articles
    investment_updates: Dict[str, str]   # Company news
    executive_summary: str               # LLM-generated summary
    errors: List[str]                    # Error tracking
    processing_stats: Dict[str, int]     # Metrics
```

### Node Functions

#### 1. **search** (retrieve_articles)
**Location**: `quantum_intel.py:218-284`

**Purpose**: Discover relevant quantum networking articles via web search

**Process**:
1. Generate 9 diverse search queries (academic, industry, government)
2. Apply date filter (past 30 days)
3. Execute Tavily search for each query
4. Deduplicate by URL (within search results)
5. Filter out non-article URLs (tag pages, categories)
6. Validate URLs are accessible (HTTP HEAD requests)
7. Clean snippets using LLM
8. Limit to 2× max_articles for deduplication buffer

**Outputs**:
- `state["new_articles"]`: List of validated articles
- `state["processing_stats"]["articles_found"]`: Count

**Error Handling**:
- Search failures logged, continue with partial results
- URL validation timeouts handled gracefully
- LLM snippet cleaning falls back to raw snippet

#### 2. **deduplicate** (deduplicate_articles)
**Location**: `quantum_intel.py:287-323`

**Purpose**: Remove duplicate articles using URL and title matching

**Process**:
1. **URL-based dedup**: Remove articles in `sent_articles.txt`
2. **Title-based dedup**: Fuzzy string matching (85% threshold)
   - Uses thefuzz.fuzz.ratio for similarity score
   - Case-insensitive comparison
   - Keeps first occurrence, discards duplicates
3. Limit to `config.max_articles` (default: 10)

**Deduplication Logic**:
```python
for article in url_deduped_articles:
    for seen_title in seen_titles:
        similarity = fuzz.ratio(article['title'].lower(), seen_title.lower())
        if similarity > 85:
            # Discard as duplicate
            break
```

**Outputs**:
- `state["deduped_articles"]`: Final article list
- `state["processing_stats"]["articles_after_url_dedup"]`
- `state["processing_stats"]["articles_after_title_dedup"]`
- `state["processing_stats"]["duplicates_removed"]`

#### 3. **summarize** (summarize_trends)
**Location**: `quantum_intel.py:325-360`

**Purpose**: Generate executive summary of quantum trends

**Process**:
1. Aggregate article titles, URLs, and snippets
2. Submit to Gemini LLM with structured prompt
3. Generate 150-word summary focusing on:
   - Key trends in quantum networks and QKD
   - Significant breakthroughs
   - Industry implications

**Prompt Structure**:
```
Analyze the following quantum networking and QKD news articles
and write a compelling 150-word executive summary that:
1. Identifies key trends
2. Highlights significant breakthroughs
3. Explains implications
4. Uses engaging, professional language
```

**Outputs**:
- `state["executive_summary"]`: LLM-generated summary

**Error Handling**:
- LLM failures set default message
- Errors logged to `state["errors"]`

#### 4. **investments** (gather_investment_updates)
**Location**: `quantum_intel.py:362-377`

**Purpose**: Track news for specific quantum companies

**Process**:
1. For each company in `config.companies_to_track`:
   - Execute targeted search (30-day window)
   - Use LLM to summarize most significant development
2. Collect updates in dictionary

**Outputs**:
- `state["investment_updates"]`: {company: update_summary}
- `state["processing_stats"]["companies_tracked"]`

#### 5. **compose** (compose_newsletter)
**Location**: `quantum_intel.py:379-431`

**Purpose**: Assemble final newsletter markdown

**Sections**:
1. **Header**: Title and generation date
2. **Executive Summary**: LLM-generated trends analysis
3. **Investment & Company Updates**: Company-specific news
4. **Latest Articles**: Numbered list with titles, URLs, snippets
5. **Newsletter Statistics**: Processing metrics
6. **Footer**: Unsubscribe link and attribution

**Format**: GitHub-flavored Markdown

**Outputs**:
- `state["messages"]`: Newsletter content as HumanMessage

#### 6. **send_and_save** (send_email_and_save)
**Location**: `quantum_intel.py:433-452`

**Purpose**: Deliver newsletter and save to file

**Process**:
1. Extract newsletter content from state
2. Convert Markdown to HTML (for email)
3. Send via Gmail SMTP (if configured)
4. Save to `quantum_newsletter_output.md`
5. Save processing stats to JSON

**Outputs**:
- Email delivered (if credentials configured)
- File: `quantum_newsletter_output.md`
- File: `newsletter_stats.json`
- `state["processing_stats"]["email_sent"]`: Boolean

#### 7. **update_persistence** (update_persistence)
**Location**: `quantum_intel.py:454-469`

**Purpose**: Update sent articles list to prevent future duplicates

**Process**:
1. Extract URLs from `state["deduped_articles"]`
2. Append to `sent_articles.txt`

**Outputs**:
- File: `sent_articles.txt` (appended)

### Execution Flow

```
START
  ↓
search (30s avg)
  ↓ new_articles
deduplicate (1s)
  ↓ deduped_articles
summarize (5s LLM)
  ↓ executive_summary
investments (10s LLM)
  ↓ investment_updates
compose (instant)
  ↓ messages
send_and_save (2s)
  ↓
update_persistence (instant)
  ↓
END
```

**Total Runtime**: ~50 seconds typical

## Data Flow

### Input Sources

1. **Environment Variables** (`.env`):
   - API keys (Gemini, Tavily, SMTP)
   - Configuration (max articles, timeouts)
   - Company tracking list

2. **Persistent Storage**:
   - `sent_articles.txt`: Historical URLs (97 entries currently)

3. **External APIs**:
   - **Tavily Search**: News discovery
   - **Google Gemini**: Content generation
   - **Gmail SMTP**: Email delivery

### Output Artifacts

1. **Newsletter Content**:
   - `quantum_newsletter_output.md`: Markdown version
   - Email (HTML): Sent to configured recipient

2. **Logs**:
   - `quantum_newsletter.log`: Detailed execution log
   - Console output: Real-time status

3. **Metadata**:
   - `newsletter_stats.json`: Processing metrics with timestamp
   - `sent_articles.txt`: Updated URL list

### State Persistence

```
┌─────────────────────────────────────┐
│      Before Execution               │
│  sent_articles.txt (97 URLs)        │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│      During Execution               │
│  In-Memory State (AgentState)       │
│  - new_articles: 141 found          │
│  - deduped_articles: 10 unique      │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│      After Execution                │
│  sent_articles.txt (107 URLs)       │
│  + 10 new URLs appended             │
└─────────────────────────────────────┘
```

## External Dependencies

### API Integrations

#### 1. Tavily Search API
- **Purpose**: Web search for quantum news
- **Rate Limit**: ~1000 searches/month (free tier)
- **Timeout**: 5 seconds (configurable)
- **Cost**: Free tier sufficient for monthly newsletter

#### 2. Google Gemini API
- **Model**: gemini-2.5-flash
- **Purpose**: Content summarization and snippet cleaning
- **Token Usage**: ~2000 tokens/run
- **Temperature**: 0.3 (for consistency)
- **Cost**: ~$0.01/run (minimal)

#### 3. Gmail SMTP
- **Purpose**: Newsletter delivery
- **Authentication**: App Password (not account password)
- **Port**: 465 (SSL)
- **Rate Limit**: 500 emails/day (more than sufficient)

### Dependency Graph

```
quantum_intel.py
├── langchain-core
│   └── Messages, Tools
├── langchain-google-genai
│   └── ChatGoogleGenerativeAI
├── langgraph
│   └── StateGraph, END
├── langchain-community
│   └── TavilySearchResults
├── requests
│   └── URL validation
├── thefuzz
│   └── Title deduplication
├── python-dotenv
│   └── Configuration
└── smtplib (stdlib)
    └── Email delivery
```

## Error Handling Strategy

### Levels of Error Handling

1. **Function-level**: Try/except blocks with logging
2. **Node-level**: Errors appended to `state["errors"]`
3. **System-level**: Graceful degradation, continue execution

### Error Categories

| Error Type | Handling | Impact |
|------------|----------|--------|
| API timeout | Log, continue | Partial results |
| Invalid URL | Skip article | Reduced article count |
| LLM failure | Default message | Generic summary |
| SMTP error | Log, save to file | No email sent |
| File I/O error | Log, continue | Data not persisted |

### Example: Search Failure Handling

```python
try:
    results = tavily_tool.invoke({"query": query})
    all_results.extend(results)
except Exception as e:
    logger.error(f"Search failed for query '{query}': {e}")
    state.setdefault("errors", []).append(f"Search failed: {e}")
    # Continue with other queries
```

## Performance Considerations

### Bottlenecks

1. **URL Validation**: HEAD requests can be slow
   - Timeout: 5 seconds per URL
   - Parallel validation not implemented (serial checks)
   - Mitigation: Skip validation for known-good domains

2. **LLM Calls**: Network latency
   - Gemini API: ~1-3 seconds per call
   - Calls: 1 for summary + N for companies + M for snippets
   - Mitigation: Use fast model (gemini-2.5-flash)

3. **Search API**: Multiple queries
   - 9 queries × 5 seconds timeout = 45 seconds max
   - Mitigation: Queries run sequentially (could parallelize)

### Optimization Opportunities

1. **Parallel URL Validation**: Use `concurrent.futures`
2. **Batch LLM Requests**: Combine snippet cleaning
3. **Caching**: Cache search results for development
4. **Database**: Replace `sent_articles.txt` with SQLite for faster lookups

### Resource Usage

- **Memory**: <100MB (article lists in memory)
- **Disk**: Logs grow ~5KB/run
- **Network**: ~10MB download/run (search results)
- **CPU**: Minimal (I/O bound)

## Security Considerations

### Credential Management

- **Storage**: `.env` file (gitignored)
- **Access**: File permissions (user-only read)
- **Rotation**: Manual key rotation recommended quarterly

### API Key Exposure Risks

1. **Logs**: Keys not logged (verified)
2. **Error messages**: No keys in exceptions
3. **Outputs**: Newsletter doesn't contain keys

### Email Security

- **Authentication**: App Password (not account password)
- **Encryption**: TLS/SSL (port 465)
- **Validation**: Email addresses not validated (internal use)

## Monitoring & Observability

### Logging

**Log Levels**:
- **INFO**: Normal operations (article counts, node transitions)
- **DEBUG**: Detailed processing (snippet cleaning, similarity scores)
- **ERROR**: Failures (API errors, validation failures)

**Log Locations**:
- `quantum_newsletter.log`: Persistent file log
- Console: Real-time stdout

### Metrics

**Tracked in `newsletter_stats.json`**:
```json
{
  "last_run": "2026-04-27T14:35:22",
  "stats": {
    "articles_found": 141,
    "articles_after_url_dedup": 12,
    "articles_after_title_dedup": 10,
    "duplicates_removed": 131,
    "companies_tracked": 2,
    "email_sent": true
  }
}
```

### Alerting

**Manual Monitoring** (current):
- Review `newsletter_stats.json` after each run
- Check `email_sent` status
- Review error count

**Future**: Slack/email alerts for failures

## Future Enhancements

### Planned Improvements

1. **Database Migration**:
   - Replace `sent_articles.txt` with SQLite
   - Enable querying by date, source, topic
   - Improve deduplication performance

2. **Scheduling**:
   - Cron job for automated execution
   - Cloud scheduler (GCP Cloud Scheduler, AWS EventBridge)

3. **Analytics Dashboard**:
   - Visualize trends over time
   - Track article sources
   - Monitor deduplication efficiency

4. **Multi-Recipient Support**:
   - Distribution lists
   - Personalized content per recipient

5. **A/B Testing**:
   - Test different summary styles
   - Optimize email subject lines

6. **Content Expansion**:
   - Include paper abstracts
   - Link to company profiles
   - Add relevant images

7. **API Endpoint**:
   - REST API for on-demand generation
   - Webhook for external triggers

### Technical Debt

1. **Serial URL validation** → Parallelize with `ThreadPoolExecutor`
2. **Hardcoded prompts** → Move to config/template files
3. **Magic numbers** → Extract to constants (e.g., similarity threshold)
4. **No retry logic** → Add exponential backoff for API calls
5. **Limited error granularity** → Separate error types for better debugging

## Testing Strategy

### Unit Tests

**Coverage Target**: >80% for testable code

**Tested Functions**:
- `validate_url()`: URL validation logic
- `is_article_url()`: Article filtering
- `get_previous_articles()`: File reading
- `deduplicate_articles()`: Deduplication logic
- `convert_markdown_to_html()`: Formatting
- `clean_snippet()`: LLM-based cleaning (mocked)

**Not Tested** (integration complexity):
- LangGraph orchestration
- Live API calls
- End-to-end workflow

### Mocking Strategy

- **LLM calls**: Mock `llm.invoke()` with fixed responses
- **API calls**: Mock `tavily_tool.invoke()` with sample data
- **HTTP requests**: Mock `requests.head()` with status codes
- **File I/O**: Use `tempfile` for isolated tests

### Test Execution

```bash
# All tests
pytest

# Specific module
pytest tests/test_deduplication.py

# With coverage
pytest --cov=quantum_intel --cov-report=html

# Verbose
pytest -v
```

## Deployment

### Current Deployment: Manual Execution

```bash
cd /Users/jessica.pan/Desktop/quantum_intel_project
source venv/bin/activate
python quantum_intel.py
```

### Future: Automated Deployment

**Option 1: Cron Job** (macOS/Linux)
```bash
# Edit crontab
crontab -e

# Add monthly execution (1st of month at 9am)
0 9 1 * * cd /path/to/project && ./scripts/run_newsletter.sh
```

**Option 2: Cloud Function** (GCP)
- Package as Cloud Function
- Trigger via Cloud Scheduler
- Store secrets in Secret Manager

## Diagrams

### Component Interaction

```
┌─────────────┐
│    User     │
└──────┬──────┘
       │ python quantum_intel.py
       ▼
┌─────────────────────────────────────┐
│     Quantum Intel Agent             │
│  ┌──────────────────────────────┐  │
│  │     LangGraph Runtime        │  │
│  │  ┌────────┐   ┌──────────┐  │  │
│  │  │ search │──▶│ deduplicate │  │  │
│  │  └────────┘   └──────────┘  │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
       │        │         │
       ▼        ▼         ▼
   Tavily   Gemini     Gmail
    API      API       SMTP
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-05-02  
**Maintainer**: SandboxAQ Quantum Intelligence Team
