# Example Service

Example Python service for Core Nexus monorepo validation.

## Overview

This is a FastAPI-based microservice that provides user management functionality. It demonstrates:

- FastAPI application structure
- Pydantic models for data validation
- Async service layer
- Comprehensive test coverage
- Poetry dependency management
- Code quality tools (ruff, black, mypy)

## Features

- Create, read, update, delete users
- User validation and email uniqueness
- Pagination for user listings
- Health check endpoints
- OpenAPI documentation

## API Endpoints

- `GET /health` - Health check
- `GET /` - Root endpoint with service info
- `POST /users` - Create a new user
- `GET /users/{user_id}` - Get user by ID
- `PUT /users/{user_id}` - Update user
- `DELETE /users/{user_id}` - Delete user
- `GET /users` - List users with pagination
- `GET /users/count` - Get user count
- `POST /users/clear` - Clear all users (testing)

## Development

### Prerequisites

- Python 3.10+
- Poetry

### Setup

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run linting
poetry run ruff check .
poetry run black --check .
poetry run mypy src/

# Format code
poetry run black .
poetry run ruff check --fix .

# Run the service
poetry run python -m example_service.main
# or
poetry run example-service
```

### Testing

The service includes comprehensive tests:

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test file
poetry run pytest tests/test_service.py
```

## API Documentation

When running the service, visit:

- http://localhost:8000/docs - Swagger UI
- http://localhost:8000/redoc - ReDoc

## Architecture

```
src/example_service/
├── __init__.py          # Package exports
├── main.py              # FastAPI application
├── models.py            # Pydantic models
└── service.py           # Business logic

tests/
├── __init__.py
├── test_service.py      # Service layer tests
└── test_api.py          # API endpoint tests
```