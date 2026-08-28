import pytest

from backend.app.core.security import verify_password
from backend.app.models.user import UserRole
from backend.app.schemas.user import UserCreate
from backend.app.services.user_service import (
    UserAlreadyExistsError,
    UserService,
)


def test_create_user(session) -> None:
    service = UserService(session)

    data = UserCreate(
        email="john@example.com",
        password="SecurePassword123!",
        first_name="John",
        last_name="Doe",
    )

    user = service.create_user(data)

    assert user.email == "john@example.com"
    assert user.role == UserRole.USER
    assert user.is_active is True

    assert verify_password(
        "SecurePassword123!",
        user.password_hash,
    )


def test_cannot_create_duplicate_email(session) -> None:
    service = UserService(session)

    data = UserCreate(
        email="john@example.com",
        password="SecurePassword123!",
        first_name="John",
        last_name="Doe",
    )

    service.create_user(data)

    with pytest.raises(UserAlreadyExistsError):
        service.create_user(data)