# MCP Tool Registry

A minimalistic Model Context Protocol (MCP) tool registry built with Python, FastAPI, and SQLite.

## Features

- **Tool Registration**: Register MCP tools with metadata and JSON schemas
- **Tool Discovery**: List and search available tools with pagination
- **Tool Retrieval**: Get specific tool details and schemas
- **RESTful API**: Clean, documented API endpoints with FastAPI
- **Database Migrations**: Alembic-powered schema management with human-readable filenames
- **Service Layer Architecture**: Clean separation of concerns with business logic layer
- **SQLite Backend**: Lightweight database for development and small deployments
- **Type Safety**: Full type hints and Pydantic validation
- **Comprehensive Testing**: 29 tests covering API and service layers
- **Professional CLI**: Enhanced command-line interface with database management

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd mcp-tool-registry
```

2. Install dependencies:
```bash
uv sync --dev
```

3. Run the development server:
```bash
# Option 1: Enhanced CLI (recommended)
uv run mcp-cli run --reload

# Option 2: Legacy CLI (backward compatible)
uv run mcp-registry --reload
```

4. Set up the database:
```bash
# Run migrations to create the database schema
uv run mcp-cli db upgrade
```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

## API Endpoints

### Core Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /tools` - Register a new tool
- `GET /tools` - List all tools (paginated)
- `GET /tools/{name}` - Get specific tool details
- `GET /tools/search` - Search tools by name/description
- `PUT /tools/{name}` - Update an existing tool
- `DELETE /tools/{name}` - Remove a tool

### Example Usage

#### Register a Tool

```bash
curl -X POST "http://localhost:8000/tools" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "calculator",
    "version": "1.0.0",
    "description": "A simple calculator tool",
    "schema": {
      "type": "object",
      "properties": {
        "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
        "a": {"type": "number"},
        "b": {"type": "number"}
      },
      "required": ["operation", "a", "b"]
    }
  }'
```

#### List Tools

```bash
curl "http://localhost:8000/tools?page=1&per_page=10"
```

#### Search Tools

```bash
curl "http://localhost:8000/tools/search?query=calculator&page=1&per_page=10"
```

#### Get Tool Details

```bash
curl "http://localhost:8000/tools/calculator"
```

## Development

### Project Structure

```
mcp-tool-registry/
├── src/mcp_tool_registry/
│   ├── __init__.py          # Package initialization
│   ├── api.py              # FastAPI application and endpoints (controllers)
│   ├── cli.py              # Command-line interface
│   ├── database.py         # Database configuration and connection
│   ├── models.py           # SQLAlchemy and Pydantic models
│   └── services.py         # Business logic service layer
├── migrations/             # Database migration files
│   ├── versions/          # Migration version files
│   ├── env.py             # Alembic environment configuration
│   └── script.py.mako     # Migration template
├── tests/
│   ├── __init__.py
│   ├── test_api.py         # API endpoint tests
│   └── test_services.py    # Service layer tests
├── examples/
│   └── basic_usage.py     # Usage examples
├── alembic.ini            # Alembic configuration
├── MIGRATION_EXAMPLE.md   # Migration workflow example
├── pyproject.toml         # Project configuration
└── README.md
```

### Architecture

The project follows the **Service Layer Pattern** (also known as Repository Pattern) for clean separation of concerns:

- **API Layer** (`api.py`): FastAPI endpoints that handle HTTP requests/responses
- **Service Layer** (`services.py`): Business logic and data operations
- **Data Layer** (`models.py`, `database.py`): Database models and connection management

This architecture provides:
- **Separation of Concerns**: Business logic is separated from HTTP handling
- **Testability**: Services can be tested independently of the API
- **Maintainability**: Changes to business logic don't affect API structure
- **Reusability**: Services can be used by other parts of the application

### Database Migrations

The project uses **Alembic** for database schema management, following Python best practices:

#### Migration Commands

```bash
# Show available CLI commands
uv run mcp-cli --help

# Database management commands
uv run mcp-cli db --help

# Run migrations to upgrade database
uv run mcp-cli db upgrade

# Show current database revision
uv run mcp-cli db current

# Show migration history
uv run mcp-cli db history

# Create a new migration (after model changes)
uv run mcp-cli db revision -m "Add new field to tools table"

# Downgrade to previous version
uv run mcp-cli db downgrade --revision <revision_id>
```

#### Migration Workflow

1. **Modify Models**: Update SQLAlchemy models in `src/mcp_tool_registry/models.py`
2. **Generate Migration**: Run `uv run mcp-cli db revision -m "Description of changes"`
3. **Review Migration**: Check the generated migration file in `migrations/versions/`
4. **Apply Migration**: Run `uv run mcp-cli db upgrade`
5. **Test**: Run tests to ensure everything works correctly

#### Migration Files

- **Location**: `migrations/versions/`
- **Filename**: `{year}_{month}_{day}_{hour}{minute}_{description}.py` (human-readable with date/time)
- **Internal ID**: Each file still contains a unique revision ID for Alembic's tracking
- **Format**: Each migration contains `upgrade()` and `downgrade()` functions
- **Version Control**: All migration files should be committed to version control

