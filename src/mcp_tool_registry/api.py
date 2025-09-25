"""FastAPI application and endpoints for the MCP tool registry."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .admin import router as admin_router
from .auth import get_current_user, require_permission, TokenData
from .auth_endpoints import router as auth_router
from .database import create_tables, get_db
from .models import (
    Base,
    ToolCreate,
    ToolListResponse,
    ToolResponse,
    ToolSearchRequest,
    ToolUpdate,
)
from .security import setup_security_middleware
from .services import ToolResponseService, ToolService

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


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
    description="A secure Model Context Protocol tool registry with authentication and authorization",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Set up security middleware
app = setup_security_middleware(app, {
    "allowed_origins": ["http://localhost:3000", "http://localhost:8080"],
    "requests_per_minute": 60,
    "audit_log": "audit.log"
})

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(auth_router)
app.include_router(admin_router)


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
@limiter.limit("20/minute")
async def create_tool(
    request: Request,
    tool_data: ToolCreate, 
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_permission("create"))
) -> ToolResponse:
    """Register a new MCP tool."""
    try:
        tool_service = ToolService(db)
        db_tool = tool_service.create_tool(tool_data)
        return ToolResponse(**ToolResponseService.tool_to_response(db_tool))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tools", response_model=ToolListResponse)
@limiter.limit("60/minute")
async def list_tools(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_permission("read"))
) -> ToolListResponse:
    """List all registered tools with pagination."""
    tool_service = ToolService(db)
    tools, total = tool_service.list_tools(page, per_page)

    response_data = ToolResponseService.create_paginated_response(
        tools, total, page, per_page
    )
    return ToolListResponse(**response_data)


@app.get("/tools/search", response_model=ToolListResponse)
@limiter.limit("60/minute")
async def search_tools(
    request: Request,
    query: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_permission("read"))
) -> ToolListResponse:
    """Search tools by name or description."""
    tool_service = ToolService(db)
    tools, total = tool_service.search_tools(query, page, per_page)

    response_data = ToolResponseService.create_paginated_response(
        tools, total, page, per_page
    )
    return ToolListResponse(**response_data)


@app.get("/tools/{tool_name}", response_model=ToolResponse)
@limiter.limit("60/minute")
async def get_tool(
    request: Request,
    tool_name: str, 
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_permission("read"))
) -> ToolResponse:
    """Get a specific tool by name."""
    tool_service = ToolService(db)
    tool = tool_service.get_tool_by_name(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    return ToolResponse(**ToolResponseService.tool_to_response(tool))


@app.put("/tools/{tool_name}", response_model=ToolResponse)
@limiter.limit("20/minute")
async def update_tool(
    request: Request,
    tool_name: str,
    tool_data: ToolUpdate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_permission("update"))
) -> ToolResponse:
    """Update an existing tool."""
    try:
        tool_service = ToolService(db)
        updated_tool = tool_service.update_tool(tool_name, tool_data)
        return ToolResponse(**ToolResponseService.tool_to_response(updated_tool))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/tools/{tool_name}", response_model=dict)
@limiter.limit("10/minute")
async def delete_tool(
    request: Request,
    tool_name: str, 
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(require_permission("delete"))
) -> dict:
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
