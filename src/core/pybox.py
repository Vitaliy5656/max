"""
PyBox - Secure Python Sandbox for MAX AI Assistant.

Allows safe execution of Python code for calculations and data analysis.
Uses AST analysis to block dangerous operations.

Security features:
- AST-level blocking of imports (os, sys, subprocess, etc.)
- Blocked function calls (exec, eval, open, etc.)
- Timeout protection
- Output size limit
- No file/network access

Usage:
    from .pybox import pybox
    
    result = await pybox.execute("2 + 2 * 3")
    # PyBoxResult(success=True, output="8", error=None)
"""
import ast
import asyncio
import io
import sys
from dataclasses import dataclass
from typing import Optional, Set
from contextlib import redirect_stdout, redirect_stderr


# Security: Blocked imports
BLOCKED_IMPORTS = {
    "os", "sys", "subprocess", "socket", "shutil", "pathlib",
    "requests", "urllib", "http", "ftplib", "smtplib",
    "multiprocessing", "threading", "concurrent",
    "pickle", "marshal", "shelve",
    "ctypes", "cffi", "importlib",
    "builtins", "__builtins__",
    "code", "codeop", "compile",
}

# Security: Blocked function calls
BLOCKED_CALLS = {
    "exec", "eval", "compile", "open",
    "__import__", "getattr", "setattr", "delattr",
    "globals", "locals", "vars", "dir",
    "input", "breakpoint",
}

# Allowed safe imports for calculations
ALLOWED_IMPORTS = {
    "math", "json", "re", "datetime", "time",
    "random", "statistics", "decimal", "fractions",
    "collections", "itertools", "functools",
    "string", "textwrap",
}

# Optional: Allowed if numpy/pandas installed
OPTIONAL_IMPORTS = {"numpy", "pandas"}


@dataclass
class PyBoxResult:
    """Result of Python code execution."""
    success: bool
    output: str
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class ASTSecurityChecker(ast.NodeVisitor):
    """
    AST visitor that checks for dangerous operations.
    
    Raises SecurityError if dangerous code is detected.
    """
    
    def __init__(self):
        self.errors: list[str] = []
    
    def visit_Import(self, node):
        """Check Import statements."""
        for alias in node.names:
            module = alias.name.split(".")[0]
            if module in BLOCKED_IMPORTS:
                self.errors.append(f"Import blocked: {module}")
            elif module not in ALLOWED_IMPORTS and module not in OPTIONAL_IMPORTS:
                self.errors.append(f"Import not allowed: {module}")
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Check 'from X import Y' statements."""
        if node.module:
            module = node.module.split(".")[0]
            if module in BLOCKED_IMPORTS:
                self.errors.append(f"Import blocked: {module}")
            elif module not in ALLOWED_IMPORTS and module not in OPTIONAL_IMPORTS:
                self.errors.append(f"Import not allowed: {module}")
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Check function calls."""
        if isinstance(node.func, ast.Name):
            if node.func.id in BLOCKED_CALLS:
                self.errors.append(f"Function blocked: {node.func.id}()")
        elif isinstance(node.func, ast.Attribute):
            # Check for things like os.system()
            if node.func.attr in {"system", "popen", "spawn", "fork", "exec"}:
                self.errors.append(f"Method blocked: .{node.func.attr}()")
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """Check attribute access."""
        # Block dunder attributes
        if node.attr.startswith("__") and node.attr.endswith("__"):
            if node.attr not in {"__init__", "__str__", "__repr__", "__len__", "__getitem__"}:
                self.errors.append(f"Access blocked: {node.attr}")
        self.generic_visit(node)


