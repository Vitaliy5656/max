# Tool Registry Module

Decorator-based tool registration with automatic JSON schema generation.

## Features

- **@registry.register()**: Decorator for easy tool registration
- **Auto JSON Schema**: Generates schema from Python type hints
- **Category Filtering**: `filter_tags` for selective tool loading
- **Confirmation Support**: `requires_confirmation` flag for dangerous ops

## Usage

```python
from src.core.tool_registry import registry

# Register a tool
@registry.register(
    description="Read a file from disk",
    category="file",
    requires_confirmation=False
)
def read_file(path: str, encoding: str = "utf-8") -> str:
    with open(path, encoding=encoding) as f:
        return f.read()

# Get all tool schemas
schemas = registry.get_tools_schema()

# Filter by category
file_tools = registry.get_tools_schema(filter_tags=["file"])

# Execute tool
result = await registry.execute("read_file", {"path": "test.txt"})
```

## Files

| File | Description |
|------|-------------|
| `registry.py` | ToolRegistry singleton + ToolDefinition |
| `__init__.py` | Package exports |

## Integration

Tools registered here can be used by the LLM via function calling.
The auto-generated JSON schema is passed to the model.
