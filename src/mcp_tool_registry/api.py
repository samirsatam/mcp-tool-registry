"""FastAPI application and endpoints for the MCP tool registry."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import create_tables, get_db
from .models import (
    Base,
    ToolCreate,
    ToolListResponse,
    ToolResponse,
    ToolSearchRequest,
    ToolUpdate,
)
from .services import ToolResponseService, ToolService


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
    try:
        tool_service = ToolService(db)
        db_tool = tool_service.create_tool(tool_data)
        return ToolResponse(**ToolResponseService.tool_to_response(db_tool))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tools", response_model=ToolListResponse)
async def list_tools(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> ToolListResponse:
    """List all registered tools with pagination."""
    tool_service = ToolService(db)
    tools, total = tool_service.list_tools(page, per_page)

    response_data = ToolResponseService.create_paginated_response(
        tools, total, page, per_page
    )
    return ToolListResponse(**response_data)


@app.get("/tools/search", response_model=ToolListResponse)
async def search_tools(
    query: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> ToolListResponse:
    """Search tools by name or description."""
    tool_service = ToolService(db)
    tools, total = tool_service.search_tools(query, page, per_page)

    response_data = ToolResponseService.create_paginated_response(
        tools, total, page, per_page
    )
    return ToolListResponse(**response_data)


@app.get("/tools/{tool_name}", response_model=ToolResponse)
async def get_tool(tool_name: str, db: Session = Depends(get_db)) -> ToolResponse:
    """Get a specific tool by name."""
    tool_service = ToolService(db)
    tool = tool_service.get_tool_by_name(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    return ToolResponse(**ToolResponseService.tool_to_response(tool))


@app.put("/tools/{tool_name}", response_model=ToolResponse)
async def update_tool(
    tool_name: str,
    tool_data: ToolUpdate,
    db: Session = Depends(get_db),
) -> ToolResponse:
    """Update an existing tool."""
    try:
        tool_service = ToolService(db)
        updated_tool = tool_service.update_tool(tool_name, tool_data)
        return ToolResponse(**ToolResponseService.tool_to_response(updated_tool))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/tools/{tool_name}", response_model=dict)
async def delete_tool(tool_name: str, db: Session = Depends(get_db)) -> dict:
    """Delete a tool."""
    try:
        tool_service = ToolService(db)
        tool_service.delete_tool(tool_name)
        return {"message": f"Tool '{tool_name}' deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
