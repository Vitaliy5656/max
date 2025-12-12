"""
Web Search Module using DuckDuckGo.

Features:
- Free web search without API key
- Page content extraction
- Result caching
"""
import asyncio
from typing import Optional
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

# P2 fix: Handle both old and new package names for DuckDuckGo search
try:
    from duckduckgo_search import DDGS
except ImportError:
    try:
        from ddgs import DDGS
    except ImportError:
        DDGS = None
        print("Warning: DuckDuckGo search not available. Install: pip install duckduckgo-search")


@dataclass
class SearchResult:
    """Single search result."""
    title: str
    url: str
    snippet: str
    

class WebSearcher:
    """
    Web search using DuckDuckGo.
    No API key required.
    """

    def __init__(self):
        # P2 fix: Handle missing DDGS gracefully
        self._ddgs = DDGS() if DDGS else None
        self._cache: dict[str, list[SearchResult]] = {}
        self._page_cache: dict[str, str] = {}
        
    async def search(
        self, 
        query: str, 
        max_results: int = 5,
        region: str = "ru-ru"
    ) -> list[SearchResult]:
        """
        Search the web.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            region: Region for results (ru-ru, en-us, etc.)
            
        Returns:
            List of search results
        """
        cache_key = f"{query}:{max_results}:{region}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # P2 fix: Check if DDGS is available
        if not self._ddgs:
            return []

        try:
            # Run in thread pool since ddgs is synchronous
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: list(self._ddgs.text(
                    query,
                    max_results=max_results,
                    region=region
                ))
            )
            
            search_results = [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", "")
                )
                for r in results
            ]
            
            self._cache[cache_key] = search_results
            return search_results
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    async def read_page(
        self, 
        url: str,
        max_length: int = 5000
    ) -> str:
        """
        Extract text content from a webpage.
        
        Args:
            url: URL to read
            max_length: Maximum characters to return
            
        Returns:
            Extracted text content
        """
        if url in self._page_cache:
            return self._page_cache[url][:max_length]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    follow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                response.raise_for_status()
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator="\n", strip=True)
            
            # Clean up whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = "\n".join(lines)
            
            self._page_cache[url] = text
            return text[:max_length]
            
        except Exception as e:
            return f"Error reading page: {str(e)}"
    
    async def search_and_summarize(
        self,
        query: str,
        max_results: int = 3
    ) -> str:
        """
        Search and return formatted summary.
        """
        results = await self.search(query, max_results)
        
        if not results:
            return "Ничего не найдено."
        
        output = f"🔍 Результаты поиска: {query}\n\n"
        for i, r in enumerate(results, 1):
            domain = urlparse(r.url).netloc
            output += f"{i}. **{r.title}**\n"
            output += f"   {domain}\n"
            output += f"   {r.snippet}\n\n"
        
        return output
    
    def clear_cache(self):
        """Clear search and page caches."""
        self._cache.clear()
        self._page_cache.clear()


# Global web searcher
web_searcher = WebSearcher()