class PyBox:
    """
    Secure Python execution sandbox.
    
    Executes Python code with safety restrictions:
    - AST analysis blocks dangerous code before execution
    - Timeout prevents infinite loops
    - Output is captured and limited
    - No access to filesystem or network
    """
    
    MAX_OUTPUT_SIZE = 10000  # 10KB max output
    DEFAULT_TIMEOUT = 10.0   # 10 seconds
    
    def __init__(self):
        self._safe_globals = self._build_safe_globals()
    
    def _build_safe_globals(self) -> dict:
        """Build safe globals for execution."""
        safe = {
            "__builtins__": {
                # Safe builtins only
                "abs": abs, "all": all, "any": any, "bool": bool,
                "dict": dict, "enumerate": enumerate, "filter": filter,
                "float": float, "format": format, "frozenset": frozenset,
                "int": int, "len": len, "list": list, "map": map,
                "max": max, "min": min, "pow": pow, "range": range,
                "reversed": reversed, "round": round, "set": set,
                "slice": slice, "sorted": sorted, "str": str,
                "sum": sum, "tuple": tuple, "type": type, "zip": zip,
                "True": True, "False": False, "None": None,
                "print": print,  # Will be captured
            }
        }
        
        # Add allowed modules
        import math
        import json
        import re
        import datetime
        import random
        import statistics
        from decimal import Decimal
        from fractions import Fraction
        from collections import Counter, defaultdict, OrderedDict
        from itertools import chain, combinations, permutations
        
        safe["math"] = math
        safe["json"] = json
        safe["re"] = re
        safe["datetime"] = datetime
        safe["random"] = random
        safe["statistics"] = statistics
        safe["Decimal"] = Decimal
        safe["Fraction"] = Fraction
        safe["Counter"] = Counter
        safe["defaultdict"] = defaultdict
        safe["OrderedDict"] = OrderedDict
        safe["chain"] = chain
        safe["combinations"] = combinations
        safe["permutations"] = permutations
        
        # Try to add numpy/pandas if available
        try:
            import numpy as np
            safe["np"] = np
            safe["numpy"] = np
        except ImportError:
            pass
        
        try:
            import pandas as pd
            safe["pd"] = pd
            safe["pandas"] = pd
        except ImportError:
            pass
        
        return safe
    
    def check_security(self, code: str) -> list[str]:
        """
        Check code for security issues using AST analysis.
        
        Args:
            code: Python source code
            
        Returns:
            List of security error messages (empty if safe)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [f"Syntax error: {e}"]
        
        checker = ASTSecurityChecker()
        checker.visit(tree)
        
        return checker.errors
    
    async def execute(
        self,
        code: str,
        timeout: float = DEFAULT_TIMEOUT
    ) -> PyBoxResult:
        """
        Execute Python code safely.
        
        Args:
            code: Python source code to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            PyBoxResult with output or error
        """
        import time
        start_time = time.time()
        
        # Security check first
        security_errors = self.check_security(code)
        if security_errors:
            return PyBoxResult(
                success=False,
                output="",
                error="Security violation: " + "; ".join(security_errors),
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        # Execute in separate thread with timeout
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    self._execute_code,
                    code
                ),
                timeout=timeout
            )
            
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result
            
        except asyncio.TimeoutError:
            return PyBoxResult(
                success=False,
                output="",
                error=f"Execution timed out after {timeout} seconds",
                execution_time_ms=timeout * 1000
            )
        except Exception as e:
            return PyBoxResult(
                success=False,
                output="",
                error=f"Execution error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def _execute_code(self, code: str) -> PyBoxResult:
        """Execute code and capture output."""
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Create fresh locals for each execution
                local_vars = {}
                
                # Compile and execute
                compiled = compile(code, "<pybox>", "exec")
                exec(compiled, self._safe_globals.copy(), local_vars)
                
                # If last expression is a value, capture it
                try:
                    expr_code = compile(code, "<pybox>", "eval")
                    result = eval(expr_code, self._safe_globals.copy(), local_vars)
                    if result is not None and not stdout_capture.getvalue():
                        print(repr(result))
                except:
                    pass
            
            output = stdout_capture.getvalue()
            stderr = stderr_capture.getvalue()
            
            # Combine and truncate output
            combined = output
            if stderr:
                combined += f"\n[stderr]: {stderr}"
            
            if len(combined) > self.MAX_OUTPUT_SIZE:
                combined = combined[:self.MAX_OUTPUT_SIZE] + "\n[... truncated ...]"
            
            return PyBoxResult(
                success=True,
                output=combined or "(no output)",
                error=None
            )
            
        except Exception as e:
            return PyBoxResult(
                success=False,
                output=stdout_capture.getvalue(),
                error=str(e)
            )


# Global instance
pybox = PyBox()
