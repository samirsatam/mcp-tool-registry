"""FastAPI application and endpoints for the MCP tool registry."""

import json
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import create_tables, deserialize_schema, get_db, serialize_schema
from .models import (
    Base,
    Tool,
    ToolCreate,
    ToolListResponse,
    ToolResponse,
    ToolSearchRequest,
    ToolUpdate,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    create_tables()
    yield
    # Shutdown (if needed)


# Create FastAPI app
app = FastAPI(
    title="MCP Tool Registry",
    description="A minimalistic Model Context Protocol tool registry",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=dict)
async def root() -> dict:
    """Root endpoint with basic information."""
    return {
        "message": "MCP Tool Registry API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", response_model=dict)
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "mcp-tool-registry"}


@app.post("/tools", response_model=ToolResponse, status_code=201)
async def create_tool(
    tool_data: ToolCreate, db: Session = Depends(get_db)
) -> ToolResponse:
    """Register a new MCP tool."""
    # Check if tool already exists
    existing_tool = db.query(Tool).filter(Tool.name == tool_data.name).first()
    if existing_tool:
        raise HTTPException(
            status_code=400, detail=f"Tool '{tool_data.name}' already exists"
        )

    # Create new tool
    db_tool = Tool(
        name=tool_data.name,
        version=tool_data.version,
        description=tool_data.description,
        schema=serialize_schema(tool_data.schema),
    )

    db.add(db_tool)
    db.commit()
    db.refresh(db_tool)

    return ToolResponse(
        id=db_tool.id,
        name=db_tool.name,
        version=db_tool.version,
        description=db_tool.description,
        schema=deserialize_schema(db_tool.schema),
        created_at=db_tool.created_at,
        updated_at=db_tool.updated_at,
    )


@app.get("/tools", response_model=ToolListResponse)
async def list_tools(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> ToolListResponse:
    """List all registered tools with pagination."""
    # Calculate offset
    offset = (page - 1) * per_page

    # Get total count
    total = db.query(func.count(Tool.id)).scalar()

    # Get tools for current page
    tools = (
        db.query(Tool)
        .order_by(Tool.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    # Convert to response format
    tool_responses = [
        ToolResponse(
            id=tool.id,
            name=tool.name,
            version=tool.version,
            description=tool.description,
            schema=deserialize_schema(tool.schema),
            created_at=tool.created_at,
            updated_at=tool.updated_at,
        )
        for tool in tools
    ]

    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page

    return ToolListResponse(
        tools=tool_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@app.get("/tools/search", response_model=ToolListResponse)
async def search_tools(
    query: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> ToolListResponse:
    """Search tools by name or description."""
    # Calculate offset
    offset = (page - 1) * per_page

    # Build search query
    search_filter = Tool.name.contains(query) | Tool.description.contains(query)

    # Get total count
    total = db.query(func.count(Tool.id)).filter(search_filter).scalar()

    # Get tools for current page
    tools = (
        db.query(Tool)
        .filter(search_filter)
        .order_by(Tool.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    # Convert to response format
    tool_responses = [
        ToolResponse(
            id=tool.id,
            name=tool.name,
            version=tool.version,
            description=tool.description,
            schema=deserialize_schema(tool.schema),
            created_at=tool.created_at,
            updated_at=tool.updated_at,
        )
        for tool in tools
    ]

    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page

    return ToolListResponse(
        tools=tool_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@app.get("/tools/{tool_name}", response_model=ToolResponse)
async def get_tool(tool_name: str, db: Session = Depends(get_db)) -> ToolResponse:
    """Get a specific tool by name."""
    tool = db.query(Tool).filter(Tool.name == tool_name).first()
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    return ToolResponse(
        id=tool.id,
        name=tool.name,
        version=tool.version,
        description=tool.description,
        schema=deserialize_schema(tool.schema),
        created_at=tool.created_at,
        updated_at=tool.updated_at,
    )


@app.put("/tools/{tool_name}", response_model=ToolResponse)
async def update_tool(
    tool_name: str,
    tool_data: ToolUpdate,
    db: Session = Depends(get_db),
) -> ToolResponse:
    """Update an existing tool."""
    tool = db.query(Tool).filter(Tool.name == tool_name).first()
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    # Update fields if provided
    if tool_data.version is not None:
        tool.version = tool_data.version
    if tool_data.description is not None:
        tool.description = tool_data.description
    if tool_data.schema is not None:
        tool.schema = serialize_schema(tool_data.schema)

    db.commit()
    db.refresh(tool)

    return ToolResponse(
        id=tool.id,
        name=tool.name,
        version=tool.version,
        description=tool.description,
        schema=deserialize_schema(tool.schema),
        created_at=tool.created_at,
        updated_at=tool.updated_at,
    )


@app.delete("/tools/{tool_name}", response_model=dict)
async def delete_tool(tool_name: str, db: Session = Depends(get_db)) -> dict:
    """Delete a tool."""
    tool = db.query(Tool).filter(Tool.name == tool_name).first()
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    db.delete(tool)
    db.commit()

    return {"message": f"Tool '{tool_name}' deleted successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
