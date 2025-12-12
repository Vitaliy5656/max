import asyncio
import sys
import os
import shutil
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.tools import tools, ToolResult
import src.core.tools

async def main():
    print("[INFO] Starting Security verification...")
    
    # Setup Sandbox
    sandbox = Path.cwd() / "sandbox_test"
    sandbox.mkdir(exist_ok=True)
    
    # Setup Secret (Target)
    secret = Path.cwd() / "secret_test.txt"
    secret.write_text("TOP SECRET DATA")
    
    # Override ALLOWED_PATHS
    src.core.tools.ALLOWED_PATHS = [sandbox]
    print(f"[INFO] Allowed paths restricted to: {sandbox}")
    
    failures = []
    
    # Test 1: List Directory Traversal
    print("\n[Test 1] List Directory Traversal")
    res = await tools.execute("list_directory", {"path": ".."})
    if "Access denied" in res or "outside allowed" in res:
        print("[OK] BLOCKED (Correct)")
    else:
        print(f"[FAIL] FAILED! Result: {res}")
        failures.append("list_directory traversal")

    # Test 2: Read File Traversal
    print("\n[Test 2] Read File Traversal")
    res = await tools.execute("read_file", {"path": "../secret_test.txt"})
    if "Access denied" in res or "outside allowed" in res:
        print("[OK] BLOCKED (Correct)")
    else:
        print(f"[FAIL] FAILED! Result: {res}")
        failures.append("read_file traversal")

    # Test 3: Delete File Traversal
    print("\n[Test 3] Delete File Traversal")
    res = await tools.execute("delete_file", {"path": "../secret_test.txt"})
    if "Access denied" in res or "outside allowed" in res:
        print("[OK] BLOCKED (Correct)")
    else:
        print(f"[FAIL] FAILED! Result: {res}")
        failures.append("delete_file traversal")
        
    # Cleanup
    if sandbox.exists():
        shutil.rmtree(sandbox)
    if secret.exists():
        secret.unlink()
        
    if failures:
        print(f"\n[FAIL] VERIFICATION FAILED. Vulnerabilities found: {failures}")
        sys.exit(1)
    else:
        print(f"\n[OK] ALL SECURITY CHECKS PASSED.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
