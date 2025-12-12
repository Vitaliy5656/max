import pytest
import asyncio
from pathlib import Path
from src.core.tools import tools, ToolResult

# Mock ALLOWED_PATHS for testing
import src.core.tools
src.core.tools.ALLOWED_PATHS = [Path.cwd() / "sandbox"]

@pytest.fixture
def sandbox_setup():
    # Create sandbox directory
    sandbox = Path.cwd() / "sandbox"
    sandbox.mkdir(exist_ok=True)
    
    # Create a secret file OUTSIDE sandbox
    secret = Path.cwd() / "secret.txt"
    secret.write_text("CONFIDENTIAL")
    
    yield sandbox
    
    # Cleanup
    if secret.exists():
        secret.unlink()
    if sandbox.exists():
        import shutil
        shutil.rmtree(sandbox)

@pytest.mark.asyncio
async def test_path_traversal_list_dir(sandbox_setup):
    """Attempt to list directory outside sandbox."""
    # Try to list the parent directory (where secret.txt is)
    result = await tools.execute("list_directory", {"path": ".."})
    
    # Should FAIL if secure, currently PASSES (vulnerable)
    # We assert "Access denied" to verify the fix
    assert "Access denied" in result or "outside allowed" in result, \
        f"VULNERABILITY DETECTED: Listed outside sandbox! Result: {result}"

@pytest.mark.asyncio
async def test_path_traversal_read_file(sandbox_setup):
    """Attempt to read file outside sandbox."""
    result = await tools.execute("read_file", {"path": "../secret.txt"})
    assert "Access denied" in result or "outside allowed" in result, \
        f"VULNERABILITY DETECTED: Read outside sandbox! Result: {result}"

@pytest.mark.asyncio
async def test_path_traversal_delete_file(sandbox_setup):
    """Attempt to delete file outside sandbox."""
    result = await tools.execute("delete_file", {"path": "../secret.txt"})
    assert "Access denied" in result or "outside allowed" in result, \
        f"VULNERABILITY DETECTED: Deleted outside sandbox! Result: {result}"
