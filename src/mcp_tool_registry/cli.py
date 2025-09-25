"""Command-line interface for the MCP tool registry."""

import uvicorn
from click import command, option

from .api import app


@command()
@option("--host", default="0.0.0.0", help="Host to bind to")
@option("--port", default=8000, help="Port to bind to")
@option("--reload", is_flag=True, help="Enable auto-reload for development")
@option("--log-level", default="info", help="Log level")
def main(host: str, port: int, reload: bool, log_level: str) -> None:
    """Run the MCP tool registry server."""
    uvicorn.run(
        "mcp_tool_registry.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
