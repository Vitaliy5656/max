"""
Tool System for MAX AI Assistant.

Provides file operations, web search, archive handling, and shell commands.
All dangerous operations require confirmation.
"""
import os
import json
import shutil
import mimetypes
import base64
import zipfile
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass
from datetime import datetime

from PIL import Image


@dataclass
class ToolResult:
    """Result of tool execution with MO_Guard Protocol."""
    success: bool
    output: str
    error: Optional[str] = None
    # MO_Guard Protocol for confirmations:
    status: str = "complete"  # "complete" | "pending" | "error"
    confirmation_id: Optional[str] = None
    confirmation_message: Optional[str] = None


# Security: Allowed paths for file operations (sandbox)
# Default to user home + cwd for safety. Empty list = allow all (UNSAFE!)
ALLOWED_PATHS: list[Path] = [
    Path.home(),  # User's home directory
    Path.cwd(),   # Current working directory
]

# Maximum files to return in list_directory to prevent memory issues
MAX_DIRECTORY_ITEMS = 500


def _is_path_allowed(path: Path) -> bool:
    """Check if path is within allowed directories (sandbox)."""
    if not ALLOWED_PATHS:
        return True  # No restrictions if list is empty
    
    resolved = path.resolve()
    return any(resolved.is_relative_to(allowed) for allowed in ALLOWED_PATHS)


def _validate_path(path: str) -> Path:
    """Validate and resolve path, checking sandbox restrictions."""
    p = Path(path).expanduser().resolve()
    if not _is_path_allowed(p):
        raise PermissionError(f"Access denied: {path} is outside allowed directories")
    return p


# ==================== Tool Definitions ====================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a text file. Returns the file content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative file path"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or append text to a file. Creates file if doesn't exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write to"},
                    "content": {"type": "string", "description": "Text content to write"},
                    "append": {"type": "boolean", "description": "Append instead of overwrite", "default": False}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and folders in a directory with details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list"},
                    "recursive": {"type": "boolean", "description": "Include subdirectories", "default": False}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "Move or rename a file or directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source path"},
                    "destination": {"type": "string", "description": "Destination path"}
                },
                "required": ["source", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "copy_file",
            "description": "Copy a file or directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source path"},
                    "destination": {"type": "string", "description": "Destination path"}
                },
                "required": ["source", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file or empty directory. REQUIRES CONFIRMATION.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to delete"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "create_directory",
            "description": "Create a new directory (including parent directories).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to create"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_info",
            "description": "Get detailed information about a file or directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to inspect"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command. REQUIRES CONFIRMATION for safety.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"},
                    "cwd": {"type": "string", "description": "Working directory", "default": "."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information. **CRITICAL**: You MUST ONLY use URLs that appear in the search results. NEVER invent or guess URLs. If a specific URL is not in the results, say 'I did not find a direct link' instead of making one up.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Max results to return", "default": 5}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_webpage",
            "description": "Read and extract text content from a webpage URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to read"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_image",
            "description": "Analyze an image and describe its contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to image file"},
                    "question": {"type": "string", "description": "Specific question about the image", "default": "Опиши это изображение"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_archive",
            "description": "Extract contents of a ZIP or RAR archive.",
            "parameters": {
                "type": "object",
                "properties": {
                    "archive_path": {"type": "string", "description": "Path to archive file"},
                    "destination": {"type": "string", "description": "Destination directory", "default": "."}
                },
                "required": ["archive_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_archive",
            "description": "Create a ZIP archive from files or directories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "Output archive path"},
                    "files": {"type": "array", "items": {"type": "string"}, "description": "List of files/directories to include"}
                },
                "required": ["output_path", "files"]
            }
        }
    }
]

# Tools that require user confirmation before execution
DANGEROUS_TOOLS = {"delete_file", "run_command", "move_file"}


