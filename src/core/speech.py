"""
Speech-to-Text Module using LM Studio Whisper.

Features:
- Audio transcription via LM Studio's audio endpoint
- Support for common audio formats
- Language detection
"""
import base64
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import httpx

from .config import config


@dataclass
class TranscriptionResult:
    """Result of audio transcription."""
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None
    

class SpeechToText:
    """
    Speech-to-text using LM Studio's Whisper model.
    
    Requirements:
    - LM Studio must have a Whisper model loaded
    - Uses /v1/audio/transcriptions endpoint
    """
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or config.lm_studio.base_url
        self._audio_endpoint = f"{self.base_url}/audio/transcriptions"
        
    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file (mp3, wav, m4a, webm, etc.)
            language: Optional language hint (e.g., 'ru', 'en')
            prompt: Optional context prompt to guide transcription
            
        Returns:
            TranscriptionResult with transcribed text
        """
        path = Path(audio_path).expanduser().resolve()
        
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Read audio file
        audio_bytes = path.read_bytes()
        
        # Prepare multipart form data
        files = {
            "file": (path.name, audio_bytes, self._get_mime_type(path.suffix))
        }
        
        data = {
            "model": "whisper-1"  # LM Studio uses this as default
        }
        
        if language:
            data["language"] = language
        if prompt:
            data["prompt"] = prompt
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self._audio_endpoint,
                    files=files,
                    data=data
                )
                response.raise_for_status()
                
            result = response.json()
            
            return TranscriptionResult(
                text=result.get("text", ""),
                language=result.get("language"),
                duration=result.get("duration")
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise RuntimeError(
                    "Whisper model not loaded in LM Studio. "
                    "Please load a Whisper model first."
                )
            raise
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {str(e)}")
    
    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio from bytes.
        
        Args:
            audio_bytes: Raw audio bytes
            filename: Filename hint for format detection
            language: Optional language hint
            
        Returns:
            TranscriptionResult with transcribed text
        """
        suffix = Path(filename).suffix
        mime_type = self._get_mime_type(suffix)
        
        files = {
            "file": (filename, audio_bytes, mime_type)
        }
        
        data = {"model": "whisper-1"}
        if language:
            data["language"] = language
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self._audio_endpoint,
                    files=files,
                    data=data
                )
                response.raise_for_status()
                
            result = response.json()
            return TranscriptionResult(text=result.get("text", ""))
            
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {str(e)}")
    
    def _get_mime_type(self, suffix: str) -> str:
        """Get MIME type for audio format."""
        mime_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".webm": "audio/webm",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
        }
        return mime_types.get(suffix.lower(), "audio/wav")
    
    async def is_available(self) -> bool:
        """Check if Whisper is available in LM Studio."""
        try:
            # Try a minimal request to check endpoint
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Just check if endpoint responds
                response = await client.get(
                    self.base_url.replace("/v1", "") + "/api/status"
                )
                return response.status_code == 200
        except httpx.ConnectError:
            # Server not running
            return False
        except httpx.TimeoutException:
            # Server too slow
            return False
        except Exception as e:
            # Log unexpected errors for debugging
            print(f"Speech availability check failed: {type(e).__name__}: {e}")
            return False


# Global speech-to-text instance
speech = SpeechToText()
