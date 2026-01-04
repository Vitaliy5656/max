import pytest
import asyncio
from src.core.safe_shell import safe_shell

@pytest.mark.asyncio
async def test_safe_shell_injection_prevention():
    """Test that safe_shell blocks dangerous characters."""
    
    dangerous_commands = [
        "dir & echo hacked",
        "echo hello > malware.bat",
        "type file.txt | more",
        "ping 127.0.0.1; whoami"  # Linux style check
    ]
    
    for cmd in dangerous_commands:
        result = await safe_shell.execute(cmd)
        # Should fail due to validation or error not return 0
        assert "Execution error: Dangerous character" in result.stderr or result.return_code == -1
        print(f"Verified blocked: {cmd}")

@pytest.mark.asyncio
async def test_safe_shell_valid_commands():
    """Test that safe_shell allows valid commands."""
    
    # Simple echo (built-in)
    result = await safe_shell.execute("echo test")
    assert result.success is True
    assert "test" in result.stdout

    # List dir (built-in)
    result = await safe_shell.execute("dir")
    assert result.success is True
    assert result.stdout  # Should have output
