#!/usr/bin/env python3
"""Development server runner for MCP Tool Registry."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "mcp_tool_registry.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )