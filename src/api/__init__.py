"""
MAX AI API package.

Provides modular FastAPI routers for:
- Chat with streaming (SSE)
- Documents (RAG)
- Auto-GPT agent
- Templates
- Metrics (IQ/Empathy)
- Models
- Health checks
- Backups

Architecture:
- app.py - New modular entry point with routers (RECOMMENDED)
- api.py - Legacy monolithic file (still works for backward compat)
- routers/ - Domain-specific routers
- schemas.py - Pydantic models
"""

# Don't auto-import to allow both api.py and app.py usage
# For new code, use: from src.api.app import app
# For legacy code: from src.api.api import app (still works)
