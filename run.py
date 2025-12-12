#!/usr/bin/env python3
"""
MAX AI Assistant - Entry Point

Run with: python run.py
Opens browser at http://localhost:7860
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ui.app import create_app
from src.core.config import config


def main():
    """Launch the MAX AI Assistant."""
    print("🚀 Starting MAX AI Assistant...")
    print(f"   Server: http://{config.host}:{config.port}")
    print(f"   LM Studio: {config.lm_studio.base_url}")
    print()
    
    app = create_app()
    
    app.launch(
        server_name=config.host,
        server_port=config.port,
        share=config.share,
        show_error=True,
        inbrowser=True
    )


if __name__ == "__main__":
    main()
