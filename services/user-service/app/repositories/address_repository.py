from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from app.models.address import Address


class AddressRepository:
    def create(self, db: Session, address: Address) -> Address:
        db.add(address)
        db.commit()
        db.refresh(address)
        return address

    def get_by_id(self, db: Session, address_id: int) -> Optional[Address]:
        return db.get(Address, address_id)

    def get_by_user_id(self, db: Session, user_id: int) -> List[Address]:
        stmt = (
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(Address.is_default.desc(), Address.id.desc())
        )
        return list(db.execute(stmt).scalars().all())

    def update(self, db: Session, address: Address, update_data: dict) -> Address:
        for field, value in update_data.items():
            if value is not None:
                setattr(address, field, value)
        db.commit()
        db.refresh(address)
        return address

    def delete(self, db: Session, address: Address) -> None:
        db.delete(address)
        db.commit()

    def clear_default_for_user(self, db: Session, user_id: int) -> None:
        stmt = update(Address).where(Address.user_id == user_id).values(is_default=False)
        db.execute(stmt)
        db.commit()


address_repository = AddressRepository()
