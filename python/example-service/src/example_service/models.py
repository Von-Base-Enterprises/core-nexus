"""
Data models for the example service.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field, validator


class User(BaseModel):
    """User model."""

    id: UUID = Field(default_factory=uuid4, description="Unique user identifier")
    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    is_active: bool = Field(default=True, description="Whether the user is active")

    @validator('name', allow_reuse=True)
    def validate_name(cls, v: str) -> str:
        """Validate and normalize the name."""
        return v.strip()

    @validator('email', allow_reuse=True)
    def validate_email(cls, v: EmailStr) -> EmailStr:
        """Validate and normalize the email."""
        return v.lower().strip()

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "John Doe",
                "email": "john@example.com",
                "created_at": "2023-01-01T00:00:00",
                "is_active": True
            }
        }


class CreateUserRequest(BaseModel):
    """Request model for creating a user."""

    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")

    @validator('name', allow_reuse=True)
    def validate_name(cls, v: str) -> str:
        """Validate and normalize the name."""
        return v.strip()

    @validator('email', allow_reuse=True)
    def validate_email(cls, v: EmailStr) -> EmailStr:
        """Validate and normalize the email."""
        return v.lower().strip()

    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com"
            }
        }


class UpdateUserRequest(BaseModel):
    """Request model for updating a user."""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="User's full name")
    email: Optional[EmailStr] = Field(None, description="User's email address")
    is_active: Optional[bool] = Field(None, description="Whether the user is active")

    @validator('name', allow_reuse=True)
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize the name."""
        return v.strip() if v else v

    @validator('email', allow_reuse=True)
    def validate_email(cls, v: Optional[EmailStr]) -> Optional[EmailStr]:
        """Validate and normalize the email."""
        return v.lower().strip() if v else v

    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "name": "Jane Doe",
                "is_active": False
            }
        }


class UserListResponse(BaseModel):
    """Response model for listing users."""

    users: list[User] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    limit: Optional[int] = Field(None, description="Limit applied to the query")
    offset: int = Field(default=0, description="Offset applied to the query")

    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "users": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "John Doe",
                        "email": "john@example.com",
                        "created_at": "2023-01-01T00:00:00",
                        "is_active": True
                    }
                ],
                "total": 1,
                "limit": 10,
                "offset": 0
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")

    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "error": "User not found",
                "detail": "No user found with the specified ID"
            }
        }
