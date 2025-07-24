"""
Example Python service for Core Nexus monorepo validation.

This package provides a FastAPI-based service with user management functionality
for demonstrating the Python toolchain in the monorepo.
"""

__version__ = "0.1.0"
__author__ = "Tyvonne Boykin <tyvonne@vonbase.com>"

from .main import app
from .models import CreateUserRequest, UpdateUserRequest, User
from .service import UserService

__all__ = [
    "User",
    "CreateUserRequest",
    "UpdateUserRequest",
    "UserService",
    "app",
]
