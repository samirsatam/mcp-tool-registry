"""Service layer for MCP tool registry business logic."""

from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import deserialize_schema, serialize_schema
from .models import Tool, ToolCreate, ToolUpdate


class ToolService:
    """Service class for tool-related business logic."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db

    def create_tool(self, tool_data: ToolCreate) -> Tool:
        """Create a new tool."""
        # Check if tool already exists
        existing_tool = self.get_tool_by_name(tool_data.name)
        if existing_tool:
            raise ValueError(f"Tool '{tool_data.name}' already exists")

        # Create new tool
        db_tool = Tool(
            name=tool_data.name,
            version=tool_data.version,
            description=tool_data.description,
            schema=serialize_schema(tool_data.schema),
        )

        self.db.add(db_tool)
        self.db.commit()
        self.db.refresh(db_tool)
        return db_tool

    def get_tool_by_name(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.db.query(Tool).filter(Tool.name == name).first()

    def get_tool_by_id(self, tool_id: int) -> Optional[Tool]:
        """Get a tool by ID."""
        return self.db.query(Tool).filter(Tool.id == tool_id).first()

    def list_tools(self, page: int = 1, per_page: int = 10) -> tuple[List[Tool], int]:
        """List tools with pagination."""
        # Calculate offset
        offset = (page - 1) * per_page

        # Get total count
        total = self.db.query(func.count(Tool.id)).scalar()

        # Get tools for current page
        tools = (
            self.db.query(Tool)
            .order_by(Tool.created_at.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )

        return tools, total

    def search_tools(
        self, query: str, page: int = 1, per_page: int = 10
    ) -> tuple[List[Tool], int]:
        """Search tools by name or description."""
        # Calculate offset
        offset = (page - 1) * per_page

        # Build search query
        search_filter = Tool.name.contains(query) | Tool.description.contains(query)

        # Get total count
        total = self.db.query(func.count(Tool.id)).filter(search_filter).scalar()

        # Get tools for current page
        tools = (
            self.db.query(Tool)
            .filter(search_filter)
            .order_by(Tool.created_at.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )

        return tools, total

    def update_tool(self, name: str, tool_data: ToolUpdate) -> Tool:
        """Update an existing tool."""
        tool = self.get_tool_by_name(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")

        # Update fields if provided
        if tool_data.version is not None:
            tool.version = tool_data.version
        if tool_data.description is not None:
            tool.description = tool_data.description
        if tool_data.schema is not None:
            tool.schema = serialize_schema(tool_data.schema)

        self.db.commit()
        self.db.refresh(tool)
        return tool

    def delete_tool(self, name: str) -> bool:
        """Delete a tool."""
        tool = self.get_tool_by_name(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")

        self.db.delete(tool)
        self.db.commit()
        return True

    def get_tool_count(self) -> int:
        """Get total number of tools."""
        return self.db.query(func.count(Tool.id)).scalar()


class ToolResponseService:
    """Service for converting database models to response models."""

    @staticmethod
    def tool_to_response(tool: Tool) -> dict:
        """Convert Tool model to response dictionary."""
        return {
            "id": tool.id,
            "name": tool.name,
            "version": tool.version,
            "description": tool.description,
            "schema": deserialize_schema(tool.schema),
            "created_at": tool.created_at,
            "updated_at": tool.updated_at,
        }

    @staticmethod
    def tools_to_response_list(tools: List[Tool]) -> List[dict]:
        """Convert list of Tool models to response list."""
        return [ToolResponseService.tool_to_response(tool) for tool in tools]

    @staticmethod
    def create_paginated_response(
        tools: List[Tool], total: int, page: int, per_page: int
    ) -> dict:
        """Create paginated response."""
        tool_responses = ToolResponseService.tools_to_response_list(tools)
        total_pages = (total + per_page - 1) // per_page

        return {
            "tools": tool_responses,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }
