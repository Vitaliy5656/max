"""
Hallucination Detection Module.

Provides advanced heuristics for detecting AI hallucinations:
- Pattern matching for suspicious content
- Confidence scoring
- Risk assessment
"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class HallucinationRisk:
    """Hallucination risk assessment."""
    risk_level: str  # "low", "medium", "high"
    risk_score: float  # 0.0 - 1.0
    risk_factors: list[str]
    recommended_action: str


class HallucinationDetector:
    """
    Detects potential hallucinations using heuristic patterns.
    
    Red flags:
    - Specific URLs with subpaths (/about, /contact, etc.)
    - Exact phone numbers
    - Email addresses
    - Precise dates/times
    - Numerical data (statistics, prices)
    """
    
    def __init__(self):
        # Patterns that indicate high-confidence fabrication
        self.high_risk_patterns = [
            (r'https?://[^\s]+/(?:about|contact|faq|support|help|info)', 
             "Specific URL subpath (e.g., /about, /contact)"),
            (r'\+\d{1,3}[-.\s]?\d{3}[-.\s]?\d{2}[-.\s]?\d{2}', 
             "Specific phone number format"),
            (r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}', 
             "Email address"),
            (r'SSL[- ]?сертификат', 
             "Technical details about SSL certificate"),
        ]
        
        self.medium_risk_patterns = [
            (r'\d{1,2}\s(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s\d{4}', 
             "Specific date"),
            (r'обновлен[ао]?\s+\d{1,2}', 
             "Last updated date claim"),
            (r'версия\s+\d+\.\d+', 
             "Specific version number"),
        ]
    
    async def detect_hallucination_risk(
        self, 
        response: str, 
        sources: Optional[str] = None
    ) -> HallucinationRisk:
        """
        Analyze response for hallucination risk.
        
        Args:
            response: AI-generated response
            sources: Source material (tool results)
            
        Returns:
            HallucinationRisk assessment
        """
        risk_factors = []
        risk_scores = []
        
        # Check high-risk patterns
        for pattern, description in self.high_risk_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                # Check if match appears in sources
                if sources:
                    for match in matches:
                        if match.lower() not in sources.lower():
                            risk_factors.append(f"{description}: {match}")
                            risk_scores.append(0.8)
                else:
                    # No sources to verify against
                    risk_factors.append(f"{description} (unverified)")
                    risk_scores.append(0.6)
        
        # Check medium-risk patterns
        for pattern, description in self.medium_risk_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                if sources:
                    for match in matches:
                        if match.lower() not in sources.lower():
                            risk_factors.append(f"{description}: {match}")
                            risk_scores.append(0.5)
                else:
                    risk_factors.append(f"{description} (unverified)")
                    risk_scores.append(0.3)
        
        # Calculate overall risk score
        if risk_scores:
            risk_score = sum(risk_scores) / len(risk_scores)
        else:
            risk_score = 0.0
        
        # Determine risk level
        if risk_score >= 0.7:
            risk_level = "high"
            action = "BLOCK or add strong warning"
        elif risk_score >= 0.4:
            risk_level = "medium"
            action = "Add verification warning"
        else:
            risk_level = "low"
            action = "Allow response"
        
        return HallucinationRisk(
            risk_level=risk_level,
            risk_score=risk_score,
            risk_factors=risk_factors,
            recommended_action=action
        )


# Global hallucination detector
hallucination_detector = HallucinationDetector()
