"""
FastAPI application for the example service.
"""

from typing import Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from .models import (
    CreateUserRequest,
    ErrorResponse,
    UpdateUserRequest,
    User,
    UserListResponse,
)
from .service import DuplicateEmailError, UserNotFoundError, UserService

# Create FastAPI app
app = FastAPI(
    title="Example Service",
    description="Example Python service for Core Nexus monorepo validation",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Create service instance
user_service = UserService()


@app.exception_handler(UserNotFoundError)
async def user_not_found_handler(request, exc: UserNotFoundError) -> JSONResponse:
    """Handle UserNotFoundError exceptions."""
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(error="User not found", detail=str(exc)).dict()
    )


@app.exception_handler(DuplicateEmailError)
async def duplicate_email_handler(request, exc: DuplicateEmailError) -> JSONResponse:
    """Handle DuplicateEmailError exceptions."""
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(error="Duplicate email", detail=str(exc)).dict()
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "example-service"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Example Service API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.post("/users", response_model=User, status_code=201)
async def create_user(request: CreateUserRequest) -> User:
    """
    Create a new user.

    Args:
        request: The user creation request

    Returns:
        The created user

    Raises:
        HTTPException: If validation fails or email already exists
    """
    try:
        return await user_service.create_user(request)
    except DuplicateEmailError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None


@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: UUID) -> User:
    """
    Get a user by ID.

    Args:
        user_id: The user ID

    Returns:
        The user

    Raises:
        HTTPException: If the user is not found
    """
    try:
        return await user_service.get_user(user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@app.put("/users/{user_id}", response_model=User)
async def update_user(user_id: UUID, request: UpdateUserRequest) -> User:
    """
    Update a user.

    Args:
        user_id: The user ID
        request: The update request

    Returns:
        The updated user

    Raises:
        HTTPException: If the user is not found or validation fails
    """
    try:
        return await user_service.update_user(user_id, request)
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except DuplicateEmailError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None


@app.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: UUID) -> None:
    """
    Delete a user.

    Args:
        user_id: The user ID

    Raises:
        HTTPException: If the user is not found
    """
    deleted = await user_service.delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")


@app.get("/users/count", response_model=dict[str, int])
async def get_user_count(
    active_only: bool = Query(False, description="Count only active users")
) -> dict[str, int]:
    """
    Get the total number of users.

    Args:
        active_only: Whether to count only active users

    Returns:
        User count
    """
    count = await user_service.get_user_count(active_only=active_only)
    return {"count": count}


@app.get("/users", response_model=UserListResponse)
async def list_users(
    limit: Optional[int] = Query(None, ge=1, le=100, description="Maximum number of users to return"),
    offset: int = Query(0, ge=0, description="Number of users to skip"),
    active_only: bool = Query(False, description="Return only active users")
) -> UserListResponse:
    """
    List users with pagination.

    Args:
        limit: Maximum number of users to return (1-100)
        offset: Number of users to skip
        active_only: Whether to return only active users

    Returns:
        Paginated list of users
    """
    users, total = await user_service.list_users(limit=limit, offset=offset, active_only=active_only)

    return UserListResponse(
        users=users,
        total=total,
        limit=limit,
        offset=offset
    )


@app.post("/users/clear", status_code=204)
async def clear_users() -> None:
    """Clear all users (useful for testing)."""
    await user_service.clear_all_users()


def main() -> None:
    """Entry point for running the service."""
    import uvicorn
    uvicorn.run(
        "example_service.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
