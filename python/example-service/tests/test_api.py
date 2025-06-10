"""
Tests for the FastAPI application.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from example_service.main import app, user_service


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
async def clear_users():
    """Clear users before each test."""
    await user_service.clear_all_users()


class TestHealthEndpoints:
    """Tests for health and info endpoints."""

    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "example-service"}

    def test_root(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Example Service API"
        assert data["version"] == "0.1.0"
        assert data["docs"] == "/docs"


class TestUserEndpoints:
    """Tests for user management endpoints."""

    def test_create_user(self, client: TestClient):
        """Test creating a user."""
        user_data = {
            "name": "John Doe",
            "email": "john@example.com"
        }

        response = client.post("/users", json=user_data)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "John Doe"
        assert data["email"] == "john@example.com"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_create_user_invalid_email(self, client: TestClient):
        """Test creating a user with invalid email."""
        user_data = {
            "name": "John Doe",
            "email": "invalid-email"
        }

        response = client.post("/users", json=user_data)
        assert response.status_code == 422  # Validation error

    def test_create_user_duplicate_email(self, client: TestClient):
        """Test creating a user with duplicate email."""
        user_data = {
            "name": "John Doe",
            "email": "john@example.com"
        }

        # Create first user
        response = client.post("/users", json=user_data)
        assert response.status_code == 201

        # Try to create second user with same email
        response = client.post("/users", json=user_data)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_get_user(self, client: TestClient):
        """Test getting a user by ID."""
        # Create a user first
        user_data = {
            "name": "John Doe",
            "email": "john@example.com"
        }

        create_response = client.post("/users", json=user_data)
        assert create_response.status_code == 201
        created_user = create_response.json()

        # Get the user
        response = client.get(f"/users/{created_user['id']}")
        assert response.status_code == 200
        assert response.json() == created_user

    def test_get_user_not_found(self, client: TestClient):
        """Test getting a non-existent user."""
        user_id = str(uuid4())
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_user(self, client: TestClient):
        """Test updating a user."""
        # Create a user first
        user_data = {
            "name": "John Doe",
            "email": "john@example.com"
        }

        create_response = client.post("/users", json=user_data)
        assert create_response.status_code == 201
        created_user = create_response.json()

        # Update the user
        update_data = {
            "name": "Jane Doe",
            "is_active": False
        }

        response = client.put(f"/users/{created_user['id']}", json=update_data)
        assert response.status_code == 200

        updated_user = response.json()
        assert updated_user["name"] == "Jane Doe"
        assert updated_user["email"] == "john@example.com"  # unchanged
        assert updated_user["is_active"] is False
        assert updated_user["id"] == created_user["id"]

    def test_update_user_not_found(self, client: TestClient):
        """Test updating a non-existent user."""
        user_id = str(uuid4())
        update_data = {"name": "Jane Doe"}

        response = client.put(f"/users/{user_id}", json=update_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_delete_user(self, client: TestClient):
        """Test deleting a user."""
        # Create a user first
        user_data = {
            "name": "John Doe",
            "email": "john@example.com"
        }

        create_response = client.post("/users", json=user_data)
        assert create_response.status_code == 201
        created_user = create_response.json()

        # Delete the user
        response = client.delete(f"/users/{created_user['id']}")
        assert response.status_code == 204

        # Verify user is gone
        get_response = client.get(f"/users/{created_user['id']}")
        assert get_response.status_code == 404

    def test_delete_user_not_found(self, client: TestClient):
        """Test deleting a non-existent user."""
        user_id = str(uuid4())
        response = client.delete(f"/users/{user_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_list_users_empty(self, client: TestClient):
        """Test listing users when none exist."""
        response = client.get("/users")
        assert response.status_code == 200

        data = response.json()
        assert data["users"] == []
        assert data["total"] == 0
        assert data["offset"] == 0

    def test_list_users(self, client: TestClient):
        """Test listing users."""
        # Create multiple users
        users_data = [
            {"name": "User 1", "email": "user1@example.com"},
            {"name": "User 2", "email": "user2@example.com"},
            {"name": "User 3", "email": "user3@example.com"},
        ]

        for user_data in users_data:
            response = client.post("/users", json=user_data)
            assert response.status_code == 201

        # List users
        response = client.get("/users")
        assert response.status_code == 200

        data = response.json()
        assert len(data["users"]) == 3
        assert data["total"] == 3
        assert data["offset"] == 0

    def test_list_users_with_pagination(self, client: TestClient):
        """Test listing users with pagination."""
        # Create multiple users
        for i in range(5):
            user_data = {"name": f"User {i}", "email": f"user{i}@example.com"}
            response = client.post("/users", json=user_data)
            assert response.status_code == 201

        # Test with limit
        response = client.get("/users?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) == 3
        assert data["total"] == 5
        assert data["limit"] == 3

        # Test with offset
        response = client.get("/users?offset=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) == 2
        assert data["total"] == 5
        assert data["offset"] == 2
        assert data["limit"] == 2

    def test_list_users_active_only(self, client: TestClient):
        """Test listing only active users."""
        # Create users
        user1_data = {"name": "User 1", "email": "user1@example.com"}
        user2_data = {"name": "User 2", "email": "user2@example.com"}

        response1 = client.post("/users", json=user1_data)
        response2 = client.post("/users", json=user2_data)
        assert response1.status_code == 201
        assert response2.status_code == 201

        user2 = response2.json()

        # Deactivate user2
        client.put(f"/users/{user2['id']}", json={"is_active": False})

        # List active users only
        response = client.get("/users?active_only=true")
        assert response.status_code == 200

        data = response.json()
        assert len(data["users"]) == 1
        assert data["total"] == 1
        assert data["users"][0]["name"] == "User 1"

    def test_get_user_count(self, client: TestClient):
        """Test getting user count."""
        # Initially no users
        response = client.get("/users/count")
        assert response.status_code == 200
        assert response.json()["count"] == 0

        # Create a user
        user_data = {"name": "John Doe", "email": "john@example.com"}
        client.post("/users", json=user_data)

        response = client.get("/users/count")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_get_user_count_active_only(self, client: TestClient):
        """Test getting count of active users only."""
        # Create users
        user1_data = {"name": "User 1", "email": "user1@example.com"}
        user2_data = {"name": "User 2", "email": "user2@example.com"}

        client.post("/users", json=user1_data)
        response2 = client.post("/users", json=user2_data)
        user2 = response2.json()

        # All users active
        response = client.get("/users/count?active_only=true")
        assert response.status_code == 200
        assert response.json()["count"] == 2

        # Deactivate one user
        client.put(f"/users/{user2['id']}", json={"is_active": False})

        response = client.get("/users/count?active_only=true")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_clear_users(self, client: TestClient):
        """Test clearing all users."""
        # Create a user
        user_data = {"name": "John Doe", "email": "john@example.com"}
        client.post("/users", json=user_data)

        # Verify user exists
        response = client.get("/users/count")
        assert response.json()["count"] == 1

        # Clear users
        response = client.post("/users/clear")
        assert response.status_code == 204

        # Verify no users
        response = client.get("/users/count")
        assert response.json()["count"] == 0
