"""Tests for the service layer."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mcp_tool_registry.database import Base
from mcp_tool_registry.models import ToolCreate, ToolUpdate
from mcp_tool_registry.services import ToolResponseService, ToolService

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test_services.db"

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Create test session factory
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def setup_test_db():
    """Set up test database for each test."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """Create a test database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def tool_service(db_session):
    """Create a tool service instance."""
    return ToolService(db_session)


@pytest.fixture
def sample_tool_data():
    """Sample tool data for testing."""
    return ToolCreate(
        name="calculator",
        version="1.0.0",
        description="A simple calculator tool",
        schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                },
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["operation", "a", "b"],
        },
    )


class TestToolService:
    """Test cases for ToolService."""

    def test_create_tool_success(self, setup_test_db, tool_service, sample_tool_data):
        """Test successful tool creation."""
        tool = tool_service.create_tool(sample_tool_data)

        assert tool.name == sample_tool_data.name
        assert tool.version == sample_tool_data.version
        assert tool.description == sample_tool_data.description
        assert tool.id is not None
        assert tool.created_at is not None
        assert tool.updated_at is not None

    def test_create_duplicate_tool_fails(
        self, setup_test_db, tool_service, sample_tool_data
    ):
        """Test that creating duplicate tool fails."""
        # Create first tool
        tool_service.create_tool(sample_tool_data)

        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            tool_service.create_tool(sample_tool_data)

    def test_get_tool_by_name_exists(
        self, setup_test_db, tool_service, sample_tool_data
    ):
        """Test getting existing tool by name."""
        created_tool = tool_service.create_tool(sample_tool_data)
        retrieved_tool = tool_service.get_tool_by_name(sample_tool_data.name)

        assert retrieved_tool is not None
        assert retrieved_tool.id == created_tool.id
        assert retrieved_tool.name == sample_tool_data.name

    def test_get_tool_by_name_not_exists(self, setup_test_db, tool_service):
        """Test getting non-existent tool by name."""
        tool = tool_service.get_tool_by_name("nonexistent")
        assert tool is None

    def test_list_tools_empty(self, setup_test_db, tool_service):
        """Test listing tools when none exist."""
        tools, total = tool_service.list_tools()
        assert len(tools) == 0
        assert total == 0

    def test_list_tools_with_data(self, setup_test_db, tool_service, sample_tool_data):
        """Test listing tools with data."""
        tool_service.create_tool(sample_tool_data)
        tools, total = tool_service.list_tools()

        assert len(tools) == 1
        assert total == 1
        assert tools[0].name == sample_tool_data.name

    def test_list_tools_pagination(self, setup_test_db, tool_service):
        """Test tool listing with pagination."""
        # Create multiple tools
        for i in range(5):
            tool_data = ToolCreate(
                name=f"tool_{i}",
                version="1.0.0",
                description=f"Tool {i}",
                schema={"type": "object"},
            )
            tool_service.create_tool(tool_data)

        # Test first page
        tools, total = tool_service.list_tools(page=1, per_page=2)
        assert len(tools) == 2
        assert total == 5

        # Test second page
        tools, total = tool_service.list_tools(page=2, per_page=2)
        assert len(tools) == 2
        assert total == 5

    def test_search_tools_by_name(self, setup_test_db, tool_service, sample_tool_data):
        """Test searching tools by name."""
        tool_service.create_tool(sample_tool_data)

        tools, total = tool_service.search_tools("calculator")
        assert len(tools) == 1
        assert total == 1
        assert tools[0].name == "calculator"

    def test_search_tools_by_description(
        self, setup_test_db, tool_service, sample_tool_data
    ):
        """Test searching tools by description."""
        tool_service.create_tool(sample_tool_data)

        tools, total = tool_service.search_tools("simple")
        assert len(tools) == 1
        assert total == 1
        assert tools[0].name == "calculator"

    def test_search_tools_no_results(self, setup_test_db, tool_service):
        """Test searching tools with no results."""
        tools, total = tool_service.search_tools("nonexistent")
        assert len(tools) == 0
        assert total == 0

    def test_update_tool_success(self, setup_test_db, tool_service, sample_tool_data):
        """Test successful tool update."""
        created_tool = tool_service.create_tool(sample_tool_data)

        update_data = ToolUpdate(version="2.0.0", description="Updated calculator tool")

        updated_tool = tool_service.update_tool(sample_tool_data.name, update_data)

        assert updated_tool.id == created_tool.id
        assert updated_tool.version == "2.0.0"
        assert updated_tool.description == "Updated calculator tool"
        assert updated_tool.name == sample_tool_data.name

    def test_update_tool_not_found(self, setup_test_db, tool_service):
        """Test updating non-existent tool."""
        update_data = ToolUpdate(version="2.0.0")

        with pytest.raises(ValueError, match="not found"):
            tool_service.update_tool("nonexistent", update_data)

    def test_delete_tool_success(self, setup_test_db, tool_service, sample_tool_data):
        """Test successful tool deletion."""
        tool_service.create_tool(sample_tool_data)

        result = tool_service.delete_tool(sample_tool_data.name)
        assert result is True

        # Verify tool is deleted
        tool = tool_service.get_tool_by_name(sample_tool_data.name)
        assert tool is None

    def test_delete_tool_not_found(self, setup_test_db, tool_service):
        """Test deleting non-existent tool."""
        with pytest.raises(ValueError, match="not found"):
            tool_service.delete_tool("nonexistent")

    def test_get_tool_count(self, setup_test_db, tool_service, sample_tool_data):
        """Test getting tool count."""
        assert tool_service.get_tool_count() == 0

        tool_service.create_tool(sample_tool_data)
        assert tool_service.get_tool_count() == 1


class TestToolResponseService:
    """Test cases for ToolResponseService."""

    def test_tool_to_response(self, setup_test_db, tool_service, sample_tool_data):
        """Test converting tool to response."""
        tool = tool_service.create_tool(sample_tool_data)
        response = ToolResponseService.tool_to_response(tool)

        assert response["id"] == tool.id
        assert response["name"] == tool.name
        assert response["version"] == tool.version
        assert response["description"] == tool.description
        assert response["schema"] == sample_tool_data.schema
        assert "created_at" in response
        assert "updated_at" in response

    def test_tools_to_response_list(
        self, setup_test_db, tool_service, sample_tool_data
    ):
        """Test converting list of tools to response list."""
        tool1 = tool_service.create_tool(sample_tool_data)

        tool2_data = ToolCreate(
            name="weather",
            version="1.0.0",
            description="Weather tool",
            schema={"type": "object"},
        )
        tool2 = tool_service.create_tool(tool2_data)

        tools = [tool1, tool2]
        responses = ToolResponseService.tools_to_response_list(tools)

        assert len(responses) == 2
        assert responses[0]["name"] == "calculator"
        assert responses[1]["name"] == "weather"

    def test_create_paginated_response(
        self, setup_test_db, tool_service, sample_tool_data
    ):
        """Test creating paginated response."""
        tool = tool_service.create_tool(sample_tool_data)
        tools = [tool]

        response = ToolResponseService.create_paginated_response(tools, 1, 1, 10)

        assert response["tools"] is not None
        assert len(response["tools"]) == 1
        assert response["total"] == 1
        assert response["page"] == 1
        assert response["per_page"] == 10
        assert response["total_pages"] == 1
