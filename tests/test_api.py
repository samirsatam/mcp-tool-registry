"""Tests for the API endpoints."""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mcp_tool_registry.api import app
from mcp_tool_registry.auth import APIKey, User, get_password_hash, generate_api_key
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


@pytest.fixture(scope="function")
def test_api_key(setup_test_db):
    """Create a test API key with full permissions."""
    db = TestingSessionLocal()
    try:
        # Generate API key
        api_key_value = generate_api_key()
        api_key_hash = get_password_hash(api_key_value)
        
        # Create API key with full permissions
        api_key = APIKey(
            name="test-key",
            key_hash=api_key_hash,
            description="Test API key",
            is_active=True,
            can_create=True,
            can_read=True,
            can_update=True,
            can_delete=True,
        )
        
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        
        yield api_key_value
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_admin_user(setup_test_db):
    """Create a test admin user."""
    db = TestingSessionLocal()
    try:
        # Create admin user
        hashed_password = get_password_hash("admin")
        admin_user = User(
            username="admin",
            email="admin@test.com",
            hashed_password=hashed_password,
            is_admin=True,
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        yield admin_user
    finally:
        db.close()


def get_auth_headers(api_key: str) -> dict:
    """Get authentication headers for API key."""
    # For API key authentication, we need to use the actual API key value, not the name
    return {"Authorization": f"Bearer {api_key}"}


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


def test_create_tool(setup_test_db, sample_tool_data, test_api_key):
    """Test creating a new tool."""
    headers = get_auth_headers(test_api_key)
    response = client.post("/tools", json=sample_tool_data, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == sample_tool_data["name"]
    assert data["version"] == sample_tool_data["version"]
    assert data["description"] == sample_tool_data["description"]
    assert data["schema"] == sample_tool_data["schema"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_duplicate_tool(setup_test_db, sample_tool_data, test_api_key):
    """Test creating a duplicate tool."""
    headers = get_auth_headers(test_api_key)
    # Create first tool
    client.post("/tools", json=sample_tool_data, headers=headers)

    # Try to create duplicate
    response = client.post("/tools", json=sample_tool_data, headers=headers)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_get_tool(setup_test_db, sample_tool_data, test_api_key):
    """Test getting a specific tool."""
    headers = get_auth_headers(test_api_key)
    # Create tool
    create_response = client.post("/tools", json=sample_tool_data, headers=headers)
    tool_name = sample_tool_data["name"]

    # Get tool
    response = client.get(f"/tools/{tool_name}", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == tool_name


def test_get_nonexistent_tool(setup_test_db, test_api_key):
    """Test getting a non-existent tool."""
    headers = get_auth_headers(test_api_key)
    response = client.get("/tools/nonexistent", headers=headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_list_tools(setup_test_db, sample_tool_data, test_api_key):
    """Test listing tools."""
    headers = get_auth_headers(test_api_key)
    # Create a tool
    client.post("/tools", json=sample_tool_data, headers=headers)

    # List tools
    response = client.get("/tools", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert "tools" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "total_pages" in data
    assert len(data["tools"]) == 1
    assert data["total"] == 1


def test_search_tools(setup_test_db, sample_tool_data, test_api_key):
    """Test searching tools."""
    headers = get_auth_headers(test_api_key)
    # Create a tool
    client.post("/tools", json=sample_tool_data, headers=headers)

    # Search tools
    response = client.get("/tools/search?query=calculator", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert len(data["tools"]) == 1
    assert data["tools"][0]["name"] == "calculator"


def test_update_tool(setup_test_db, sample_tool_data, test_api_key):
    """Test updating a tool."""
    headers = get_auth_headers(test_api_key)
    # Create tool
    create_response = client.post("/tools", json=sample_tool_data, headers=headers)
    tool_name = sample_tool_data["name"]

    # Update tool
    update_data = {"version": "2.0.0", "description": "Updated calculator tool"}
    response = client.put(f"/tools/{tool_name}", json=update_data, headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["version"] == "2.0.0"
    assert data["description"] == "Updated calculator tool"


def test_delete_tool(setup_test_db, sample_tool_data, test_api_key):
    """Test deleting a tool."""
    headers = get_auth_headers(test_api_key)
    # Create tool
    client.post("/tools", json=sample_tool_data, headers=headers)
    tool_name = sample_tool_data["name"]

    # Delete tool
    response = client.delete(f"/tools/{tool_name}", headers=headers)
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify tool is deleted
    get_response = client.get(f"/tools/{tool_name}", headers=headers)
    assert get_response.status_code == 404


def test_delete_nonexistent_tool(setup_test_db, test_api_key):
    """Test deleting a non-existent tool."""
    headers = get_auth_headers(test_api_key)
    response = client.delete("/tools/nonexistent", headers=headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
