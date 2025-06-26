# quantum_newsletter_agent.py

"""
Quantum Newsletter Agent

Enhanced LangGraph agent that generates a quantum technology newsletter. It:
- Searches for relevant articles using Tavily
- Cleans and deduplicates article snippets
- Tracks investment updates for target companies
- Generates an executive summary with LLM support
- Composes and emails a markdown+HTML newsletter
- Logs processing stats and updates persistence files
"""

import datetime
import json
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import urlparse
from typing import TypedDict, List, Optional, Dict, Any

import requests
from dotenv import load_dotenv
from thefuzz import fuzz  # For smart deduplication

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults



# =============================================================================
# Configuration and Logging
# =============================================================================

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quantum_newsletter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# State and Config Definitions
# =============================================================================

class AgentState(TypedDict):
    """Represents the structured state used and modified across the LangGraph agent nodes
    during newsletter generation.

    Attributes
    ----------
    messages : List[BaseMessage]
        List of LangChain messages used in LLM interactions (e.g., prompts and responses).
    new_articles : List[Dict[str, Any]]
        Raw, validated articles retrieved from the web, before deduplication.
    deduped_articles : List[Dict[str, Any]]
        Final set of unique articles after URL and fuzzy title deduplication.
    investment_updates : Dict[str, str]
        Company-specific update summaries (e.g., funding, partnerships).
    executive_summary : str
        LLM-generated summary of trends in the quantum news space.
    errors : List[str]
        List of error messages encountered during processing for logging/debugging.
    processing_stats : Dict[str, int]
        Dictionary of counters and metrics collected during execution
        (e.g., number of articles found, duplicates removed).
    """
    messages: List[BaseMessage]
    new_articles: List[Dict[str, Any]]
    deduped_articles: List[Dict[str, Any]]
    investment_updates: Dict[str, str]
    executive_summary: str
    errors: List[str]
    processing_stats: Dict[str, int]


class NewsletterConfig:
    """Configuration parameters for newsletter generation loaded from environment variables.

    Attributes
    ----------
    max_articles : int
        Maximum number of final articles to include in the newsletter.
    search_timeout : int
        Timeout in seconds for article search queries.
    link_validation_timeout : int
        Timeout in seconds for validating URLs via HEAD requests.
    previous_articles_file : str
        File path storing URLs of previously sent articles to avoid duplicates.
    output_file : str
        File path to save the generated newsletter markdown.
    companies_to_track : List[str]
        Names of companies to track for investment updates.
    bad_url_keywords : List[str]
        Substrings indicating URLs to exclude (e.g., tag or category pages).
    title_similarity_threshold : int
        Threshold (0-100) for fuzzy title similarity deduplication.
    """
    def __init__(self):
        """
        Initialize NewsletterConfig from environment variables.
        """
        self.max_articles = int(os.getenv("MAX_ARTICLES", "10"))
        self.search_timeout = int(os.getenv("SEARCH_TIMEOUT", "5"))
        self.link_validation_timeout = int(os.getenv("LINK_VALIDATION_TIMEOUT", "5"))
        self.previous_articles_file = os.getenv("PREVIOUS_ARTICLES_FILE", "sent_articles.txt")
        self.output_file = os.getenv("OUTPUT_FILE", "quantum_newsletter_output.md")
        self.companies_to_track = os.getenv("COMPANIES_TO_TRACK", "EvolutionQ,Qunnect").split(",")
        self.bad_url_keywords = ['/tag/', '/tags/', '/category/', '/topics/', '/solutions/', '/search/', '/page/']
        self.title_similarity_threshold = 85


config = NewsletterConfig()


# =============================================================================
# Model and Tool Initialization
# =============================================================================

try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-latest",
        temperature=0.3,
        google_api_key=os.getenv("Gemini_API_Key")
    )
    tavily_tool = TavilySearchResults(max_results=30)
    logger.info("Successfully initialized LLM and search tools")
except Exception as e:
    logger.error(f"Failed to initialize tools: {e}")
    raise


# =============================================================================
# Utility Functions
# =============================================================================

