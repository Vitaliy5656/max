"""
URL Validation Module for Anti-Hallucination System.

Validates URLs through multiple checks:
- Format validation
- DNS resolution
- HTTP accessibility
- Result caching
"""
import asyncio
import socket
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlparse

import validators
import httpx


@dataclass
class ValidationResult:
    """Result of URL validation."""
    url: str
    valid: bool
    confidence: float  # 0.0 - 1.0
    error_reason: Optional[str] = None
    checked_at: Optional[datetime] = None


class URLValidator:
    """
    Validates URLs through multi-layer checks.
    
    Validation layers:
    1. Format check (RFC compliance)
    2. DNS resolution (domain exists)
    3. HTTP accessibility (server responds)
    """
    
    def __init__(self, cache_ttl_seconds: int = 3600):
        """
        Initialize validator.
        
        Args:
            cache_ttl_seconds: Time to live for cache entries (default: 1 hour)
        """
        self._cache: dict[str, ValidationResult] = {}
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)
        
    async def validate_url(self, url: str) -> ValidationResult:
        """
        Validate URL through all layers.
        
        Args:
            url: URL to validate
            
        Returns:
            ValidationResult with confidence score
        """
        # Check cache first
        cached = self._get_cached(url)
        if cached:
            return cached
        
        result = await self._validate_full(url)
        self._cache[url] = result
        return result
    
    def _get_cached(self, url: str) -> Optional[ValidationResult]:
        """Get cached validation result if still valid."""
        if url not in self._cache:
            return None
        
        cached = self._cache[url]
        if cached.checked_at:
            age = datetime.now() - cached.checked_at
            if age > self._cache_ttl:
                del self._cache[url]
                return None
        
        return cached
    
    async def _validate_full(self, url: str) -> ValidationResult:
        """Perform full validation of URL."""
        now = datetime.now()
        
        # Layer 1: Format validation
        if not validators.url(url):
            return ValidationResult(
                url=url,
                valid=False,
                confidence=0.0,
                error_reason="Invalid URL format",
                checked_at=now
            )
        
        # Parse URL
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
        except Exception as e:
            return ValidationResult(
                url=url,
                valid=False,
                confidence=0.0,
                error_reason=f"URL parse error: {str(e)}",
                checked_at=now
            )
        
        # Layer 2: DNS resolution
        dns_valid = await self._check_dns(domain)
        if not dns_valid:
            return ValidationResult(
                url=url,
                valid=False,
                confidence=0.0,
                error_reason=f"Domain does not exist: {domain}",
                checked_at=now
            )
        
        # Layer 3: HTTP accessibility (HEAD request)
        http_valid, http_error = await self._check_http(url)
        
        if http_valid:
            return ValidationResult(
                url=url,
                valid=True,
                confidence=1.0,
                checked_at=now
            )
        else:
            # Domain exists but HTTP failed - medium confidence
            return ValidationResult(
                url=url,
                valid=False,
                confidence=0.5,  # DNS works, but HTTP doesn't
                error_reason=f"HTTP check failed: {http_error}",
                checked_at=now
            )
    
    async def _check_dns(self, domain: str) -> bool:
        """Check if domain exists via DNS lookup."""
        try:
            loop = asyncio.get_event_loop()
            # Run DNS lookup in thread pool (blocking operation)
            await loop.run_in_executor(
                None,
                socket.gethostbyname,
                domain
            )
            return True
        except socket.gaierror:
            return False
        except Exception:
            return False
    
    async def _check_http(self, url: str, timeout: float = 5.0) -> tuple[bool, Optional[str]]:
        """
        Check if URL is accessible via HTTP HEAD request.
        
        Args:
            url: URL to check
            timeout: Request timeout in seconds
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.head(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (MAX AI Assistant URL Validator)"}
                )
                
                # Accept 2xx and 3xx status codes
                if 200 <= response.status_code < 400:
                    return True, None
                else:
                    return False, f"HTTP {response.status_code}"
                    
        except httpx.ConnectError:
            return False, "Connection failed"
        except httpx.TimeoutException:
            return False, "Request timeout"
        except httpx.HTTPError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def clear_cache(self):
        """Clear validation cache."""
        self._cache.clear()


# Global URL validator instance
url_validator = URLValidator(cache_ttl_seconds=3600)