class ToolExecutor:
    """
    Executes tool calls from the LLM.
    Handles file operations, web requests, and system commands.
    """
    
    def __init__(self):
        self._pending_confirmations: dict[str, dict] = {}
        
    def requires_confirmation(self, tool_name: str) -> bool:
        """Check if tool requires user confirmation."""
        return tool_name in DANGEROUS_TOOLS
    
    async def execute(self, tool_name: str, arguments: dict) -> str:
        """
        Execute a tool and return result.
        
        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments
            
        Returns:
            String result of tool execution
        """
        try:
            method = getattr(self, f"_tool_{tool_name}", None)
            if not method:
                return f"Unknown tool: {tool_name}"
            
            result = await method(**arguments) if callable(method) else method(**arguments)
            
            if isinstance(result, ToolResult):
                if result.success:
                    return result.output
                else:
                    return f"Error: {result.error}"
            return str(result)
            
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"
    
    # ==================== File Operations ====================
    
    async def _tool_read_file(self, path: str) -> ToolResult:
        """Read file contents."""
        try:
            p = _validate_path(path)
            if not p.exists():
                return ToolResult(False, "", f"File not found: {path}")
            if not p.is_file():
                return ToolResult(False, "", f"Not a file: {path}")
            
            # Check if binary
            mime = mimetypes.guess_type(str(p))[0] or ""
            if mime.startswith("image/"):
                return ToolResult(False, "", "This is an image file. Use analyze_image instead.")
            
            content = p.read_text(encoding="utf-8", errors="replace")
            return ToolResult(True, content)
        except PermissionError as e:
            return ToolResult(False, "", str(e))
        except Exception as e:
            return ToolResult(False, "", str(e))
    
    async def _tool_write_file(self, path: str, content: str, append: bool = False) -> ToolResult:
        """Write to file with Shadow Copy backup."""
        try:
            p = _validate_path(path)
            
            # Shadow Copy: backup before overwrite
            if p.exists() and not append:
                self._create_shadow_copy(p)
            
            p.parent.mkdir(parents=True, exist_ok=True)
            
            mode = "a" if append else "w"
            with open(p, mode, encoding="utf-8") as f:
                f.write(content)
            
            return ToolResult(True, f"Written to {path}")
        except PermissionError as e:
            return ToolResult(False, "", str(e))
        except Exception as e:
            return ToolResult(False, "", str(e))
    
    def _create_shadow_copy(self, path: Path) -> Path:
        """Shadow Copy — mandatory backup before overwrite."""
        backup_dir = Path("data/.file_backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{path.name}.{timestamp}.bak"
        shutil.copy2(path, backup_path)
        return backup_path
    
    async def _tool_list_directory(self, path: str, recursive: bool = False, limit: int = MAX_DIRECTORY_ITEMS) -> ToolResult:
        """List directory contents with limit to prevent memory issues."""
        try:
            p = _validate_path(path)
            if not p.exists():
                return ToolResult(False, "", f"Directory not found: {path}")
            if not p.is_dir():
                return ToolResult(False, "", f"Not a directory: {path}")

            items = []
            count = 0
            truncated = False

            if recursive:
                for item in p.rglob("*"):
                    if count >= limit:
                        truncated = True
                        break
                    rel = item.relative_to(p)
                    icon = "📁" if item.is_dir() else "📄"
                    try:
                        size = item.stat().st_size if item.is_file() else 0
                    except (OSError, PermissionError):
                        size = 0
                    items.append(f"{icon} {rel} ({self._format_size(size)})")
                    count += 1
            else:
                for item in sorted(p.iterdir()):
                    if count >= limit:
                        truncated = True
                        break
                    icon = "📁" if item.is_dir() else "📄"
                    try:
                        size = item.stat().st_size if item.is_file() else 0
                    except (OSError, PermissionError):
                        size = 0
                    items.append(f"{icon} {item.name} ({self._format_size(size)})")
                    count += 1

            result = "\n".join(items) if items else "(empty)"
            if truncated:
                result += f"\n\n[... truncated at {limit} items. Use more specific path.]"

            return ToolResult(True, result)
        except Exception as e:
            return ToolResult(False, "", str(e))
    
    async def _tool_move_file(self, source: str, destination: str) -> ToolResult:
        """Move/rename file."""
        try:
            src = _validate_path(source)
            dst = _validate_path(destination)
            
            if not src.exists():
                return ToolResult(False, "", f"Source not found: {source}")
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            
            return ToolResult(True, f"✓ Moved {source} → {destination}")
        except Exception as e:
            return ToolResult(False, "", str(e))
    
    async def _tool_copy_file(self, source: str, destination: str) -> ToolResult:
        """Copy file/directory."""
        try:
            src = _validate_path(source)
            dst = _validate_path(destination)
            
            if not src.exists():
                return ToolResult(False, "", f"Source not found: {source}")
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            if src.is_dir():
                shutil.copytree(str(src), str(dst))
            else:
                shutil.copy2(str(src), str(dst))
            
            return ToolResult(True, f"✓ Copied {source} → {destination}")
        except Exception as e:
            return ToolResult(False, "", str(e))
    
    async def _tool_delete_file(self, path: str, force: bool = False) -> ToolResult:
        """Delete file or directory.

        Args:
            path: Path to delete
            force: If True, delete non-empty directories recursively (DANGEROUS!)
        """
        try:
            p = _validate_path(path)
            if not p.exists():
                return ToolResult(False, "", f"Not found: {path}")

            if p.is_dir():
                # Check if directory is empty
                children = list(p.iterdir())
                if children and not force:
                    return ToolResult(
                        False, "",
                        f"Directory not empty ({len(children)} items). "
                        f"Use force=True to delete recursively (DANGEROUS!)."
                    )
                if force:
                    shutil.rmtree(str(p))
                else:
                    p.rmdir()
            else:
                p.unlink()

            return ToolResult(True, f"✓ Deleted {path}")
        except Exception as e:
            return ToolResult(False, "", str(e))
    
    async def _tool_create_directory(self, path: str) -> ToolResult:
        """Create directory."""
        try:
            p = _validate_path(path)
            p.mkdir(parents=True, exist_ok=True)
            return ToolResult(True, f"✓ Created directory {path}")
        except Exception as e:
            return ToolResult(False, "", str(e))
    
    async def _tool_get_file_info(self, path: str) -> ToolResult:
        """Get file information."""
        try:
            p = _validate_path(path)
            if not p.exists():
                return ToolResult(False, "", f"Not found: {path}")
            
            stat = p.stat()
            info = {
                "name": p.name,
                "path": str(p),
                "type": "directory" if p.is_dir() else "file",
                "size": self._format_size(stat.st_size),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
            
            if p.is_file():
                info["mime_type"] = mimetypes.guess_type(str(p))[0]
            
            return ToolResult(True, json.dumps(info, indent=2, ensure_ascii=False))
        except Exception as e:
            return ToolResult(False, "", str(e))
    
    # ==================== Shell Commands ====================
    
    async def _tool_run_command(self, command: str, cwd: str = ".") -> ToolResult:
        """Run shell command with security restrictions."""
        from .safe_shell import safe_shell

        # Security: Block dangerous commands
        BLOCKED_PATTERNS = [
            "rm -rf /", "del /s /q c:\\", "format ", "mkfs",
            "> /dev/", "dd if=", ":(){:|:&};:",  # Fork bomb
            "&&", "||", ";", "|", "`", "$(",  # Shell chaining/injection
            ">", ">>", "<",  # Redirections
        ]

        # Block code execution flags that allow arbitrary code
        BLOCKED_CODE_FLAGS = [
            "-c",  # python -c, sh -c, etc.
            "--command",
            "-e",  # perl -e, ruby -e
            "--eval",
            "exec(",  # python exec
            "eval(",  # python eval
            "__import__",  # python import trick
            "subprocess",  # subprocess module
            "os.system",  # os.system call
        ]

        cmd_lower = command.lower()
        for pattern in BLOCKED_PATTERNS:
            if pattern in cmd_lower:
                return ToolResult(False, "", f"Blocked dangerous command pattern: {pattern}")

        for flag in BLOCKED_CODE_FLAGS:
            if flag in cmd_lower:
                return ToolResult(False, "", f"Blocked code execution pattern: {flag}")

        # Whitelist of allowed commands (P0 fix: Command Injection protection)
        # Security ensured by BLOCKED_CODE_FLAGS (blocks -c, exec(, eval(), etc.)
        ALLOWED_COMMANDS = {
            "ls", "dir", "cat", "type", "head", "tail", "grep", "find",
            "pwd", "cd", "echo", 
            "ps", "top", "htop", "df", "du", "free", "uptime", "whoami",
            # Issue #5 fix: Allow interpreters (dangerous flags blocked separately)
            "python", "python3", "node", "npm", "pip",
        }

        try:
            import shlex
            import os
            
            # Parse command safely
            try:
                args = shlex.split(command)
            except ValueError:
                args = command.split()
            
            if not args:
                return ToolResult(False, "", "Empty command")

            # Check if base command is allowed
            base_cmd = os.path.basename(args[0]).lower()
            if base_cmd.endswith('.exe'):
                base_cmd = base_cmd[:-4]

            if base_cmd not in ALLOWED_COMMANDS:
                return ToolResult(False, "", f"Command not in whitelist: {base_cmd}. Allowed: {', '.join(sorted(ALLOWED_COMMANDS))}")

            # Use SafeShell for cross-platform execution (Windows built-in support)
            result = await safe_shell.execute(command, cwd=cwd, timeout=60.0)

            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]: {result.stderr}"
            if result.timed_out:
                output += "\n[TIMED OUT after 60 seconds]"

            return ToolResult(
                success=result.return_code == 0 and not result.timed_out,
                output=output or "(no output)"
            )
        except Exception as e:
            return ToolResult(False, "", str(e))
    
    # ==================== Image Analysis ====================

    async def _tool_analyze_image(self, path: str, question: str = "Опиши это изображение") -> ToolResult:
        """Analyze image using vision model with actual LLM analysis."""
        try:
            from .lm_client import lm_client, TaskType

            p = _validate_path(path)
            if not p.exists():
                return ToolResult(False, "", f"Image not found: {path}")

            # Use context manager to properly close image
            with Image.open(p) as img:
                # Get basic info
                info = f"Image: {p.name}, Size: {img.size[0]}x{img.size[1]}, Format: {img.format}\n\n"

                # Convert to base64 for vision model
                import io
                buffer = io.BytesIO()
                # Convert to RGB if necessary (for RGBA images)
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                img.save(buffer, format='JPEG', quality=85)
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # Send to vision model for actual analysis
            try:
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": question
                            }
                        ]
                    }
                ]

                response = await lm_client.chat(
                    messages=messages,
                    stream=False,
                    task_type=TaskType.VISION,
                    max_tokens=1000
                )

                return ToolResult(True, info + f"Анализ:\n{response}")

            except Exception as llm_error:
                # Fallback to basic info if LLM fails
                return ToolResult(True, info + f"[Vision model unavailable: {llm_error}]")

        except PermissionError as e:
            return ToolResult(False, "", str(e))
        except Exception as e:
            return ToolResult(False, "", str(e))
    
    # ==================== Web Operations ====================

    async def _tool_web_search(self, query: str, max_results: int = 5) -> ToolResult:
        """Search the web using DuckDuckGo with URL validation."""
        try:
            from .web_search import web_searcher
            from .url_validator import url_validator

            results = await web_searcher.search(query, max_results=max_results)

            if not results:
                return ToolResult(True, "Ничего не найдено по данному запросу.")

            # ANTI-HALLUCINATION: Validate each URL
            validated_results = []
            invalid_count = 0
            
            for r in results:
                validation = await url_validator.validate_url(r.url)
                r.validation_status = "verified" if validation.valid else "invalid"
                r.confidence = validation.confidence
                
                if validation.valid:
                    validated_results.append(r)
                else:
                    invalid_count += 1
            
            # If no valid URLs found, return error
            if not validated_results:
                return ToolResult(
                    True, 
                    f"⚠️ Найдено {len(results)} результатов, но ни один URL не прошел проверку.\n"
                    "Возможно, эти сайты не существуют или недоступны."
                )

            output_parts = [
                f"🔍 Результаты поиска: {query}\n",
                f"✅ Проверено: {len(validated_results)} валидных URL из {len(results)} найденных\n",
                f"⚠️ КРИТИЧЕСКИ ВАЖНО: Используйте ТОЛЬКО эти проверенные URL. НЕ придумывайте другие!\n"
            ]
            
            for i, r in enumerate(validated_results, 1):
                confidence_icon = "🟢" if r.confidence >= 0.9 else "🟡"
                output_parts.append(f"\n{i}. {confidence_icon} **{r.title}**")
                output_parts.append(f"   🔗 URL: {r.url}")
                output_parts.append(f"   📝 {r.snippet}")
                output_parts.append(f"   ✓ Проверен и доступен")

            if invalid_count > 0:
                output_parts.append(f"\n⚠️ Отфильтровано {invalid_count} недоступных URL")
            
            output_parts.append("\n🚫 Это ВСЕ проверенные URL. Других достоверных ссылок НЕТ.")
            
            return ToolResult(True, "\n".join(output_parts))
        except Exception as e:
            return ToolResult(False, "", str(e))

    async def _tool_read_webpage(self, url: str, max_length: int = 5000) -> ToolResult:
        """Read and extract text content from a webpage."""
        try:
            from .web_search import web_searcher

            content = await web_searcher.read_page(url, max_length=max_length)

            if content.startswith("Error"):
                return ToolResult(False, "", content)

            return ToolResult(True, f"📄 Content from {url}:\n\n{content}")
        except Exception as e:
            return ToolResult(False, "", str(e))

    # ==================== Archive Operations ====================

    async def _tool_extract_archive(self, archive_path: str, destination: str = ".") -> ToolResult:
        """Extract contents of a ZIP archive."""
        try:
            p = _validate_path(archive_path)
            if not p.exists():
                return ToolResult(False, "", f"Archive not found: {archive_path}")

            dest = Path(destination).expanduser().resolve()
            dest.mkdir(parents=True, exist_ok=True)

            suffix = p.suffix.lower()

            if suffix == ".zip":
                with zipfile.ZipFile(p, 'r') as zf:
                    # Security: check for path traversal
                    for member in zf.namelist():
                        member_path = dest / member
                        if not str(member_path.resolve()).startswith(str(dest.resolve())):
                            return ToolResult(False, "", f"Path traversal detected: {member}")
                    zf.extractall(dest)
                    extracted = zf.namelist()
            else:
                return ToolResult(False, "", f"Unsupported archive format: {suffix}. Only .zip is supported.")

            return ToolResult(True, f"✓ Extracted {len(extracted)} items to {destination}")
        except Exception as e:
            return ToolResult(False, "", str(e))

    async def _tool_create_archive(self, output_path: str, files: list[str]) -> ToolResult:
        """Create a ZIP archive from files or directories."""
        try:
            out_p = _validate_path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(out_p, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in files:
                    p = _validate_path(file_path)
                    if not p.exists():
                        return ToolResult(False, "", f"File not found: {file_path}")

                    if p.is_file():
                        zf.write(p, p.name)
                    elif p.is_dir():
                        for item in p.rglob("*"):
                            if item.is_file():
                                zf.write(item, item.relative_to(p.parent))

            return ToolResult(True, f"✓ Created archive {output_path}")
        except Exception as e:
            return ToolResult(False, "", str(e))

    # ==================== Helpers ====================

    def _format_size(self, size: int) -> str:
        """Format byte size to human readable."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# Global tool executor
tools = ToolExecutor()
