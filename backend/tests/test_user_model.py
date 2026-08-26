from sqlalchemy import select

from backend.app.core.database import SessionLocal
from backend.app.core.security import hash_password
from backend.app.models.user import User, UserRole


def test_create_user() -> None:
    with SessionLocal() as session:
        user = User(
            email="test@nexus.local",
            password_hash=hash_password("TestPassword123!"),
            first_name="Test",
            last_name="User",
            role=UserRole.USER,
        )

        session.add(user)
        session.commit()
        session.refresh(user)

        assert user.id is not None
        assert user.email == "test@nexus.local"
        assert user.is_active is True