"""
Tests for Research Lab - Storage and Parser modules.
"""

import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.research.storage import ResearchStorage, TopicInfo
from src.core.research.parser import DualParser, ParseResult, MIN_CONTENT_LENGTH


class TestResearchStorage:
    """Tests for ResearchStorage class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp, ignore_errors=True)
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        service = AsyncMock()
        service.get_or_compute = AsyncMock(return_value=[0.1, 0.2, 0.3] * 256)  # 768-dim
        return service
    
    @pytest.fixture
    async def storage(self, temp_dir, mock_embedding_service):
        """Create initialized storage."""
        storage = ResearchStorage(persist_dir=temp_dir)
        storage._skills_file = Path(temp_dir) / "skills.json"
        await storage.initialize(mock_embedding_service)
        return storage
    
    @pytest.mark.asyncio
    async def test_initialize(self, temp_dir, mock_embedding_service):
        """Test storage initialization."""
        storage = ResearchStorage(persist_dir=temp_dir)
        storage._skills_file = Path(temp_dir) / "skills.json"
        await storage.initialize(mock_embedding_service)
        
        assert storage._initialized is True
        assert storage._client is not None
        assert storage._skills_file.exists()
    
    @pytest.mark.asyncio
    async def test_create_topic(self, storage):
        """Test creating a topic."""
        topic_id = await storage.create_topic("Test Topic", "Test description")
        
        assert topic_id is not None
        assert len(topic_id) == 36  # UUID format
        
        # Verify topic was saved
        topics = await storage.list_topics()
        assert len(topics) == 1
        assert topics[0].name == "Test Topic"
        assert topics[0].status == "incomplete"
    
    @pytest.mark.asyncio
    async def test_create_topic_with_status(self, storage):
        """Test creating topic with specific status."""
        topic_id = await storage.create_topic("Test", "Desc", status="complete")
        
        topic = await storage.get_topic(topic_id)
        assert topic.status == "complete"
    
    @pytest.mark.asyncio
    async def test_update_topic_status(self, storage):
        """Test updating topic status."""
        topic_id = await storage.create_topic("Test", "Desc")
        
        await storage.update_topic_status(topic_id, "complete")
        
        topic = await storage.get_topic(topic_id)
        assert topic.status == "complete"
    
    @pytest.mark.asyncio
    async def test_add_and_search_chunk(self, storage):
        """Test adding chunk and searching."""
        topic_id = await storage.create_topic("Python", "Python programming")
        
        await storage.add_chunk(topic_id, "Python is a programming language", {
            "source": "test",
            "type": "knowledge"
        })
        
        results = await storage.search(topic_id, "programming language")
        
        assert len(results) >= 1
        assert "Python" in results[0]["content"]
    
    @pytest.mark.asyncio
    async def test_save_and_get_skill(self, storage):
        """Test saving and retrieving skill."""
        topic_id = await storage.create_topic("Test", "Desc")
        
        skill = "You are an expert in testing."
        await storage.save_skill(topic_id, skill)
        
        retrieved = await storage.get_skill(topic_id)
        assert retrieved == skill
    
    @pytest.mark.asyncio
    async def test_delete_topic(self, storage):
        """Test deleting topic."""
        topic_id = await storage.create_topic("Test", "Desc")
        
        result = await storage.delete_topic(topic_id)
        assert result is True
        
        topics = await storage.list_topics()
        assert len(topics) == 0
    
    @pytest.mark.asyncio
    async def test_get_all_skills(self, storage):
        """Test getting all skills."""
        topic1_id = await storage.create_topic("Topic1", "Desc1")
        topic2_id = await storage.create_topic("Topic2", "Desc2")
        
        await storage.save_skill(topic1_id, "Skill 1")
        await storage.save_skill(topic2_id, "Skill 2")
        
        skills = await storage.get_all_skills()
        
        assert "Topic1" in skills
        assert "Topic2" in skills
        assert skills["Topic1"] == "Skill 1"


class TestDualParser:
    """Tests for DualParser class."""
    
    @pytest.fixture
    def parser(self, tmp_path):
        """Create parser with temp stats file."""
        p = DualParser()
        p._stats_file = tmp_path / "parser_stats.json"
        return p
    
    @pytest.mark.asyncio
    async def test_extract_with_bs4_fallback(self, parser):
        """Test extraction falls back to BS4."""
        html = """
        <html>
        <body>
            <main>
                <p>This is a test paragraph with enough content to pass the minimum length check.
                It includes multiple sentences to ensure the content is substantial enough.
                The parser should successfully extract this text from the HTML.</p>
            </main>
        </body>
        </html>
        """
        
        result = await parser.extract("http://example.com", html)
        
        assert result.content != ""
        assert "test paragraph" in result.content
        assert result.parser_used in ["trafilatura", "bs4"]
    
    @pytest.mark.asyncio
    async def test_extract_skips_short_content(self, parser):
        """Test that short content is skipped."""
        html = "<html><body><p>Short</p></body></html>"
        
        result = await parser.extract("http://example.com", html)
        
        assert result.parser_used == "skipped"
        assert result.char_count == 0
    
    @pytest.mark.asyncio
    async def test_removes_script_and_style(self, parser):
        """Test that script and style tags are removed."""
        html = f"""
        <html>
        <body>
            <script>alert('evil');</script>
            <style>.hidden {{ display: none; }}</style>
            <p>{'A' * MIN_CONTENT_LENGTH}</p>
        </body>
        </html>
        """
        
        result = await parser.extract("http://example.com", html)
        
        assert "alert" not in result.content
        assert "display: none" not in result.content
    
    def test_stats_tracking(self, parser):
        """Test stats are tracked correctly."""
        stats = parser.get_stats()
        
        assert "trafilatura" in stats
        assert "bs4" in stats
        assert "skipped" in stats
        assert "total_pages" in stats
    
    def test_stats_persistence(self, parser, tmp_path):
        """Test stats are saved and loaded."""
        parser._stats.trafilatura_success = 10
        parser._stats.bs4_success = 5
        parser._save_stats()
        
        # Create new parser with same file
        parser2 = DualParser()
        parser2._stats_file = tmp_path / "parser_stats.json"
        parser2._load_stats()
        
        assert parser2._stats.trafilatura_success == 10
        assert parser2._stats.bs4_success == 5


class TestTopicInfo:
    """Tests for TopicInfo dataclass."""
    
    def test_topic_info_creation(self):
        """Test creating TopicInfo."""
        info = TopicInfo(
            id="test-123",
            name="Test Topic",
            description="Description",
            chunk_count=5,
            skill="Expert prompt",
            status="complete",
            created_at="2024-01-01T00:00:00"
        )
        
        assert info.id == "test-123"
        assert info.name == "Test Topic"
        assert info.status == "complete"
        assert info.chunk_count == 5
