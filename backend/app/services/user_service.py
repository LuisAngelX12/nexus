from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.jwt import create_access_token
from backend.app.core.security import hash_password, verify_password
from backend.app.models.user import User
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.user import UserCreate


class UserAlreadyExistsError(Exception):
    pass


class UserService:
    def __init__(self, session: Session) -> None:
        self.repository = UserRepository(session)

    def authenticate_user(
        self,
        email: str,
        password: str,
    ) -> str | None:
        normalized_email = email.strip().lower()

        user = self.repository.get_by_email(normalized_email)

        if user is None:
            return None

        if not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            return None

        return create_access_token(user.id)

    def create_user(self, data: UserCreate) -> User:
        normalized_email = data.email.strip().lower()

        existing_user = self.repository.get_by_email(normalized_email)

        if existing_user is not None:
            raise UserAlreadyExistsError("A user with this email already exists.")

        user = User(
            email=normalized_email,
            password_hash=hash_password(data.password),
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
        )

        try:
            return self.repository.create(user)
        except IntegrityError as exc:
            raise UserAlreadyExistsError("A user with this email already exists.") from exc