**Example:**
- **Filename**: `2025_09_25_1540_create_tools_table.py` (human-readable)
- **Internal ID**: `b8950eedfb43` (used by Alembic for dependencies and rollbacks)

#### Custom Migration Naming

The project uses a human-readable naming format with date/time prefixes. You can customize this in `alembic.ini`:

```ini
# Available tokens for file_template:
# %%(year)d        - 4-digit year (e.g., 2025)
# %%(month).2d     - 2-digit month (e.g., 09)
# %%(day).2d       - 2-digit day (e.g., 25)
# %%(hour).2d      - 2-digit hour (e.g., 15)
# %%(minute).2d    - 2-digit minute (e.g., 45)
# %%(rev)s         - Revision ID (e.g., a2c5f6ed102e)
# %%(slug)s        - Description slug (e.g., add_user_table)

# Current format: 2025_09_25_1545_add_user_table.py
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d_%%(slug)s

# Alternative formats:
# With revision ID: 2025_09_25_1545_a2c5f6ed102e_add_user_table.py
# file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s

# ISO format: 2025-09-25T15:45_add_user_table.py
# file_template = %%(year)d-%%(month).2d-%%(day).2dT%%(hour).2d%%(minute).2d_%%(slug)s
```

### Examples and Documentation

- **`examples/basic_usage.py`**: Complete example showing how to use the API
- **`MIGRATION_EXAMPLE.md`**: Step-by-step guide for adding new database fields
- **Interactive API Docs**: Available at `http://localhost:8000/docs` when server is running

### Running Tests

```bash
# Run all tests
uv run pytest

# Run only API tests
uv run pytest tests/test_api.py

# Run only service layer tests
uv run pytest tests/test_services.py

# Run with verbose output
uv run pytest -v
```

### Code Quality

The project includes configuration for:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

Run all quality checks:

```bash
uv run black src tests
uv run isort src tests
uv run flake8 src tests
uv run mypy src
```

### Database

The application uses SQLite for simplicity with Alembic migrations for schema management. The database file (`mcp_registry.db`) is created automatically when you run migrations.

**Initial Setup:**
```bash
# Run migrations to create the database schema
uv run mcp-cli db upgrade
```

For production deployments, consider migrating to PostgreSQL or another production-ready database by updating the `DATABASE_URL` in `alembic.ini`.

## Configuration

### Environment Variables

- `DATABASE_URL`: Database connection string (default: `sqlite:///./mcp_registry.db`)

### CLI Commands

The project provides two CLI interfaces for different use cases:

#### Enhanced CLI (mcp-cli) - Recommended

```bash
# Show all available commands
uv run mcp-cli --help

# Server commands
uv run mcp-cli run --help
uv run mcp-cli run --reload --port 8000

# Database management commands
uv run mcp-cli db --help
uv run mcp-cli db upgrade          # Run migrations
uv run mcp-cli db current          # Show current revision
uv run mcp-cli db history          # Show migration history
uv run mcp-cli db revision -m "..." # Create new migration
uv run mcp-cli db downgrade --revision <id> # Rollback migration
```

**Server Options:**
- `--host`: Host to bind to (default: 0.0.0.0)
- `--port`: Port to bind to (default: 8000)
- `--reload`: Enable auto-reload for development
- `--log-level`: Log level (default: info)

#### Legacy CLI (mcp-registry) - Backward Compatible

```bash
# Simple server command (backward compatible)
uv run mcp-registry --help
uv run mcp-registry --reload
```

**When to use which:**
- **mcp-cli**: Use for development, database management, and full feature set
- **mcp-registry**: Use for simple server startup or existing scripts

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `uv run pytest`
5. Run quality checks: `uv run black src tests && uv run isort src tests && uv run flake8 src tests && uv run mypy src`
6. Commit your changes: `git commit -am 'Add feature'`
7. Push to the branch: `git push origin feature-name`
8. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Roadmap

### Completed ✅
- [x] **Service Layer Architecture**: Clean separation of concerns
- [x] **Database Migrations**: Alembic with human-readable filenames
- [x] **Professional CLI**: Enhanced command-line interface
- [x] **Comprehensive Testing**: 29 tests covering all functionality
- [x] **Type Safety**: Full type hints and Pydantic validation
- [x] **Code Quality**: Black, isort, flake8, mypy configuration

### Planned 🚀
- [ ] **Authentication and authorization**: JWT-based auth system
- [ ] **Tool versioning and history**: Track tool changes over time
- [ ] **Tool categories and tags**: Organize tools by type/purpose
- [ ] **Rate limiting**: API rate limiting and quotas
- [ ] **Metrics and monitoring**: Health checks and performance metrics
- [ ] **Docker support**: Containerization and deployment
- [ ] **PostgreSQL support**: Production-ready database support
- [ ] **Tool validation**: Validate tools against MCP specifications
- [ ] **API versioning**: Support for multiple API versions
- [ ] **Webhook support**: Real-time notifications for tool changes