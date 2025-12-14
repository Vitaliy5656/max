"""
Safe Shell for MAX AI Assistant.

Cross-platform shell executor with Windows built-in command support.
Windows built-in commands (dir, echo, type, etc.) are automatically wrapped
with cmd /c for proper execution.

Usage:
    from .safe_shell import safe_shell
    result = await safe_shell.execute("dir", cwd="C:\\Users")
"""
import asyncio
import platform
import shlex
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable


# Windows built-in commands that require cmd /c wrapping
WINDOWS_BUILTINS = {
    "dir", "echo", "type", "copy", "move", "del", "rd", "md",
    "ren", "cls", "date", "time", "ver", "vol", "path", "set",
    "cd", "pushd", "popd", "mkdir", "rmdir", "erase", "color",
    "title", "prompt", "assoc", "ftype", "break", "call", "chcp",
    "chdir", "if", "for", "goto", "rem", "shift", "start", "exit"
}


@dataclass
class ShellResult:
    """Result of shell command execution."""
    stdout: str
    stderr: str
    return_code: int
    timed_out: bool = False
    
    @property
    def success(self) -> bool:
        """Check if command succeeded."""
        return self.return_code == 0 and not self.timed_out


class SafeShell:
    """
    Cross-platform shell with Windows built-in support.
    
    Automatically detects Windows built-in commands and wraps them
    with cmd /c for proper execution via asyncio.create_subprocess_exec.
    
    Features:
    - Windows built-in command detection
    - Timeout handling with process kill
    - Real-time output streaming (optional callback)
    - Output truncation to prevent memory issues
    """
    
    MAX_OUTPUT_SIZE = 100 * 1024  # 100KB max output
    
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
    
    def _needs_shell_wrap(self, command: str) -> bool:
        """Check if command needs cmd /c wrapper (Windows only)."""
        if not self.is_windows:
            return False
        
        # Parse first token of command
        parts = command.strip().split(None, 1)
        if not parts:
            return False
        
        base_cmd = parts[0].lower()
        # Remove .exe extension if present
        if base_cmd.endswith('.exe'):
            base_cmd = base_cmd[:-4]
        
        return base_cmd in WINDOWS_BUILTINS
    
    def _validate_command(self, command: str) -> None:
        """
        Validate command for dangerous characters.
        
        Raises ValueError if dangerous characters detection.
        """
        # Block shell control characters unless strictly necessary (and even then be careful)
        # & = chain commands
        # | = pipe
        # <, > = redirection
        # ; = chain (Linux)
        # ` = subshell (Linux)
        # $ = variable (Linux/PowerShell)
        
        dangerous_chars = ['&', '|', '>', '<', ';', '`', '$']
        for char in dangerous_chars:
            if char in command:
                 raise ValueError(f"Dangerous character '{char}' detected in command. Execution blocked for security.")

    def _prepare_command(self, command: str) -> tuple[str, ...]:
        """
        Prepare command for execution.
        
        Returns tuple of arguments for create_subprocess_exec.
        Windows built-in commands are wrapped with cmd /c.
        """
        # Security validation
        self._validate_command(command)

        if self._needs_shell_wrap(command):
            # Use cmd /c for Windows built-ins
            # Critical P0 Fix: Don't just pass the string.
            # We must be careful even with cmd /c.
            # But create_subprocess_exec will handle arg quoting for the list.
            
            # If command is 'dir /s', we want ('cmd', '/c', 'dir', '/s') ? 
            # No, 'dir /s' is a single shell command string for cmd /c.
            # Wait, subprocess.exec(['cmd', '/c', 'dir /s']) works? 
            # Ideally: ['cmd', '/c', 'dir', '/s'] 
            # But the user passes a string "dir /s".
            
            # Let's split safe items.
            tokens = shlex.split(command, posix=False) if self.is_windows else shlex.split(command)
            return ("cmd", "/c", *tokens)
        
        # Parse command using shlex for proper quoting
        try:
            if self.is_windows:
                # shlex.split on Windows needs posix=False
                args = shlex.split(command, posix=False)
            else:
                args = shlex.split(command)
            return tuple(args)
        except ValueError as e:
            # If shlex fails, try simple split for Windows
            if self.is_windows:
                return tuple(command.split())
            raise e
    
    async def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: float = 60.0,
        on_stdout: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> ShellResult:
        """
        Execute a shell command.
        
        Args:
            command: Command string to execute
            cwd: Working directory (optional)
            timeout: Maximum execution time in seconds
            on_stdout: Async callback for real-time output streaming
            
        Returns:
            ShellResult with stdout, stderr, return_code, and timed_out flag
        """
        try:
            args = self._prepare_command(command)
            if not args:
                return ShellResult("", "Empty command", -1)
            
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            stdout_parts: list[str] = []
            stderr_parts: list[str] = []
            total_output_size = 0
            timed_out = False
            
            async def read_stream(stream, parts: list, is_stdout: bool):
                nonlocal total_output_size
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    
                    decoded = line.decode(errors='replace')
                    
                    # Check output size limit
                    if total_output_size + len(decoded) > self.MAX_OUTPUT_SIZE:
                        parts.append("\n[... output truncated ...]\n")
                        break
                    
                    total_output_size += len(decoded)
                    parts.append(decoded)
                    
                    # Call streaming callback if provided
                    if is_stdout and on_stdout:
                        try:
                            await on_stdout(decoded)
                        except Exception:
                            pass  # Ignore callback errors
            
            try:
                # Read stdout and stderr concurrently with timeout
                await asyncio.wait_for(
                    asyncio.gather(
                        read_stream(proc.stdout, stdout_parts, True),
                        read_stream(proc.stderr, stderr_parts, False)
                    ),
                    timeout=timeout
                )
                await proc.wait()
            except asyncio.TimeoutError:
                timed_out = True
                proc.kill()
                await proc.wait()
            
            stdout = "".join(stdout_parts)
            stderr = "".join(stderr_parts)
            
            return ShellResult(
                stdout=stdout,
                stderr=stderr,
                return_code=proc.returncode if proc.returncode is not None else -1,
                timed_out=timed_out
            )
            
        except FileNotFoundError as e:
            return ShellResult("", f"Command not found: {e}", -1)
        except PermissionError as e:
            return ShellResult("", f"Permission denied: {e}", -1)
        except Exception as e:
            return ShellResult("", f"Execution error: {str(e)}", -1)


# Global instance
safe_shell = SafeShell()
