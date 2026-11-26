from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.menu_category import MenuCategory
from app.models.menu_item import MenuItem


class MenuRepository:
    def create_category(self, db: Session, category: MenuCategory) -> MenuCategory:
        db.add(category)
        db.commit()
        db.refresh(category)
        return category

    def get_category_by_id(self, db: Session, category_id: int) -> Optional[MenuCategory]:
        return db.get(MenuCategory, category_id)

    def get_categories_by_restaurant(self, db: Session, restaurant_id: int) -> List[MenuCategory]:
        stmt = (
            select(MenuCategory)
            .where(MenuCategory.restaurant_id == restaurant_id)
            .order_by(MenuCategory.display_order.asc(), MenuCategory.id.asc())
        )
        return list(db.execute(stmt).scalars().all())

    def update_category(self, db: Session, category: MenuCategory, update_data: dict) -> MenuCategory:
        for field, value in update_data.items():
            if value is not None:
                setattr(category, field, value)
        db.commit()
        db.refresh(category)
        return category

    def delete_category(self, db: Session, category: MenuCategory) -> None:
        db.delete(category)
        db.commit()

    def create_item(self, db: Session, item: MenuItem) -> MenuItem:
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def get_item_by_id(self, db: Session, item_id: int) -> Optional[MenuItem]:
        return db.get(MenuItem, item_id)

    def get_items_by_ids(self, db: Session, item_ids: List[int]) -> List[MenuItem]:
        stmt = select(MenuItem).where(MenuItem.id.in_(item_ids))
        return list(db.execute(stmt).scalars().all())

    def get_items_by_restaurant(
        self,
        db: Session,
        restaurant_id: int,
        include_deleted: bool = False,
    ) -> List[MenuItem]:
        stmt = select(MenuItem).where(MenuItem.restaurant_id == restaurant_id)
        if not include_deleted:
            stmt = stmt.where(MenuItem.is_deleted == False)
        return list(db.execute(stmt).scalars().all())

    def update_item(self, db: Session, item: MenuItem, update_data: dict) -> MenuItem:
        for field, value in update_data.items():
            if value is not None:
                setattr(item, field, value)
        db.commit()
        db.refresh(item)
        return item

    def soft_delete_item(self, db: Session, item: MenuItem) -> MenuItem:
        item.is_deleted = True
        item.is_available = False
        db.commit()
        db.refresh(item)
        return item


menu_repository = MenuRepository()
