"""
GBNF Grammar for Structured LLM Output.

Provides grammar-constrained generation for LM Studio to guarantee
valid JSON output from the LLM Router.

Key features:
    - Routing decision grammar
    - Tool call grammar
    - Fact extraction grammar
    - Response validation grammar
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..logger import log


class GrammarType(Enum):
    """Available grammar types."""
    ROUTING = "routing"
    TOOL_CALL = "tool_call"
    FACT_EXTRACTION = "fact_extraction"
    INTENT_ONLY = "intent_only"
    YES_NO = "yes_no"


# =========================================
# GBNF Grammar Definitions
# =========================================

# Basic JSON primitives
JSON_PRIMITIVES = r'''
ws ::= [ \t\n]*
string ::= "\"" ([^"\\] | "\\" .)* "\""
number ::= "-"? [0-9]+ ("." [0-9]+)?
boolean ::= "true" | "false"
null ::= "null"
'''

# Routing Decision Grammar
ROUTING_GRAMMAR = r'''
root ::= "{" ws routing-content ws "}"
routing-content ::= intent-field "," ws complexity-field "," ws confidence-field ("," ws optional-fields)?

intent-field ::= "\"intent\"" ws ":" ws intent-value
intent-value ::= "\"greeting\"" | "\"question\"" | "\"coding\"" | "\"creative\"" | "\"math\"" | "\"translation\"" | "\"search\"" | "\"system_cmd\"" | "\"task\"" | "\"psychology\"" | "\"vision\"" | "\"goodbye\"" | "\"unknown\""

complexity-field ::= "\"complexity\"" ws ":" ws complexity-value
complexity-value ::= "\"simple\"" | "\"moderate\"" | "\"complex\"" | "\"expert\""

confidence-field ::= "\"confidence\"" ws ":" ws number

optional-fields ::= needs-search-field | needs-code-field | suggested-mode-field
needs-search-field ::= "\"needs_search\"" ws ":" ws boolean
needs-code-field ::= "\"needs_code\"" ws ":" ws boolean
suggested-mode-field ::= "\"suggested_mode\"" ws ":" ws mode-value
mode-value ::= "\"fast\"" | "\"balanced\"" | "\"deep\""
''' + JSON_PRIMITIVES

# Intent Only Grammar (minimal, fastest)
INTENT_ONLY_GRAMMAR = r'''
root ::= "{" ws "\"intent\"" ws ":" ws intent-value ws "}"
intent-value ::= "\"greeting\"" | "\"question\"" | "\"coding\"" | "\"creative\"" | "\"math\"" | "\"translation\"" | "\"search\"" | "\"system_cmd\"" | "\"task\"" | "\"psychology\"" | "\"vision\"" | "\"goodbye\"" | "\"unknown\""
''' + JSON_PRIMITIVES

# Tool Call Grammar
TOOL_CALL_GRAMMAR = r'''
root ::= "{" ws tool-content ws "}"
tool-content ::= name-field "," ws args-field

name-field ::= "\"name\"" ws ":" ws string
args-field ::= "\"arguments\"" ws ":" ws object

object ::= "{" ws (pair ("," ws pair)*)? ws "}"
pair ::= string ws ":" ws value
value ::= string | number | boolean | null | object | array
array ::= "[" ws (value ("," ws value)*)? ws "]"
''' + JSON_PRIMITIVES

# Fact Extraction Grammar
FACT_EXTRACTION_GRAMMAR = r'''
root ::= "{" ws "\"facts\"" ws ":" ws facts-array ws "}"
facts-array ::= "[" ws (fact ("," ws fact)*)? ws "]"

fact ::= "{" ws fact-content ws "}"
fact-content ::= key-field "," ws value-field ("," ws confidence-field)?

key-field ::= "\"key\"" ws ":" ws string
value-field ::= "\"value\"" ws ":" ws string
confidence-field ::= "\"confidence\"" ws ":" ws number
''' + JSON_PRIMITIVES

# Yes/No Grammar (for simple decisions)
YES_NO_GRAMMAR = r'''
root ::= "{" ws "\"answer\"" ws ":" ws answer-value ws "}"
answer-value ::= "\"yes\"" | "\"no\""
''' + JSON_PRIMITIVES


# Grammar registry
GRAMMARS: Dict[GrammarType, str] = {
    GrammarType.ROUTING: ROUTING_GRAMMAR,
    GrammarType.TOOL_CALL: TOOL_CALL_GRAMMAR,
    GrammarType.FACT_EXTRACTION: FACT_EXTRACTION_GRAMMAR,
    GrammarType.INTENT_ONLY: INTENT_ONLY_GRAMMAR,
    GrammarType.YES_NO: YES_NO_GRAMMAR,
}


@dataclass
class GrammarConfig:
    """Configuration for grammar-constrained generation."""
    grammar: str
    grammar_type: GrammarType
    max_tokens: int = 256
    temperature: float = 0.1  # Low temp for structured output


class GrammarManager:
    """
    Manager for GBNF grammars.
    
    Provides grammar strings for LM Studio API calls.
    """
    
    def __init__(self):
        log.debug("GrammarManager initialized")
    
    def get_grammar(self, grammar_type: GrammarType) -> str:
        """Get GBNF grammar string by type."""
        return GRAMMARS.get(grammar_type, INTENT_ONLY_GRAMMAR)
    
    def get_config(self, grammar_type: GrammarType) -> GrammarConfig:
        """Get full config for grammar-constrained generation."""
        grammar = self.get_grammar(grammar_type)
        
        # Adjust max_tokens based on grammar complexity
        max_tokens = {
            GrammarType.ROUTING: 256,
            GrammarType.TOOL_CALL: 512,
            GrammarType.FACT_EXTRACTION: 1024,
            GrammarType.INTENT_ONLY: 64,
            GrammarType.YES_NO: 32,
        }.get(grammar_type, 256)
        
        return GrammarConfig(
            grammar=grammar,
            grammar_type=grammar_type,
            max_tokens=max_tokens
        )
    
    def build_chat_params(
        self,
        grammar_type: GrammarType,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Build parameters for LM Studio chat completion with grammar.
        
        Usage:
            params = grammar_manager.build_chat_params(GrammarType.ROUTING)
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                **params
            )
        """
        config = self.get_config(grammar_type)
        
        return {
            "extra_body": {
                "grammar": config.grammar
            },
            "max_tokens": config.max_tokens,
            "temperature": temperature,
        }
    
    def validate_routing_response(self, response: str) -> Optional[Dict]:
        """
        Validate and parse routing response.
        
        Returns parsed dict or None if invalid.
        """
        import json
        
        try:
            data = json.loads(response)
            
            # Validate required fields
            if "intent" not in data:
                return None
            
            # Normalize
            return {
                "intent": data.get("intent", "unknown"),
                "complexity": data.get("complexity", "simple"),
                "confidence": float(data.get("confidence", 0.5)),
                "needs_search": data.get("needs_search", False),
                "needs_code": data.get("needs_code", False),
                "suggested_mode": data.get("suggested_mode", "fast"),
            }
        except (json.JSONDecodeError, ValueError) as e:
            log.warn(f"Failed to parse routing response: {e}")
            return None


# Global instance
_grammar_manager: Optional[GrammarManager] = None


def get_grammar_manager() -> GrammarManager:
    """Get or create global GrammarManager."""
    global _grammar_manager
    if _grammar_manager is None:
        _grammar_manager = GrammarManager()
    return _grammar_manager


def get_routing_grammar() -> str:
    """Quick helper to get routing grammar."""
    return get_grammar_manager().get_grammar(GrammarType.ROUTING)


def get_intent_grammar() -> str:
    """Quick helper to get intent-only grammar."""
    return get_grammar_manager().get_grammar(GrammarType.INTENT_ONLY)
