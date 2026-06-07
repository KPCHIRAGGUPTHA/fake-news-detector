import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Known reliable domains
RELIABLE_DOMAINS = [
    "reuters.com", "bbc.com", "bbc.co.uk", "apnews.com",
    "theguardian.com", "nytimes.com", "washingtonpost.com",
    "bloomberg.com", "economist.com", "ft.com", "wsj.com",
    "npr.org", "pbs.org", "thehindu.com", "ndtv.com",
    "timesofindia.com", "hindustantimes.com"
]

# Known unreliable domains
UNRELIABLE_DOMAINS = [
    "infowars.com", "naturalnews.com", "breitbart.com",
    "theonion.com", "babylonbee.com", "worldnewsdailyreport.com",
    "empirenews.net", "nationalreport.net", "newslo.com"
]


def get_domain(url: str) -> str:
    """Extract base domain from URL."""
    url = url.lower().replace("https://", "").replace("http://", "").replace("www.", "")
    return url.split("/")[0]


def check_domain_trust(url: str) -> dict:
    domain = get_domain(url)
    if any(d in domain for d in RELIABLE_DOMAINS):
        return {"trust": "high",   "label": "Trusted Source",     "color": "good"}
    if any(d in domain for d in UNRELIABLE_DOMAINS):
        return {"trust": "low",    "label": "Unreliable Source",   "color": "warn"}
    return     {"trust": "unknown","label": "Unknown Source",      "color": "neutral"}


def scrape_article(url: str) -> dict:
    """
    Scrape article text from a URL.
    Returns { text, title, domain, trust }
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. The website took too long to respond."}
    except requests.exceptions.ConnectionError:
        return {"error": "Could not connect to the URL. Check the link and try again."}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error: {e.response.status_code}"}
    except Exception as e:
        return {"error": f"Failed to fetch URL: {str(e)}"}

    soup  = BeautifulSoup(resp.text, "html.parser")

    # Remove script, style, nav, footer tags
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    # Try to get title
    title = ""
    if soup.find("h1"):
        title = soup.find("h1").get_text(strip=True)
    elif soup.title:
        title = soup.title.get_text(strip=True)

    # Try common article containers first
    article_text = ""
    for selector in ["article", "main", '[class*="article"]', '[class*="content"]', '[class*="story"]']:
        container = soup.select_one(selector)
        if container:
            paragraphs = container.find_all("p")
            article_text = " ".join(p.get_text(strip=True) for p in paragraphs)
            if len(article_text) > 200:
                break

    # Fallback: all paragraphs on the page
    if len(article_text) < 200:
        paragraphs   = soup.find_all("p")
        article_text = " ".join(p.get_text(strip=True) for p in paragraphs)

    # Clean up whitespace
    article_text = re.sub(r'\s+', ' ', article_text).strip()

    if len(article_text) < 100:
        return {"error": "Could not extract enough text from this page. Try copying the article text manually."}

    domain = get_domain(url)
    trust  = check_domain_trust(url)

    return {
        "text":   article_text[:3000],  # limit to 3000 chars
        "title":  title,
        "domain": domain,
        "trust":  trust,
        "chars":  len(article_text)
    }
