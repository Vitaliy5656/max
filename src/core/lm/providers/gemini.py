"""
Gemini API Provider for MAX AI.

Uses direct REST API calls to Google's Gemini endpoint.
No deprecated SDK required!
"""
import os
import asyncio
import httpx
from typing import AsyncIterator, Optional
from dataclasses import dataclass

from ...logger import log


@dataclass
class GeminiConfig:
    """Gemini provider configuration."""
    api_key: str = ""
    model: str = "gemini-2.5-flash"
    temperature: float = 0.7
    max_tokens: int = 4096
    
    @classmethod
    def from_env(cls) -> "GeminiConfig":
        """Load config from environment variables."""
        return cls(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        )


class GeminiProvider:
    """
    Async Gemini API client using direct REST calls.
    
    Uses: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
    """
    
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    
    def __init__(self, config: Optional[GeminiConfig] = None):
        self.config = config or GeminiConfig.from_env()
        
        if not self.config.api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        
        self._client = httpx.AsyncClient(timeout=60.0)
        
        log.api(f"GeminiProvider initialized with model: {self.config.model}")
    
    def _build_url(self, action: str = "generateContent") -> str:
        """Build API URL with key."""
        return f"{self.BASE_URL}/models/{self.config.model}:{action}?key={self.config.api_key}"
    
    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        """
        Convert OpenAI-format messages to Gemini format.
        """
        contents = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                # Prepend system message as user context
                contents.insert(0, {
                    "role": "user",
                    "parts": [{"text": f"[System Instructions]: {content}"}]
                })
            elif role == "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif role == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })
        
        return contents
    
    async def chat(
        self,
        messages: list[dict],
        stream: bool = True,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str] | str:
        """
        Send chat completion request via REST API.
        """
        contents = self._convert_messages(messages)
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature or self.config.temperature,
                "maxOutputTokens": max_tokens or self.config.max_tokens,
            }
        }
        
        if stream:
            return self._stream_response(payload)
        else:
            return await self._generate(payload)
    
    async def _generate(self, payload: dict) -> str:
        """Non-streaming generation."""
        url = self._build_url("generateContent")
        
        try:
            response = await self._client.post(url, json=payload)
            
            if response.status_code == 429:
                log.warn("Gemini rate limit hit (429). Waiting 30s...")
                await asyncio.sleep(30)
                response = await self._client.post(url, json=payload)
            
            if response.status_code != 200:
                error_text = response.text
                log.error(f"Gemini API error {response.status_code}: {error_text}")
                return f"[Ошибка Gemini: {response.status_code}]"
            
            data = response.json()
            
            # Extract text from response
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            
            return "[Пустой ответ от Gemini]"
            
        except Exception as e:
            log.error(f"Gemini request error: {e}")
            return f"[Ошибка: {str(e)}]"
    
    async def _stream_response(self, payload: dict) -> AsyncIterator[str]:
        """Stream response using SSE."""
        url = self._build_url("streamGenerateContent") + "&alt=sse"
        
        try:
            async with self._client.stream("POST", url, json=payload) as response:
                if response.status_code == 429:
                    log.warn("Gemini rate limit hit (429)")
                    yield "[Превышен лимит запросов Gemini. Подождите 30 секунд.]"
                    return
                
                if response.status_code != 200:
                    yield f"[Ошибка Gemini: {response.status_code}]"
                    return
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            import json
                            data = json.loads(line[6:])
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                if parts:
                                    text = parts[0].get("text", "")
                                    if text:
                                        yield text
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            log.error(f"Gemini stream error: {e}")
            yield f"\n[Ошибка Gemini: {str(e)}]"
    
    async def test_connection(self) -> bool:
        """Test API connection."""
        try:
            response = await self.chat(
                [{"role": "user", "content": "Say 'OK' in one word."}],
                stream=False
            )
            return bool(response) and "Ошибка" not in response
        except Exception as e:
            log.error(f"Gemini connection test failed: {e}")
            return False
    
    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()


# Singleton instance (lazy)
_gemini_provider: Optional[GeminiProvider] = None


def get_gemini_provider() -> GeminiProvider:
    """Get or create the global GeminiProvider instance."""
    global _gemini_provider
    
    if _gemini_provider is None:
        _gemini_provider = GeminiProvider()
    
    return _gemini_provider