def validate_url(url: str, timeout: int = 5) -> bool:
    """Check if a URL is reachable by sending a HEAD request.

    Parameters
    ----------
    url : str
        URL to validate.
    timeout : int, optional
        Timeout in seconds for the HEAD request (default is 5).

    Returns
    -------
    bool
        True if the URL responds with a 2xx status code, False otherwise.
    """
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        response = requests.head(url, allow_redirects=True, timeout=timeout)
        return 200 <= response.status_code < 300
    except requests.exceptions.RequestException:
        return False


def is_article_url(url: str) -> bool:
    """Determine if a URL likely points to an article by excluding known bad keywords.

    Parameters
    ----------
    url : str
        URL string to check.

    Returns
    -------
    bool
        True if URL does not contain any bad_url_keywords, False otherwise.
    """
    url_lower = url.lower()
    return not any(keyword in url_lower for keyword in config.bad_url_keywords)


def clean_snippet(raw_snippet: str) -> str:
    """Clean a raw text snippet by removing boilerplate using an LLM.

    Parameters
    ----------
    raw_snippet : str
        Raw snippet text to clean.

    Returns
    -------
    str
        Cleaned snippet text. Returns empty string if input is empty.
    """
    if not raw_snippet:
        return ""
    
    logger.debug(f"Cleaning snippet: {raw_snippet[:100]}...")
    prompt = f"""
    Please clean the following text snippet. Remove any website navigation elements, menu items, ad-related text, or other non-article boilerplate text.
    Return only the core, clean sentence(s) of the snippet. If the snippet is already clean, return it unchanged.

    RAW SNIPPET:
    "{raw_snippet}"

    CLEANED SNIPPET:
    """
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        cleaned = response.content.strip().strip('"')
        logger.debug(f"Cleaned snippet: {cleaned[:100]}...")
        return cleaned
    except Exception as e:
        logger.error(f"Failed to clean snippet: {e}")
        return raw_snippet


