"""Database models for the MCP tool registry."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Tool(Base):
    """SQLAlchemy model for MCP tools."""

    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    schema = Column(Text, nullable=False)  # JSON schema as string
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Tool(name='{self.name}', version='{self.version}')>"


class ToolCreate(BaseModel):
    """Pydantic model for creating a new tool."""

    name: str = Field(..., min_length=1, max_length=255, description="Tool name")
    version: str = Field(..., min_length=1, max_length=50, description="Tool version")
    description: Optional[str] = Field(None, description="Tool description")
    schema: Dict[str, Any] = Field(..., description="Tool JSON schema")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "calculator",
                "version": "1.0.0",
                "description": "A simple calculator tool",
                "tool_schema": {
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
        }
    }


class ToolUpdate(BaseModel):
    """Pydantic model for updating an existing tool."""

    version: Optional[str] = Field(
        None, min_length=1, max_length=50, description="Tool version"
    )
    description: Optional[str] = Field(None, description="Tool description")
    schema: Optional[Dict[str, Any]] = Field(None, description="Tool JSON schema")


class ToolResponse(BaseModel):
    """Pydantic model for tool responses."""

    id: int
    name: str
    version: str
    description: Optional[str]
    schema: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ToolListResponse(BaseModel):
    """Pydantic model for paginated tool list responses."""

    tools: list[ToolResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class ToolSearchRequest(BaseModel):
    """Pydantic model for tool search requests."""

    query: str = Field(..., min_length=1, description="Search query")
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(10, ge=1, le=100, description="Items per page")
