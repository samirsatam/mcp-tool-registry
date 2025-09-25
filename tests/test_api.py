"""Tests for the API endpoints."""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mcp_tool_registry.api import app
from mcp_tool_registry.database import get_db
from mcp_tool_registry.models import Base, Tool

# Test database URL
TEST_DATABASE_URL = "sqlite:///./test_mcp_registry.db"

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Create test session factory
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(scope="function")
def setup_test_db():
    """Set up test database for each test."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def sample_tool_data():
    """Sample tool data for testing."""
    return {
        "name": "calculator",
        "version": "1.0.0",
        "description": "A simple calculator tool",
        "schema": {
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
    }


def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_create_tool(setup_test_db, sample_tool_data):
    """Test creating a new tool."""
    response = client.post("/tools", json=sample_tool_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == sample_tool_data["name"]
    assert data["version"] == sample_tool_data["version"]
    assert data["description"] == sample_tool_data["description"]
    assert data["schema"] == sample_tool_data["schema"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_duplicate_tool(setup_test_db, sample_tool_data):
    """Test creating a duplicate tool."""
    # Create first tool
    client.post("/tools", json=sample_tool_data)

    # Try to create duplicate
    response = client.post("/tools", json=sample_tool_data)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_get_tool(setup_test_db, sample_tool_data):
    """Test getting a specific tool."""
    # Create tool
    create_response = client.post("/tools", json=sample_tool_data)
    tool_name = sample_tool_data["name"]

    # Get tool
    response = client.get(f"/tools/{tool_name}")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == tool_name


def test_get_nonexistent_tool(setup_test_db):
    """Test getting a non-existent tool."""
    response = client.get("/tools/nonexistent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_list_tools(setup_test_db, sample_tool_data):
    """Test listing tools."""
    # Create a tool
    client.post("/tools", json=sample_tool_data)

    # List tools
    response = client.get("/tools")
    assert response.status_code == 200

    data = response.json()
    assert "tools" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "total_pages" in data
    assert len(data["tools"]) == 1
    assert data["total"] == 1


def test_search_tools(setup_test_db, sample_tool_data):
    """Test searching tools."""
    # Create a tool
    client.post("/tools", json=sample_tool_data)

    # Search tools
    response = client.get("/tools/search?query=calculator")
    assert response.status_code == 200

    data = response.json()
    assert len(data["tools"]) == 1
    assert data["tools"][0]["name"] == "calculator"


def test_update_tool(setup_test_db, sample_tool_data):
    """Test updating a tool."""
    # Create tool
    create_response = client.post("/tools", json=sample_tool_data)
    tool_name = sample_tool_data["name"]

    # Update tool
    update_data = {"version": "2.0.0", "description": "Updated calculator tool"}
    response = client.put(f"/tools/{tool_name}", json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["version"] == "2.0.0"
    assert data["description"] == "Updated calculator tool"


def test_delete_tool(setup_test_db, sample_tool_data):
    """Test deleting a tool."""
    # Create tool
    client.post("/tools", json=sample_tool_data)
    tool_name = sample_tool_data["name"]

    # Delete tool
    response = client.delete(f"/tools/{tool_name}")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify tool is deleted
    get_response = client.get(f"/tools/{tool_name}")
    assert get_response.status_code == 404


def test_delete_nonexistent_tool(setup_test_db):
    """Test deleting a non-existent tool."""
    response = client.delete("/tools/nonexistent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
