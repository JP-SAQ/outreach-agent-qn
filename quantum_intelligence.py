# Enhanced LangGraph Agent for Quantum Newsletter
from typing import TypedDict, List, Optional, Dict, Any
import datetime
import smtplib
import os
import requests
import json
import logging
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from urllib.parse import urlparse
from thefuzz import fuzz # --- NEW --- For smart deduplication

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults

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

# --- Enhanced State Definition ---
class AgentState(TypedDict):
    messages: List[BaseMessage]
    new_articles: List[Dict[str, Any]]
    deduped_articles: List[Dict[str, Any]]
    investment_updates: Dict[str, str]
    executive_summary: str
    errors: List[str]
    processing_stats: Dict[str, int]

# --- Configuration Class ---
class NewsletterConfig:
    def __init__(self):
        self.max_articles = int(os.getenv("MAX_ARTICLES", "10"))
        self.search_timeout = int(os.getenv("SEARCH_TIMEOUT", "5"))
        self.link_validation_timeout = int(os.getenv("LINK_VALIDATION_TIMEOUT", "5"))
        self.previous_articles_file = os.getenv("PREVIOUS_ARTICLES_FILE", "sent_articles.txt")
        self.output_file = os.getenv("OUTPUT_FILE", "quantum_newsletter_output.md")
        self.companies_to_track = os.getenv("COMPANIES_TO_TRACK", "EvolutionQ,Qunnect").split(",")
        self.bad_url_keywords = ['/tag/', '/tags/', '/category/', '/topics/', '/solutions/', '/search/', '/page/']
        self.title_similarity_threshold = 85 # --- NEW --- Similarity score for deduplication

config = NewsletterConfig()

# --- Model and Tool Initialization ---
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

