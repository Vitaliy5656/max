"""
Response Validation Module.

Validates AI-generated responses for fabricated content:
- Extracts URLs from response
- Checks if URLs appear in tool results
- Detects hallucinated information
"""
import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class ResponseValidation:
    """Result of response validation."""
    has_fabricated_urls: bool
    fabricated_urls: list[str]
    fabricated_phones: list[str]
    fabricated_emails: list[str]
    risk_score: float  # 0.0 (safe) to 1.0 (high hallucination risk)
    warnings: list[str]


class ResponseValidator:
    """
    Validates AI responses for hallucinated content.
    
    Checks:
    - URLs not present in tool results
    - Phone numbers not in source data
    - Email addresses not in source data
    - Specific details (dates, names) not grounded in sources
    """
    
    # Regex patterns for extraction
    URL_PATTERN = re.compile(
        r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?',
        re.IGNORECASE
    )
    
    PHONE_PATTERN = re.compile(
        r'\+?\d{1,4}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
        re.MULTILINE
    )
    
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )
    
    def __init__(self):
        pass
    
    async def validate_response(
        self, 
        response: str, 
        tool_results: Optional[str] = None
    ) -> ResponseValidation:
        """
        Validate AI response for hallucinated content.
        
        Args:
            response: AI-generated response text
            tool_results: Combined tool results (search results, webpage content, etc.)
            
        Returns:
            ResponseValidation with risk assessment
        """
        warnings = []
        fabricated_urls = []
        fabricated_phones = []
        fabricated_emails = []
        
        # Extract all URLs from response
        response_urls = self.URL_PATTERN.findall(response)
        
        # Extract all phone numbers
        response_phones = self.PHONE_PATTERN.findall(response)
        
        # Extract all emails
        response_emails = self.EMAIL_PATTERN.findall(response)
        
        # If no tool results provided, can't validate
        if not tool_results:
            # Still check if response has suspicious detailed info
            if response_urls or response_phones or response_emails:
                warnings.append(
                    "Response contains URLs/contacts but no tool results to verify against"
                )
            
            return ResponseValidation(
                has_fabricated_urls=False,
                fabricated_urls=[],
                fabricated_phones=[],
                fabricated_emails=[],
                risk_score=0.3 if warnings else 0.0,
                warnings=warnings
            )
        
        # Check URLs against tool results
        for url in response_urls:
            if url not in tool_results:
                fabricated_urls.append(url)
                warnings.append(f"URL not in search results: {url}")
        
        # Check phone numbers against tool results
        for phone in response_phones:
            # Normalize phone for comparison (remove spaces, dashes)
            normalized = re.sub(r'[-.\s()]', '', phone)
            normalized_results = re.sub(r'[-.\s()]', '', tool_results)
            
            if normalized not in normalized_results:
                fabricated_phones.append(phone)
                warnings.append(f"Phone number not in sources: {phone}")
        
        # Check emails against tool results
        for email in response_emails:
            if email.lower() not in tool_results.lower():
                fabricated_emails.append(email)
                warnings.append(f"Email not in sources: {email}")
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(
            fabricated_urls, 
            fabricated_phones, 
            fabricated_emails
        )
        
        return ResponseValidation(
            has_fabricated_urls=len(fabricated_urls) > 0,
            fabricated_urls=fabricated_urls,
            fabricated_phones=fabricated_phones,
            fabricated_emails=fabricated_emails,
            risk_score=risk_score,
            warnings=warnings
        )
    
    def _calculate_risk_score(
        self, 
        urls: list[str], 
        phones: list[str], 
        emails: list[str]
    ) -> float:
        """
        Calculate hallucination risk score.
        
        High risk indicators:
        - Multiple fabricated URLs
        - Phone numbers (very specific)
        - Email addresses (very specific)
        """
        score = 0.0
        
        # URLs: 0.3 per fabricated URL
        score += len(urls) * 0.3
        
        # Phones: 0.4 per fabricated phone (high specificity)
        score += len(phones) * 0.4
        
        # Emails: 0.4 per fabricated email (high specificity)
        score += len(emails) * 0.4
        
        # Cap at 1.0
        return min(score, 1.0)


# Global response validator
response_validator = ResponseValidator()