def send_newsletter_email(subject: str, html_content: str) -> bool:
    """Send the newsletter via email with HTML formatting.

    Parameters
    ----------
    subject : str
        Email subject line.
    html_content : str
        The markdown content to convert and send as email body.

    Returns
    -------
    bool
        True if email sent successfully, False otherwise.
    """
    sender = os.getenv("EMAIL_USER")
    recipient = os.getenv("EMAIL_RECIPIENT")
    password = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))

    if not all([sender, recipient, password]):
        logger.warning("Email credentials not fully configured. Skipping email.")
        return False

    html_formatted = convert_markdown_to_html(html_content)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html_content, "plain"))
    msg.attach(MIMEText(html_formatted, "html"))

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        logger.info(f"Email successfully sent to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def convert_markdown_to_html(md_content: str) -> str:
    """Convert basic markdown to HTML for email formatting.

    Parameters
    ----------
    md_content : str
        Markdown content string.

    Returns
    -------
    str
        HTML-formatted string with basic tag replacements.
    """
    html = md_content
    html = html.replace("## ", "<h2>").replace("\n", "</h2>\n", 1) if "## " in html else html
    import re
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
    html = html.replace("\n", "<br>\n")
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; font-size: 12px; line-height: 1.6; color: #333;">
    {html}
    </body>
    </html>
    """


def get_previous_articles() -> List[str]:
    """Load URLs of previously sent articles from persistence file.

    Returns
    -------
    List[str]
        List of URLs.
    """
    try:
        with open(config.previous_articles_file, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        logger.info("No previous articles file found. Starting fresh.")
        return []


def save_processing_stats(stats: Dict[str, int]) -> None:
    """Persist processing statistics to a JSON file.

    Parameters
    ----------
    stats : Dict[str, int]
        Dictionary of processing counters and metrics.

    Returns
    -------
    None
    """
    stats_file = "newsletter_stats.json"
    try:
        with open(stats_file, "w") as f:
            json.dump({
                "last_run": datetime.datetime.now().isoformat(),
                "stats": stats
            }, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save stats: {e}")


@tool
def get_dynamic_company_update(company: str) -> str:
    """Fetch recent business developments for a quantum company using Tavily.

    Parameters
    ----------
    company : str
        Name of the company to query.

    Returns
    -------
    str
        Concise summary of recent developments or an error message.
    """
    logger.info(f"Fetching update for: {company}")
    current_date = datetime.date.today()
    current_year = current_date.year
    two_months_ago = current_date - datetime.timedelta(days=60)
    date_filter = f"after:{two_months_ago.strftime('%Y-%m-%d')}"
    query = f'"{company}" quantum computing funding investment partnership technology {current_year} {date_filter}'
    
    try:
        search_results = tavily_tool.invoke({"query": query})
        if not search_results:
            return f"No recent news found for {company} in the past two months."
        prompt = f"""
        Based on the search results below, write a concise, informative summary (1-2 sentences) 
        of the most significant recent development for {company} from the past two months. 
        Focus on business developments, funding, partnerships, or technology breakthroughs.
        If no recent developments are found, state that clearly.
        
        Search Results: {search_results}
        """
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        logger.error(f"Failed to get update for {company}: {e}")
        return f"Unable to retrieve recent updates for {company}."


def retrieve_articles(state: AgentState) -> AgentState:
    """Retrieve, filter, validate, and clean article snippets.

    Parameters
    ----------
    state : AgentState
        Current agent state with prior data.

    Returns
    -------
    AgentState
        Updated state including new_articles and processing_stats.
    """
    logger.info("Starting article retrieval and validation...")
    current_date = datetime.date.today()
    current_year = current_date.year
    two_months_ago = current_date - datetime.timedelta(days=60)
    date_filter = f"after:{two_months_ago.strftime('%Y-%m-%d')}"
    queries = [
        f"quantum key distribution QKD network security breakthrough {current_year} {date_filter}",
        f"quantum networking infrastructure communication technology news {current_year} {date_filter}",
        f"quantum internet quantum network protocol development {current_year} {date_filter}"
    ]
    
    all_results = []
    for query in queries:
        try:
            results = tavily_tool.invoke({"query": query})
            all_results.extend(results)
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            state.setdefault("errors", []).append(f"Search failed: {e}")
    
    seen_urls = set()
    unique_results = []
    for result in all_results:
        url = result.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)
    
    article_candidates = [
        result for result in unique_results  
        if is_article_url(result.get('url', ''))
    ]
    logger.info(f"Found {len(article_candidates)} article candidates after URL filtering")
    
    live_articles = []
    for result in article_candidates:
        url = result.get('url')
        if url and validate_url(url, config.link_validation_timeout):
            raw_snippet = result.get('content', '')
            cleaned_snippet = clean_snippet(raw_snippet)
            live_articles.append({
                'title': result.get('title', 'Untitled'),
                'url': url,
                'snippet': cleaned_snippet[:250] + '...' if cleaned_snippet else ''
            })
        else:
            logger.debug(f"Discarding invalid/dead link: {url}")
    
    state["new_articles"] = live_articles[:config.max_articles * 2]
    state.setdefault("processing_stats", {})["articles_found"] = len(live_articles)
    logger.info(f"Retrieved {len(state['new_articles'])} validated and cleaned articles")
    return state


def deduplicate_articles(state: AgentState) -> AgentState:
    """Remove previously sent and fuzzy-title duplicate articles.

    Parameters
    ----------
    state : AgentState
        State containing new_articles and processing stats.

    Returns
    -------
    AgentState
        Updated state with deduped_articles and updated stats.
    """
    logger.info("Deduplicating articles with URL and title similarity checks...")
    previous_urls = set(get_previous_articles())
    url_deduped_articles = [
        article for article in state["new_articles"]  
        if article["url"] not in previous_urls
    ]
    
    final_articles = []
    seen_titles = []
    for article in url_deduped_articles:
        is_duplicate = False
        for seen_title in seen_titles:
            similarity = fuzz.ratio(article['title'].lower(), seen_title.lower())
            if similarity > config.title_similarity_threshold:
                is_duplicate = True
                logger.info(f"Found title duplicate (similarity...")
