import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any
from urllib.parse import urlparse
import datetime

async def scrape_url(url: str, timeout: float = 15.0) -> Dict[str, Any]:
    """
    Fetches content from a URL, strips boilerplate (nav, scripts, ads, footers),
    and extracts clean article/text content for RAG semantic ingestion.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL format: '{url}'. Please include http:// or https://")
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text
        
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove unwanted tags
    for unwanted in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "svg", "iframe"]):
        unwanted.decompose()
        
    # Extract page title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("h1"):
        title = soup.find("h1").get_text().strip()
    else:
        title = parsed.netloc + parsed.path
        
    # Look for main article or body container
    main_container = soup.find("article") or soup.find("main") or soup.find(id="content") or soup.body or soup
    
    # Extract text with structured breaks
    lines = []
    for element in main_container.find_all(["h1", "h2", "h3", "h4", "p", "li", "pre", "code"]):
        text = element.get_text(separator=" ", strip=True)
        if not text:
            continue
        tag = element.name.lower()
        if tag == "h1":
            lines.append(f"\n# {text}\n")
        elif tag == "h2":
            lines.append(f"\n## {text}\n")
        elif tag == "h3":
            lines.append(f"\n### {text}\n")
        elif tag == "li":
            lines.append(f"- {text}")
        elif tag in ["pre", "code"]:
            lines.append(f"\n```\n{text}\n```\n")
        else:
            lines.append(text)
            
    clean_text = "\n\n".join(lines)
    if not clean_text.strip():
        # Fallback to whole text
        clean_text = soup.get_text(separator="\n", strip=True)
        
    return {
        "title": title,
        "url": url,
        "source": parsed.netloc,
        "file_type": "web_url",
        "text": clean_text,
        "timestamp": datetime.datetime.now().isoformat(),
        "char_count": len(clean_text)
    }
