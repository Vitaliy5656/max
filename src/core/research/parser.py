"""
Dual Parser Module

Clean text extraction using trafilatura as primary parser with BeautifulSoup fallback.

Features:
- Async-safe trafilatura with timeout
- BeautifulSoup fallback for failed extractions
- Stats tracking for parser comparison
- Minimum content length filtering
"""

import asyncio
import time
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from bs4 import BeautifulSoup

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False


# Configuration
TRAFILATURA_TIMEOUT = 10  # seconds
MIN_CONTENT_LENGTH = 200  # chars - skip garbage pages


@dataclass
class ParseResult:
    """Result of parsing a web page."""
    content: str
    parser_used: str  # "trafilatura" | "bs4" | "skipped"
    char_count: int
    parse_time_ms: float
    url: str = ""
    error: Optional[str] = None


@dataclass
class ParserStats:
    """Statistics for parser comparison."""
    trafilatura_success: int = 0
    trafilatura_fail: int = 0
    trafilatura_total_chars: int = 0
    trafilatura_total_time_ms: float = 0
    bs4_success: int = 0
    bs4_fail: int = 0
    bs4_total_chars: int = 0
    bs4_total_time_ms: float = 0
    skipped: int = 0


class DualParser:
    """
    Dual parser with trafilatura primary and BS4 fallback.
    
    Gotcha: trafilatura.extract() is SYNC and can take 1-3 sec.
    Must run in executor to not block event loop.
    """
    
    def __init__(self):
        self._stats = ParserStats()
        self._stats_file = Path("data/research/parser_stats.json")
        self._load_stats()
    
    async def extract(self, url: str, html: str) -> ParseResult:
        """
        Extract clean text from HTML.
        Try trafilatura first, fallback to BS4.
        
        Returns ParseResult with parser_used="skipped" if content too short.
        """
        start_time = time.time()
        
        # Try trafilatura first (if available)
        if TRAFILATURA_AVAILABLE:
            result = await self._try_trafilatura(url, html)
            if result and len(result) >= MIN_CONTENT_LENGTH:
                elapsed = (time.time() - start_time) * 1000
                self._stats.trafilatura_success += 1
                self._stats.trafilatura_total_chars += len(result)
                self._stats.trafilatura_total_time_ms += elapsed
                self._save_stats()
                
                return ParseResult(
                    content=result,
                    parser_used="trafilatura",
                    char_count=len(result),
                    parse_time_ms=elapsed,
                    url=url
                )
            else:
                self._stats.trafilatura_fail += 1
        
        # Fallback to BeautifulSoup
        result = self._extract_with_bs4(html)
        elapsed = (time.time() - start_time) * 1000
        
        if result and len(result) >= MIN_CONTENT_LENGTH:
            self._stats.bs4_success += 1
            self._stats.bs4_total_chars += len(result)
            self._stats.bs4_total_time_ms += elapsed
            self._save_stats()
            
            return ParseResult(
                content=result,
                parser_used="bs4",
                char_count=len(result),
                parse_time_ms=elapsed,
                url=url
            )
        
        # Content too short - skip
        self._stats.skipped += 1
        self._stats.bs4_fail += 1
        self._save_stats()
        
        return ParseResult(
            content="",
            parser_used="skipped",
            char_count=0,
            parse_time_ms=elapsed,
            url=url,
            error=f"Content too short ({len(result) if result else 0} chars < {MIN_CONTENT_LENGTH})"
        )
    
    async def _try_trafilatura(self, url: str, html: str) -> Optional[str]:
        """Try extracting with trafilatura, with timeout."""
        try:
            loop = asyncio.get_event_loop()
            
            # Run in executor with timeout
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: trafilatura.extract(
                        html,
                        url=url,
                        include_comments=False,
                        include_tables=True,
                        no_fallback=False  # Allow trafilatura's own fallbacks
                    )
                ),
                timeout=TRAFILATURA_TIMEOUT
            )
            
            return result
            
        except asyncio.TimeoutError:
            return None
        except Exception:
            return None
    
    def _extract_with_bs4(self, html: str) -> str:
        """Extract text using BeautifulSoup."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form']):
                tag.decompose()
            
            # Try to find main content
            main_content = (
                soup.find('main') or 
                soup.find('article') or 
                soup.find('div', {'class': ['content', 'post', 'article', 'entry']}) or
                soup.find('div', {'id': ['content', 'main', 'article']}) or
                soup.body
            )
            
            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
            else:
                text = soup.get_text(separator='\n', strip=True)
            
            # Clean up whitespace
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return '\n'.join(lines)
            
        except Exception:
            return ""
    
    def get_stats(self) -> dict:
        """Return parser comparison stats for benchmarking."""
        t_total = self._stats.trafilatura_success + self._stats.trafilatura_fail
        b_total = self._stats.bs4_success + self._stats.bs4_fail
        
        return {
            "trafilatura": {
                "success": self._stats.trafilatura_success,
                "fail": self._stats.trafilatura_fail,
                "success_rate": self._stats.trafilatura_success / t_total if t_total > 0 else 0,
                "avg_chars": self._stats.trafilatura_total_chars / self._stats.trafilatura_success if self._stats.trafilatura_success > 0 else 0,
                "avg_time_ms": self._stats.trafilatura_total_time_ms / self._stats.trafilatura_success if self._stats.trafilatura_success > 0 else 0
            },
            "bs4": {
                "success": self._stats.bs4_success,
                "fail": self._stats.bs4_fail,
                "success_rate": self._stats.bs4_success / b_total if b_total > 0 else 0,
                "avg_chars": self._stats.bs4_total_chars / self._stats.bs4_success if self._stats.bs4_success > 0 else 0,
                "avg_time_ms": self._stats.bs4_total_time_ms / self._stats.bs4_success if self._stats.bs4_success > 0 else 0
            },
            "skipped": self._stats.skipped,
            "total_pages": t_total + self._stats.skipped
        }
    
    def reset_stats(self):
        """Reset all stats."""
        self._stats = ParserStats()
        self._save_stats()
    
    def _load_stats(self):
        """Load stats from file."""
        try:
            if self._stats_file.exists():
                data = json.loads(self._stats_file.read_text())
                self._stats = ParserStats(**data)
        except Exception:
            pass
    
    def _save_stats(self):
        """Save stats to file."""
        try:
            self._stats_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "trafilatura_success": self._stats.trafilatura_success,
                "trafilatura_fail": self._stats.trafilatura_fail,
                "trafilatura_total_chars": self._stats.trafilatura_total_chars,
                "trafilatura_total_time_ms": self._stats.trafilatura_total_time_ms,
                "bs4_success": self._stats.bs4_success,
                "bs4_fail": self._stats.bs4_fail,
                "bs4_total_chars": self._stats.bs4_total_chars,
                "bs4_total_time_ms": self._stats.bs4_total_time_ms,
                "skipped": self._stats.skipped
            }
            self._stats_file.write_text(json.dumps(data, indent=2))
        except Exception:
            pass
