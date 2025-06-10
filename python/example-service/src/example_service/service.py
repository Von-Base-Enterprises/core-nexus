"""
User service implementation for the example service.
"""

from uuid import UUID

from .models import CreateUserRequest, UpdateUserRequest, User


class UserNotFoundError(Exception):
    """Raised when a user is not found."""
    pass


class DuplicateEmailError(Exception):
    """Raised when trying to create a user with a duplicate email."""
    pass


class UserService:
    """In-memory user service for demonstration purposes."""

    def __init__(self) -> None:
        """Initialize the service."""
        self._users: dict[UUID, User] = {}

    async def create_user(self, request: CreateUserRequest) -> User:
        """
        Create a new user.

        Args:
            request: The user creation request

        Returns:
            The created user

        Raises:
            DuplicateEmailError: If a user with the email already exists
        """
        # Check for duplicate email
        for user in self._users.values():
            if user.email == request.email:
                raise DuplicateEmailError(f"User with email {request.email} already exists")

        user = User(
            name=request.name,
            email=request.email
        )

        self._users[user.id] = user
        return user

    async def get_user(self, user_id: UUID) -> User:
        """
        Get a user by ID.

        Args:
            user_id: The user ID

        Returns:
            The user

        Raises:
            UserNotFoundError: If the user is not found
        """
        user = self._users.get(user_id)
        if not user:
            raise UserNotFoundError(f"User with ID {user_id} not found")
        return user

    async def update_user(self, user_id: UUID, request: UpdateUserRequest) -> User:
        """
        Update a user.

        Args:
            user_id: The user ID
            request: The update request

        Returns:
            The updated user

        Raises:
            UserNotFoundError: If the user is not found
            DuplicateEmailError: If trying to update to a duplicate email
        """
        user = await self.get_user(user_id)

        # Check for duplicate email if email is being updated
        if request.email and request.email != user.email:
            for existing_user in self._users.values():
                if existing_user.email == request.email and existing_user.id != user_id:
                    raise DuplicateEmailError(f"User with email {request.email} already exists")

        # Update fields
        update_data = request.dict(exclude_unset=True)
        updated_user = user.copy(update=update_data)

        self._users[user_id] = updated_user
        return updated_user

    async def delete_user(self, user_id: UUID) -> bool:
        """
        Delete a user.

        Args:
            user_id: The user ID

        Returns:
            True if the user was deleted, False if not found
        """
        return self._users.pop(user_id, None) is not None

    async def list_users(
        self,
        limit: int | None = None,
        offset: int = 0,
        active_only: bool = False
    ) -> tuple[list[User], int]:
        """
        List users with pagination.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            active_only: Whether to return only active users

        Returns:
            A tuple of (users, total_count)
        """
        users = list(self._users.values())

        # Filter by active status if requested
        if active_only:
            users = [user for user in users if user.is_active]

        # Sort by creation date
        users.sort(key=lambda u: u.created_at)

        total = len(users)

        # Apply pagination
        if offset > 0:
            users = users[offset:]

        if limit is not None:
            users = users[:limit]

        return users, total

    async def get_user_count(self, active_only: bool = False) -> int:
        """
        Get the total number of users.

        Args:
            active_only: Whether to count only active users

        Returns:
            The user count
        """
        if not active_only:
            return len(self._users)

        return sum(1 for user in self._users.values() if user.is_active)

    async def clear_all_users(self) -> None:
        """Clear all users (useful for testing)."""
        self._users.clear()

    async def user_exists(self, user_id: UUID) -> bool:
        """
        Check if a user exists.

        Args:
            user_id: The user ID

        Returns:
            True if the user exists, False otherwise
        """
        return user_id in self._users
