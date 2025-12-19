"""
Test script to verify Phi-3.5 extraction model loading.
"""
import sys
from pathlib import Path

print("=" * 60)
print("Phi-3.5 Extraction Model Test")
print("=" * 60)

# Step 1: Check if llama-cpp-python is installed
print("\n[1/4] Checking llama-cpp-python...")
try:
    from llama_cpp import Llama
    print("✅ llama-cpp-python is installed")
except ImportError:
    print("❌ llama-cpp-python NOT installed!")
    print("Install with: pip install llama-cpp-python")
    sys.exit(1)

# Step 2: Check if model file exists
print("\n[2/4] Checking model file...")
model_path = Path(__file__).parent / "Phi-3.5-mini-instruct-GGUF" / "Phi-3.5-mini-instruct.IQ1_S.gguf"
print(f"Looking for: {model_path}")

if not model_path.exists():
    print(f"❌ Model file NOT found!")
    print(f"Expected path: {model_path}")
    sys.exit(1)

file_size_mb = model_path.stat().st_size / (1024 * 1024)
print(f"✅ Model file found ({file_size_mb:.1f} MB)")

# Step 3: Try to load model
print("\n[3/4] Loading model (this may take 5-10 seconds)...")
try:
    llm = Llama(
        model_path=str(model_path),
        n_ctx=512,  # Small context
        n_threads=4,
        n_gpu_layers=0,  # CPU only
        verbose=False
    )
    print("✅ Model loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    sys.exit(1)

# Step 4: Test inference
print("\n[4/4] Testing fact extraction...")
test_prompt = """Extract facts about the user from their message.

MESSAGE: "My name is John, I love programming"

If NO facts - respond: NO

If facts exist - list each fact on a SEPARATE line in this format:
(personal) ...
(preference) ...

FACTS:"""

try:
    response = llm(
        test_prompt,
        max_tokens=150,
        temperature=0.1,
        stop=["USER:", "\n\n\n"],
        echo=False
    )
    
    result = response['choices'][0]['text'].strip()
    print(f"✅ Inference successful!")
    print(f"\nModel response:")
    print("-" * 40)
    print(result)
    print("-" * 40)
    
    # Check if response makes sense
    if "(personal)" in result or "(preference)" in result:
        print("\n🎉 SUCCESS! Model is working correctly!")
    else:
        print("\n⚠️  Model responded but format may be unexpected")
        
except Exception as e:
    print(f"❌ Inference failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("Test completed successfully! ✅")
print("=" * 60)