# ------------------------------
# Enhanced Utility Functions
# ------------------------------
def validate_url(url: str, timeout: int = 5) -> bool:
    """Validate if a URL is accessible and returns a successful status code."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        response = requests.head(url, allow_redirects=True, timeout=timeout)
        return 200 <= response.status_code < 300
    except requests.exceptions.RequestException:
        return False

def is_article_url(url: str) -> bool:
    """Check if URL appears to be an article rather than a category/tag page."""
    url_lower = url.lower()
    return not any(keyword in url_lower for keyword in config.bad_url_keywords)

# --- NEW --- Snippet Cleaning Function
def clean_snippet(raw_snippet: str) -> str:
    """Uses an LLM to clean raw text snippets."""
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
        return raw_snippet # Return original snippet on failure

def send_newsletter_email(subject: str, html_content: str) -> bool:
    """Enhanced email sending with better error handling and HTML formatting."""
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
    """Convert basic markdown to HTML for better email formatting."""
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
    """Load previously sent article URLs."""
    try:
        with open(config.previous_articles_file, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        logger.info("No previous articles file found. Starting fresh.")
        return []

def save_processing_stats(stats: Dict[str, int]):
    """Save processing statistics to a JSON file."""
    stats_file = "newsletter_stats.json"
    try:
        with open(stats_file, "w") as f:
            json.dump({
                "last_run": datetime.datetime.now().isoformat(),
                "stats": stats
            }, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save stats: {e}")

# ------------------------------
# Enhanced Tools
# ------------------------------
@tool
def get_dynamic_company_update(company: str) -> str:
    """Get recent news about a specific quantum computing company."""
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

# ------------------------------
# Enhanced Graph Node Functions
# ------------------------------
# --- MODIFIED --- to include snippet cleaning
def retrieve_articles(state: AgentState) -> AgentState:
    """Enhanced article retrieval with better filtering, validation, and snippet cleaning."""
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
            # Clean the snippet before adding
            raw_snippet = result.get('content', '')
            cleaned_snippet = clean_snippet(raw_snippet)
            
            live_articles.append({
                'title': result.get('title', 'Untitled'),
                'url': url,
                'snippet': cleaned_snippet[:250] + '...' if cleaned_snippet else ''
            })
        else:
            logger.debug(f"Discarding invalid/dead link: {url}")
    
    state["new_articles"] = live_articles[:config.max_articles * 2] # Fetch more to allow for better deduplication
    state.setdefault("processing_stats", {})["articles_found"] = len(live_articles)
    logger.info(f"Retrieved {len(state['new_articles'])} validated and cleaned articles")
    return state

# --- MODIFIED --- to include title similarity check
def deduplicate_articles(state: AgentState) -> AgentState:
    """Remove articles that were already sent or have highly similar titles."""
    logger.info("Deduplicating articles with URL and title similarity checks...")
    
    # First pass: Deduplicate based on previously sent URLs
    previous_urls = set(get_previous_articles())
    url_deduped_articles = [
        article for article in state["new_articles"] 
        if article["url"] not in previous_urls
    ]
    
    # Second pass: Deduplicate based on title similarity
    final_articles = []
    seen_titles = []
    for article in url_deduped_articles:
        is_duplicate = False
        for seen_title in seen_titles:
            similarity = fuzz.ratio(article['title'].lower(), seen_title.lower())
            if similarity > config.title_similarity_threshold:
                is_duplicate = True
                logger.info(f"Found title duplicate (similarity: {similarity}%). Discarding '{article['title']}' as it is too similar to '{seen_title}'.")
                break
        
        if not is_duplicate:
            final_articles.append(article)
            seen_titles.append(article['title'])

    # Limit to max articles after all deduplication
    state["deduped_articles"] = final_articles[:config.max_articles]
    
    stats = state.setdefault("processing_stats", {})
    stats["articles_after_url_dedup"] = len(url_deduped_articles)
    stats["articles_after_title_dedup"] = len(state["deduped_articles"])
    stats["duplicates_removed"] = len(state["new_articles"]) - len(state["deduped_articles"])
    
    logger.info(f"After all deduplication: {len(state['deduped_articles'])} new articles remain.")
    return state

def summarize_trends(state: AgentState) -> AgentState:
    """Generate executive summary of quantum news trends."""
    logger.info("Generating executive summary...")
    if not state["deduped_articles"]:
        state["executive_summary"] = "No significant new developments in quantum networking this period."
        return state
    
    articles_info = []
    for article in state["deduped_articles"]:
        info = f"Title: {article['title']}\nURL: {article['url']}"
        if article.get('snippet'):
            info += f"\nSnippet: {article['snippet']}"
        articles_info.append(info)
    
    content = "\n\n".join(articles_info)
    prompt = f"""
    Analyze the following quantum networking and quantum key distribution (QKD) news articles 
    and write a compelling 150-word executive summary that:
    1. Identifies key trends in both quantum networks and QKD from the past two months
    2. Highlights the most significant breakthroughs in quantum networking and QKD
    3. Explains implications for the quantum industry
    4. Keep it concise and under 150 words
    5. Use engaging, professional language suitable for investors and technologists
    
    Articles:
    {content}
    """
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        state["executive_summary"] = response.content
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        state["executive_summary"] = "Unable to generate executive summary due to processing error."
        state.setdefault("errors", []).append(f"Summary generation failed: {e}")
    
    return state

def gather_investment_updates(state: AgentState) -> AgentState:
    """Gather updates on tracked quantum companies."""
    logger.info("Gathering investment updates...")
    updates = {}
    for company in config.companies_to_track:
        company = company.strip()
        try:
            update = get_dynamic_company_update.invoke(company)
            updates[company] = update
        except Exception as e:
            logger.error(f"Failed to get update for {company}: {e}")
            updates[company] = f"Update unavailable for {company}"
    
    state["investment_updates"] = updates
    state.setdefault("processing_stats", {})["companies_tracked"] = len(updates)
    return state

def compose_newsletter(state: AgentState) -> AgentState:
    """Compose the final newsletter content."""
    logger.info("Composing newsletter...")
    
    today = datetime.date.today()
    
    # Articles section (underscores for italics removed from snippet)
    if state["deduped_articles"]:
        articles_md = "\n".join([
            f"{i+1}. [{article['title']}]({article['url']})"
            + (f"\n    {article['snippet']}" if article.get('snippet') else "")
            for i, article in enumerate(state["deduped_articles"])
        ])
    else:
        articles_md = "_No new articles this period._"
    
    # Investment updates section
    investment_md = "\n\n".join([
        f"{company}: {update}" 
        for company, update in state["investment_updates"].items()
    ])
    
    # Processing stats
    stats = state.get("processing_stats", {})
    stats_md = f"""
