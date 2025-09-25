"""Command-line interface for the MCP tool registry."""

import os
import sys
from pathlib import Path

import uvicorn
from alembic import command as alembic_command
from alembic.config import Config
from click import command, group, option

from .api import app


@group()
def cli():
    """MCP Tool Registry CLI."""
    pass


@cli.command()
@option("--host", default="0.0.0.0", help="Host to bind to")
@option("--port", default=8000, help="Port to bind to")
@option("--reload", is_flag=True, help="Enable auto-reload for development")
@option("--log-level", default="info", help="Log level")
def run(host: str, port: int, reload: bool, log_level: str) -> None:
    """Run the MCP tool registry server."""
    uvicorn.run(
        "mcp_tool_registry.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


@cli.group()
def db():
    """Database management commands."""
    pass


@db.command()
def upgrade():
    """Run database migrations to upgrade to the latest version."""
    alembic_cfg = _get_alembic_config()
    alembic_command.upgrade(alembic_cfg, "head")


@db.command()
@option("--revision", default="base", help="Target revision")
def downgrade(revision: str):
    """Downgrade database to a previous version."""
    alembic_cfg = _get_alembic_config()
    alembic_command.downgrade(alembic_cfg, revision)


@db.command()
@option("--message", "-m", required=True, help="Migration message")
def revision(message: str):
    """Create a new migration revision."""
    alembic_cfg = _get_alembic_config()
    alembic_command.revision(alembic_cfg, message=message, autogenerate=True)


@db.command()
def current():
    """Show current database revision."""
    alembic_cfg = _get_alembic_config()
    alembic_command.current(alembic_cfg)


@db.command()
def history():
    """Show migration history."""
    alembic_cfg = _get_alembic_config()
    alembic_command.history(alembic_cfg)


def _get_alembic_config() -> Config:
    """Get Alembic configuration."""
    # Set PYTHONPATH to include src directory
    src_path = Path(__file__).parent.parent.parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Set environment variable for Alembic
    os.environ["PYTHONPATH"] = str(src_path)

    return Config("alembic.ini")


# For backward compatibility
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
    cli()
