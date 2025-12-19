"""
Tool Registry — The Swiss Army Knife.

Decorator-based tool registration with automatic JSON Schema generation
from Python type hints. No manual schema writing required.

Usage:
    from src.core.tools import registry
    
    @registry.register(category="files", requires_confirmation=False)
    async def read_file(path: str) -> str:
        '''Read contents of a file.'''
        ...
    
    # Get all schemas for LLM
    schemas = registry.get_tools_schema()
    
    # Filter by category (future RAG support)
    file_schemas = registry.get_tools_schema(filter_tags=["files"])
"""
import inspect
from dataclasses import dataclass, field
from typing import Callable, Optional, Any, get_type_hints, Union
from functools import wraps


# Type mapping: Python types -> JSON Schema types
TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    type(None): "null",
}


@dataclass
class ToolDefinition:
    """Registered tool metadata and function reference."""
    name: str
    description: str
    parameters: dict  # JSON Schema
    function: Callable
    requires_confirmation: bool = False
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    
    def to_schema(self) -> dict:
        """Convert to OpenAI-compatible tool schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class ToolRegistry:
    """
    Central registry for all tools with auto-schema generation.
    
    Features:
    - Decorator-based registration
    - Automatic JSON Schema from type hints
    - Category-based filtering (for future RAG)
    - Confirmation flag for dangerous operations
    """
    
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
    
    def register(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: str = "general",
        tags: Optional[list[str]] = None,
        requires_confirmation: bool = False
    ) -> Callable:
        """
        Decorator to register a tool function.
        
        Args:
            name: Tool name (defaults to function name)
            description: Tool description (defaults to docstring)
            category: Category for filtering (e.g., "files", "web", "system")
            tags: Additional tags for RAG-based selection
            requires_confirmation: If True, requires user confirmation before execution
        
        Example:
            @registry.register(category="files")
            async def read_file(path: str) -> str:
                '''Read file contents.'''
                ...
        """
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            tool_description = description or func.__doc__ or f"Execute {tool_name}"
            
            # Generate JSON Schema from function signature
            schema = self._generate_schema(func)
            
            # Register the tool
            self._tools[tool_name] = ToolDefinition(
                name=tool_name,
                description=tool_description.strip(),
                parameters=schema,
                function=func,
                requires_confirmation=requires_confirmation,
                category=category,
                tags=tags or []
            )
            
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            
            return wrapper
        
        return decorator
    
    def _generate_schema(self, func: Callable) -> dict:
        """
        Generate JSON Schema from function signature and type hints.
        
        Inspects:
        - Type hints for parameter types
        - Default values for optional parameters
        - Docstring for parameter descriptions (TODO)
        """
        sig = inspect.signature(func)
        
        try:
            hints = get_type_hints(func)
        except Exception:
            hints = {}
        
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            # Skip self, cls, *args, **kwargs
            if param_name in ("self", "cls") or param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD
            ):
                continue
            
            # Get type from hints
            param_type = hints.get(param_name, Any)
            json_type = self._python_type_to_json(param_type)
            
            properties[param_name] = {
                "type": json_type,
                "description": f"Parameter: {param_name}"  # TODO: Extract from docstring
            }
            
            # Check if required (no default value)
            if param.default is inspect.Parameter.empty:
                required.append(param_name)
            else:
                properties[param_name]["default"] = param.default
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def _python_type_to_json(self, python_type: type) -> str:
        """Convert Python type to JSON Schema type string."""
        # Handle Optional[X], Union[X, None]
        origin = getattr(python_type, "__origin__", None)
        if origin is Union:
            args = getattr(python_type, "__args__", ())
            # Filter out NoneType
            non_none = [a for a in args if a is not type(None)]
            if non_none:
                return self._python_type_to_json(non_none[0])
        
        # Handle List[X]
        if origin is list:
            return "array"
        
        # Handle Dict[X, Y]
        if origin is dict:
            return "object"
        
        # Direct type mapping
        return TYPE_MAP.get(python_type, "string")
    
    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_tools_schema(
        self,
        filter_tags: Optional[list[str]] = None,
        limit: Optional[int] = None
    ) -> list[dict]:
        """
        Get tool schemas for LLM with optional filtering.
        
        Args:
            filter_tags: Only include tools with these categories/tags
            limit: Maximum number of tools to return
        
        Returns:
            List of OpenAI-compatible tool schemas
        
        # TODO: Implement RAG for tool selection
        # In future: semantic search on user query -> select relevant tools
        """
        tools = list(self._tools.values())
        
        if filter_tags:
            tools = [
                t for t in tools 
                if t.category in filter_tags or any(tag in filter_tags for tag in t.tags)
            ]
        
        if limit:
            tools = tools[:limit]
        
        return [t.to_schema() for t in tools]
    
    def get_all_tools(self) -> dict[str, ToolDefinition]:
        """Get all registered tools."""
        return self._tools.copy()
    
    def requires_confirmation(self, tool_name: str) -> bool:
        """Check if a tool requires user confirmation."""
        tool = self._tools.get(tool_name)
        return tool.requires_confirmation if tool else False
    
    async def execute(self, tool_name: str, arguments: dict) -> Any:
        """Execute a registered tool by name."""
        tool = self._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return await tool.function(**arguments)


# Global singleton instance
registry = ToolRegistry()