Processing Statistics:
- Articles found: {stats.get('articles_found', 0)}
- New articles (after deduplication): {stats.get('articles_after_title_dedup', 0)}
- Companies tracked: {stats.get('companies_tracked', 0)}
"""
    
    newsletter_content = f"""# Quantum Intelligence Newsletter
*Generated on {today.strftime('%B %d, %Y')}*

## 🧠 Executive Summary
{state['executive_summary']}

## 📈 Investment & Company Updates
{investment_md}

## 📚 Latest Articles & Developments
{articles_md}

## 📊 Newsletter Statistics
{stats_md}

---
*This newsletter was automatically generated by the Quantum Intelligence Agent*
"""
    
    state["messages"] = [HumanMessage(content=newsletter_content)]
    return state

def send_email_and_save(state: AgentState) -> AgentState:
    """Send newsletter via email and save to file."""
    logger.info("Sending email and saving newsletter...")
    today = datetime.date.today()
    subject = f"🚀 Quantum Intelligence Newsletter – {today.strftime('%B %Y')}"
    content = state["messages"][-1].content
    email_sent = send_newsletter_email(subject, content)
    
    try:
        output_path = Path(config.output_file)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Newsletter saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save newsletter: {e}")
        state.setdefault("errors", []).append(f"File save failed: {e}")
    
    save_processing_stats(state.get("processing_stats", {}))
    state.setdefault("processing_stats", {})["email_sent"] = email_sent
    return state

def update_persistence(state: AgentState) -> AgentState:
    """Update the persistence file with new article URLs."""
    logger.info("Updating persistence...")
    new_urls = [article['url'] for article in state["deduped_articles"]]
    
    if new_urls:
        try:
            with open(config.previous_articles_file, "a") as f:
                for url in new_urls:
                    f.write(f"{url}\n")
            logger.info(f"Saved {len(new_urls)} URLs to persistence file")
        except Exception as e:
            logger.error(f"Failed to update persistence: {e}")
            state.setdefault("errors", []).append(f"Persistence update failed: {e}")
    
    return state

# ------------------------------
# Graph Definition
# ------------------------------
def create_newsletter_graph():
    """Create and return the compiled newsletter generation graph."""
    builder = StateGraph(AgentState)
    builder.add_node("search", retrieve_articles)
    builder.add_node("deduplicate", deduplicate_articles)
    builder.add_node("summarize", summarize_trends)
    builder.add_node("investments", gather_investment_updates)
    builder.add_node("compose", compose_newsletter)
    builder.add_node("send_and_save", send_email_and_save)
    builder.add_node("update_persistence", update_persistence)
    
    builder.set_entry_point("search")
    builder.add_edge("search", "deduplicate")
    builder.add_edge("deduplicate", "summarize")
    builder.add_edge("summarize", "investments")
    builder.add_edge("investments", "compose")
    builder.add_edge("compose", "send_and_save")
    builder.add_edge("send_and_save", "update_persistence")
    builder.add_edge("update_persistence", END)
    
    return builder.compile()

# ------------------------------
# Main Execution
# ------------------------------
def main():
    """Main function to run the newsletter generation."""
    logger.info("Starting Quantum Newsletter Generation...")
    initial_state = {
        "messages": [],
        "new_articles": [],
        "deduped_articles": [],
        "investment_updates": {},
        "executive_summary": "",
        "errors": [],
        "processing_stats": {}
    }
    
    try:
        graph = create_newsletter_graph()
        result = graph.invoke(initial_state)
        
        logger.info("Newsletter generation completed successfully!")
        
        # print(result["messages"][-1].content)
        
        if result.get("errors"):
            print("\n" + "="*60)
            print("ERRORS ENCOUNTERED")
            print("="*60)
            for error in result["errors"]:
                print(f"- {error}")
        
        stats = result.get("processing_stats", {})
        print("\n" + "="*60)
        print("FINAL NEWSLETTER & STATISTICS")
        print("="*60)
        print(result["messages"][-1].content)
        print("\n" + "="*60)
        for key, value in stats.items():
            print(f"- {key.replace('_', ' ').title()}: {value}")
            
    except Exception as e:
        logger.error(f"Newsletter generation failed: {e}")
        raise

if __name__ == "__main__":
    main()
