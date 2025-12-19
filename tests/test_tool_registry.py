"""
Unit tests for Tool Registry module.

Tests:
- Tool registration via decorator
- JSON schema generation
- Tool execution
- Category filtering
"""
import pytest


class TestToolRegistry:
    """Tests for ToolRegistry class."""
    
    def test_registry_exists(self):
        """Test that registry singleton exists."""
        from src.core.tool_registry import registry
        
        assert registry is not None
    
    def test_has_register_method(self):
        """Test that registry has register method."""
        from src.core.tool_registry import registry
        
        assert hasattr(registry, 'register')
        assert callable(registry.register)
    
    def test_has_execute_method(self):
        """Test that registry has execute method."""
        from src.core.tool_registry import registry
        
        assert hasattr(registry, 'execute')
    
    def test_has_get_tools_schema_method(self):
        """Test that registry has get_tools_schema method."""
        from src.core.tool_registry import registry
        
        assert hasattr(registry, 'get_tools_schema')
    
    def test_register_decorator(self):
        """Test registering a tool via decorator."""
        from src.core.tool_registry import registry
        
        @registry.register(
            description="Test tool",
            category="test"
        )
        async def test_tool(x: int) -> int:
            return x * 2
        
        # Tool should be registered
        tools = registry.get_tools_schema()
        # Schema format: {"type": "function", "function": {"name": ...}}
        tool_names = [t['function']['name'] for t in tools]
        assert 'test_tool' in tool_names
    
    def test_schema_has_parameters(self):
        """Test that schema includes parameter definitions."""
        from src.core.tool_registry import registry
        
        @registry.register(
            description="Add two numbers",
            category="math"
        )
        async def add_numbers(a: int, b: int) -> int:
            return a + b
        
        tools = registry.get_tools_schema()
        add_tool = next((t for t in tools if t['function']['name'] == 'add_numbers'), None)
        
        assert add_tool is not None
        assert 'parameters' in add_tool['function']
    
    def test_filter_by_category(self):
        """Test filtering tools by category."""
        from src.core.tool_registry import registry
        
        @registry.register(description="Cat A", category="category_a")
        async def tool_a():
            pass
        
        @registry.register(description="Cat B", category="category_b")
        async def tool_b():
            pass
        
        filtered = registry.get_tools_schema(filter_tags=["category_a"])
        names = [t['function']['name'] for t in filtered]
        
        assert 'tool_a' in names


class TestToolDefinition:
    """Tests for ToolDefinition dataclass."""
    
    def test_tool_definition_fields(self):
        """Test ToolDefinition has required fields."""
        from src.core.tool_registry.registry import ToolDefinition
        
        assert hasattr(ToolDefinition, '__dataclass_fields__')
        fields = ToolDefinition.__dataclass_fields__
        
        assert 'name' in fields
        assert 'description' in fields
        assert 'function' in fields  # Not 'func'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
