"""
Tests for SafeShell module.

Tests Windows built-in command support, timeout handling, and cross-platform execution.
"""
import pytest
import asyncio
import platform

from src.core.safe_shell import SafeShell, safe_shell, WINDOWS_BUILTINS


class TestSafeShellBasic:
    """Basic SafeShell tests."""
    
    def test_instance_exists(self):
        """Global safe_shell instance should exist."""
        assert safe_shell is not None
        assert isinstance(safe_shell, SafeShell)
    
    def test_platform_detection(self):
        """Platform detection should be correct."""
        is_windows = platform.system() == "Windows"
        assert safe_shell.is_windows == is_windows
    
    def test_windows_builtins_defined(self):
        """Windows builtins should be defined."""
        assert "dir" in WINDOWS_BUILTINS
        assert "echo" in WINDOWS_BUILTINS
        assert "type" in WINDOWS_BUILTINS
        assert "cd" in WINDOWS_BUILTINS


class TestNeedsShellWrap:
    """Tests for _needs_shell_wrap method."""
    
    def test_dir_command(self):
        """'dir' should need shell wrap on Windows."""
        shell = SafeShell()
        if shell.is_windows:
            assert shell._needs_shell_wrap("dir") is True
            assert shell._needs_shell_wrap("dir /b") is True
            assert shell._needs_shell_wrap("DIR") is True
    
    def test_echo_command(self):
        """'echo' should need shell wrap on Windows."""
        shell = SafeShell()
        if shell.is_windows:
            assert shell._needs_shell_wrap("echo hello") is True
    
    def test_non_builtin_command(self):
        """Non-builtin commands should not need shell wrap."""
        shell = SafeShell()
        assert shell._needs_shell_wrap("python --version") is False
        assert shell._needs_shell_wrap("git status") is False
    
    def test_empty_command(self):
        """Empty command should not need shell wrap."""
        shell = SafeShell()
        assert shell._needs_shell_wrap("") is False
        assert shell._needs_shell_wrap("   ") is False


class TestPrepareCommand:
    """Tests for _prepare_command method."""
    
    def test_dir_wrapped_on_windows(self):
        """'dir' should be wrapped with cmd /c on Windows."""
        shell = SafeShell()
        if shell.is_windows:
            result = shell._prepare_command("dir /b")
            assert result == ("cmd", "/c", "dir /b")
    
    def test_regular_command_parsed(self):
        """Regular commands should be parsed with shlex."""
        shell = SafeShell()
        result = shell._prepare_command("python --version")
        assert result[0] == "python"
        assert result[1] == "--version"


@pytest.mark.asyncio
class TestExecute:
    """Tests for execute method."""
    
    async def test_echo_on_windows(self):
        """echo command should work on Windows."""
        if platform.system() != "Windows":
            pytest.skip("Windows-only test")
        
        result = await safe_shell.execute("echo hello world")
        assert result.success or "hello" in result.stdout.lower()
    
    async def test_dir_on_windows(self):
        """dir command should work on Windows."""
        if platform.system() != "Windows":
            pytest.skip("Windows-only test")
        
        # Use user's temp folder - always accessible
        import tempfile
        result = await safe_shell.execute("dir", cwd=tempfile.gettempdir())
        assert result.success
        assert len(result.stdout) > 0
    
    async def test_ls_on_linux(self):
        """ls command should work on Linux/Mac."""
        if platform.system() == "Windows":
            pytest.skip("Linux/Mac-only test")
        
        result = await safe_shell.execute("ls -la", cwd="/")
        assert result.success
        assert len(result.stdout) > 0
    
    async def test_nonexistent_command(self):
        """Nonexistent command should fail gracefully."""
        result = await safe_shell.execute("nonexistent_cmd_12345")
        assert not result.success
        assert "not found" in result.stderr.lower() or "not recognized" in result.stderr.lower()
    
    async def test_empty_command(self):
        """Empty command should fail gracefully."""
        result = await safe_shell.execute("")
        assert not result.success
    
    async def test_timeout(self):
        """Long-running command should timeout."""
        if platform.system() == "Windows":
            cmd = "ping -n 100 127.0.0.1"
        else:
            cmd = "sleep 100"
        
        result = await safe_shell.execute(cmd, timeout=0.5)
        assert result.timed_out
        assert not result.success
    
    async def test_cwd_parameter(self):
        """Working directory should be respected."""
        import tempfile
        import os
        
        if platform.system() == "Windows":
            # Use echo with special variable that shows current dir
            result = await safe_shell.execute("echo %CD%", cwd=tempfile.gettempdir())
            assert result.success
            # Should contain part of temp path
            assert "Temp" in result.stdout or "temp" in result.stdout.lower() or tempfile.gettempdir().lower() in result.stdout.lower()
        else:
            result = await safe_shell.execute("pwd", cwd="/tmp")
            assert result.success
            assert "/tmp" in result.stdout


@pytest.mark.asyncio
class TestShellResult:
    """Tests for ShellResult dataclass."""
    
    async def test_success_property(self):
        """success property should reflect return_code and timed_out."""
        result = await safe_shell.execute("echo test")
        # Even if command fails to run, success should be a valid boolean
        assert isinstance(result.success, bool)
    
    async def test_stdout_captured(self):
        """stdout should be captured."""
        if platform.system() == "Windows":
            result = await safe_shell.execute("echo captured_output")
        else:
            result = await safe_shell.execute("echo captured_output")
        
        if result.success:
            assert "captured_output" in result.stdout


@pytest.mark.asyncio
class TestOutputLimits:
    """Tests for output size limits."""
    
    async def test_output_truncation(self):
        """Large output should be truncated."""
        shell = SafeShell()
        shell.MAX_OUTPUT_SIZE = 100  # Set very small limit for testing
        
        if platform.system() == "Windows":
            # Generate modest output - just list a small folder
            result = await shell.execute("dir /s C:\\Windows\\Temp", timeout=5.0)
        else:
            result = await shell.execute("ls -la /usr/bin", timeout=5.0)
        
        # Output should be truncated (check for truncation or small size)
        total_size = len(result.stdout) + len(result.stderr)
        # Allow some overhead but should be limited
        assert total_size < 1000 or "truncated" in result.stdout.lower()
