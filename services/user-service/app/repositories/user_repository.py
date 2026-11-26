from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import User
from app.core.constants import UserRole


class UserRepository:
    def get_by_id(self, db: Session, user_id: int) -> Optional[User]:
        return db.get(User, user_id)

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        return db.execute(stmt).scalars().first()

    def create(self, db: Session, user: User) -> User:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update(self, db: Session, user: User, update_data: dict) -> User:
        for field, value in update_data.items():
            if value is not None:
                setattr(user, field, value)
        db.commit()
        db.refresh(user)
        return user

    def list_delivery_agents(self, db: Session, only_active: bool = False) -> List[User]:
        stmt = select(User).where(User.role == UserRole.DELIVERY_AGENT)
        if only_active:
            stmt = stmt.where(User.is_active == True)
        return list(db.execute(stmt).scalars().all())


user_repository = UserRepository()
