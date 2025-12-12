"""
Tests for MemoryManager module.

ALIGNED WITH REAL API: MemoryManager class.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMemoryManagerStructure:
    """Tests for MemoryManager class structure."""
    
    def test_imports_and_classes_exist(self):
        """Test that all expected classes can be imported."""
        from src.core.memory import (
            MemoryManager,
            Message,
            Fact,
            Conversation
        )
        
        assert MemoryManager is not None
        assert Message is not None
        assert Fact is not None
        assert Conversation is not None
        
    def test_message_dataclass(self):
        """Test Message dataclass fields."""
        from src.core.memory import Message
        
        msg = Message(
            conversation_id="test-conv",
            role="user",
            content="Hello"
        )
        
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.conversation_id == "test-conv"
        
    def test_fact_dataclass(self):
        """Test Fact dataclass fields."""
        from src.core.memory import Fact
        
        fact = Fact(
            content="User likes Python",
            category="preference",
            confidence=0.9
        )
        
        assert fact.content == "User likes Python"
        assert fact.category == "preference"
        assert fact.confidence == 0.9
        
    def test_conversation_dataclass(self):
        """Test Conversation dataclass fields."""
        from src.core.memory import Conversation
        
        conv = Conversation(title="Test Chat")
        
        assert conv.title == "Test Chat"
        # Should have auto-generated ID
        assert conv.id is not None


class TestMemoryManagerMethods:
    """Tests for MemoryManager method signatures."""
    
    def test_memory_manager_has_methods(self):
        """Test that MemoryManager has expected methods."""
        from src.core.memory import MemoryManager
        
        # Check method existence
        assert hasattr(MemoryManager, 'initialize')
        assert hasattr(MemoryManager, 'close')
        assert hasattr(MemoryManager, 'create_conversation')
        assert hasattr(MemoryManager, 'get_conversation')
        assert hasattr(MemoryManager, 'list_conversations')
        assert hasattr(MemoryManager, 'delete_conversation')
        assert hasattr(MemoryManager, 'add_message')
        assert hasattr(MemoryManager, 'get_messages')
        assert hasattr(MemoryManager, 'get_smart_context')
        assert hasattr(MemoryManager, 'add_fact')
        assert hasattr(MemoryManager, 'get_relevant_facts')
        
    def test_memory_manager_instantiation(self):
        """Test MemoryManager can be instantiated."""
        from src.core.memory import MemoryManager
        
        # Should be able to create with optional path
        manager = MemoryManager()
        assert manager is not None
        
    def test_count_tokens_method(self):
        """Test count_tokens method exists and works."""
        from src.core.memory import MemoryManager
        
        manager = MemoryManager()
        
        # Method should exist
        assert hasattr(manager, 'count_tokens')
        
        # Should return integer
        count = manager.count_tokens("Hello world")
        assert isinstance(count, int)
        assert count > 0
