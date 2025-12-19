"""
Test script for Gemini Flash API connection.
Run: python tests/test_gemini_connection.py
"""
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set API key before importing provider
# To test: set GEMINI_API_KEY environment variable or uncomment and add your key:
# os.environ["GEMINI_API_KEY"] = "YOUR_API_KEY_HERE"
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")

async def test_gemini():
    """Test Gemini Flash API connection."""
    print("=" * 50)
    print("[TEST] Testing Gemini Flash API Connection")
    print("=" * 50)
    
    try:
        from src.core.lm.providers.gemini import GeminiProvider
        print("[OK] GeminiProvider imported successfully")
    except ImportError as e:
        print(f"[FAIL] Import error: {e}")
        print("[TIP] Install: pip install google-generativeai")
        return False
    
    try:
        provider = GeminiProvider()
        print(f"[OK] Provider initialized with model: {provider.config.model}")
    except Exception as e:
        print(f"[FAIL] Provider init failed: {e}")
        return False
    
    # Test 1: Simple connection test
    print("\n[...] Test 1: Basic connection...")
    try:
        result = await provider.test_connection()
        if result:
            print("[OK] Connection test PASSED")
        else:
            print("[FAIL] Connection test FAILED")
            return False
    except Exception as e:
        print(f"[FAIL] Connection error: {e}")
        return False
    
    # Test 2: Chat completion (non-streaming)
    print("\n[...] Test 2: Chat completion (non-streaming)...")
    try:
        response = await provider.chat(
            messages=[
                {"role": "system", "content": "You are MAX, a helpful AI assistant. Be brief."},
                {"role": "user", "content": "Say: I am MAX and I am working!"}
            ],
            stream=False
        )
        print(f"[OK] Response: {response}")
    except Exception as e:
        print(f"[FAIL] Chat error: {e}")
        return False
    
    # Test 3: Streaming response
    print("\n[...] Test 3: Streaming response...")
    try:
        stream = await provider.chat(
            messages=[
                {"role": "user", "content": "Count from 1 to 5, each number on new line."}
            ],
            stream=True
        )
        print("Response: ", end="")
        async for chunk in stream:
            print(chunk, end="", flush=True)
        print("\n[OK] Streaming PASSED")
    except Exception as e:
        print(f"[FAIL] Streaming error: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("[SUCCESS] ALL TESTS PASSED! Gemini Flash is working!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_gemini())
    sys.exit(0 if success else 1)
