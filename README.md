# MCP Tool Registry

A minimalistic Model Context Protocol (MCP) tool registry built with Python, FastAPI, and SQLite.

## Features

- **Tool Registration**: Register MCP tools with metadata and JSON schemas
- **Tool Discovery**: List and search available tools with pagination
- **Tool Retrieval**: Get specific tool details and schemas
- **RESTful API**: Clean, documented API endpoints
- **SQLite Backend**: Lightweight database for development and small deployments
- **Type Safety**: Full type hints and Pydantic validation
- **Testing**: Comprehensive test suite with pytest

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
uv run mcp-registry --reload
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
├── tests/
│   ├── __init__.py
│   ├── test_api.py         # API endpoint tests
│   └── test_services.py    # Service layer tests
├── pyproject.toml          # Project configuration
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

The application uses SQLite for simplicity. The database file (`mcp_registry.db`) is created automatically on first run.

For production deployments, consider migrating to PostgreSQL or another production-ready database by updating the `DATABASE_URL` in `database.py`.

## Configuration

### Environment Variables

- `DATABASE_URL`: Database connection string (default: `sqlite:///./mcp_registry.db`)

### Server Configuration

The CLI supports several options:

```bash
uv run mcp-registry --help
```

Options:
- `--host`: Host to bind to (default: 0.0.0.0)
- `--port`: Port to bind to (default: 8000)
- `--reload`: Enable auto-reload for development
- `--log-level`: Log level (default: info)

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

- [ ] Authentication and authorization
- [ ] Tool versioning and history
- [ ] Tool categories and tags
- [ ] Rate limiting
- [ ] Metrics and monitoring
- [ ] Docker support
- [ ] PostgreSQL support
- [ ] Tool validation against MCP specifications