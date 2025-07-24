"""
Tests for the UserService class.
"""

from uuid import uuid4

import pytest
from example_service.models import CreateUserRequest, UpdateUserRequest
from example_service.service import DuplicateEmailError, UserNotFoundError, UserService


@pytest.fixture
async def service() -> UserService:
    """Create a fresh UserService instance for each test."""
    service = UserService()
    await service.clear_all_users()
    return service


@pytest.fixture
def create_user_request() -> CreateUserRequest:
    """Create a sample user creation request."""
    return CreateUserRequest(
        name="John Doe",
        email="john@example.com"
    )


class TestUserService:
    """Tests for UserService class."""

    async def test_create_user(self, service: UserService, create_user_request: CreateUserRequest):
        """Test creating a user."""
        user = await service.create_user(create_user_request)

        assert user.name == "John Doe"
        assert user.email == "john@example.com"
        assert user.is_active is True
        assert user.id is not None
        assert user.created_at is not None

    async def test_create_user_duplicate_email(self, service: UserService, create_user_request: CreateUserRequest):
        """Test creating a user with duplicate email raises error."""
        await service.create_user(create_user_request)

        with pytest.raises(DuplicateEmailError, match="User with email john@example.com already exists"):
            await service.create_user(create_user_request)

    async def test_get_user(self, service: UserService, create_user_request: CreateUserRequest):
        """Test getting a user by ID."""
        created_user = await service.create_user(create_user_request)
        retrieved_user = await service.get_user(created_user.id)

        assert retrieved_user == created_user

    async def test_get_user_not_found(self, service: UserService):
        """Test getting a non-existent user raises error."""
        user_id = uuid4()

        with pytest.raises(UserNotFoundError, match=f"User with ID {user_id} not found"):
            await service.get_user(user_id)

    async def test_update_user(self, service: UserService, create_user_request: CreateUserRequest):
        """Test updating a user."""
        user = await service.create_user(create_user_request)

        update_request = UpdateUserRequest(
            name="Jane Doe",
            is_active=False
        )

        updated_user = await service.update_user(user.id, update_request)

        assert updated_user.name == "Jane Doe"
        assert updated_user.email == "john@example.com"  # unchanged
        assert updated_user.is_active is False
        assert updated_user.id == user.id
        assert updated_user.created_at == user.created_at

    async def test_update_user_not_found(self, service: UserService):
        """Test updating a non-existent user raises error."""
        user_id = uuid4()
        update_request = UpdateUserRequest(name="Jane Doe")

        with pytest.raises(UserNotFoundError, match=f"User with ID {user_id} not found"):
            await service.update_user(user_id, update_request)

    async def test_update_user_duplicate_email(self, service: UserService):
        """Test updating a user with duplicate email raises error."""
        user1 = await service.create_user(CreateUserRequest(name="User 1", email="user1@example.com"))
        user2 = await service.create_user(CreateUserRequest(name="User 2", email="user2@example.com"))

        update_request = UpdateUserRequest(email="user1@example.com")

        with pytest.raises(DuplicateEmailError, match="User with email user1@example.com already exists"):
            await service.update_user(user2.id, update_request)

    async def test_delete_user(self, service: UserService, create_user_request: CreateUserRequest):
        """Test deleting a user."""
        user = await service.create_user(create_user_request)

        deleted = await service.delete_user(user.id)
        assert deleted is True

        # Verify user is gone
        with pytest.raises(UserNotFoundError):
            await service.get_user(user.id)

    async def test_delete_user_not_found(self, service: UserService):
        """Test deleting a non-existent user returns False."""
        user_id = uuid4()
        deleted = await service.delete_user(user_id)
        assert deleted is False

    async def test_list_users_empty(self, service: UserService):
        """Test listing users when none exist."""
        users, total = await service.list_users()
        assert users == []
        assert total == 0

    async def test_list_users(self, service: UserService):
        """Test listing users."""
        # Create multiple users
        user1 = await service.create_user(CreateUserRequest(name="User 1", email="user1@example.com"))
        user2 = await service.create_user(CreateUserRequest(name="User 2", email="user2@example.com"))
        user3 = await service.create_user(CreateUserRequest(name="User 3", email="user3@example.com"))

        users, total = await service.list_users()

        assert len(users) == 3
        assert total == 3

        # Should be sorted by creation date
        assert users[0].created_at <= users[1].created_at <= users[2].created_at

    async def test_list_users_with_pagination(self, service: UserService):
        """Test listing users with pagination."""
        # Create multiple users
        for i in range(5):
            await service.create_user(CreateUserRequest(name=f"User {i}", email=f"user{i}@example.com"))

        # Test limit
        users, total = await service.list_users(limit=3)
        assert len(users) == 3
        assert total == 5

        # Test offset
        users, total = await service.list_users(offset=2, limit=2)
        assert len(users) == 2
        assert total == 5

    async def test_list_users_active_only(self, service: UserService):
        """Test listing only active users."""
        user1 = await service.create_user(CreateUserRequest(name="User 1", email="user1@example.com"))
        user2 = await service.create_user(CreateUserRequest(name="User 2", email="user2@example.com"))

        # Deactivate one user
        await service.update_user(user2.id, UpdateUserRequest(is_active=False))

        users, total = await service.list_users(active_only=True)
        assert len(users) == 1
        assert total == 1
        assert users[0].id == user1.id

    async def test_get_user_count(self, service: UserService):
        """Test getting user count."""
        assert await service.get_user_count() == 0

        await service.create_user(CreateUserRequest(name="User 1", email="user1@example.com"))
        assert await service.get_user_count() == 1

        await service.create_user(CreateUserRequest(name="User 2", email="user2@example.com"))
        assert await service.get_user_count() == 2

    async def test_get_user_count_active_only(self, service: UserService):
        """Test getting count of active users only."""
        user1 = await service.create_user(CreateUserRequest(name="User 1", email="user1@example.com"))
        user2 = await service.create_user(CreateUserRequest(name="User 2", email="user2@example.com"))

        assert await service.get_user_count() == 2
        assert await service.get_user_count(active_only=True) == 2

        # Deactivate one user
        await service.update_user(user2.id, UpdateUserRequest(is_active=False))

        assert await service.get_user_count() == 2
        assert await service.get_user_count(active_only=True) == 1

    async def test_user_exists(self, service: UserService, create_user_request: CreateUserRequest):
        """Test checking if user exists."""
        user_id = uuid4()
        assert await service.user_exists(user_id) is False

        user = await service.create_user(create_user_request)
        assert await service.user_exists(user.id) is True

        await service.delete_user(user.id)
        assert await service.user_exists(user.id) is False

    async def test_clear_all_users(self, service: UserService):
        """Test clearing all users."""
        # Create some users
        await service.create_user(CreateUserRequest(name="User 1", email="user1@example.com"))
        await service.create_user(CreateUserRequest(name="User 2", email="user2@example.com"))

        assert await service.get_user_count() == 2

        await service.clear_all_users()
        assert await service.get_user_count() == 0
