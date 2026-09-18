from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:

    def create(
        self,
        db: Session,
        name: str,
        email: str,
        password_hash: str,
    ) -> User:
        db_user = User(
            name=name,
            email=email.strip().lower(),
            password_hash=password_hash,
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return db_user

    def get_by_email(
        self,
        db: Session,
        email: str,
    ) -> User | None:
        return (
            db.query(User)
            .filter(
                func.lower(User.email)
                == email.strip().lower()
            )
            .first()
        )

    def get_by_id(
        self,
        db: Session,
        user_id: int,
    ) -> User | None:
        return (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )