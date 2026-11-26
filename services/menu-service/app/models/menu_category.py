from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class MenuCategory(Base, TimestampMixin):
    __tablename__ = "menu_categories"

    id = Column(Integer, primary_key=True, index=True)
    # Cross-service reference to restaurant-service (no cross-DB FK constraint)
    restaurant_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    items = relationship("MenuItem", back_populates="category", cascade="all, delete-orphan")
