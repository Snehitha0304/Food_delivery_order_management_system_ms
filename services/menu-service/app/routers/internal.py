from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.menu import MenuItemBatchRequest, MenuItemResponse
from app.security import verify_internal_api_key
from app.services.menu_service import menu_service

router = APIRouter(
    prefix="/internal",
    tags=["Internal Service API"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.post("/menu-items/batch", response_model=List[MenuItemResponse])
def internal_get_menu_items_batch(data: MenuItemBatchRequest, db: Session = Depends(get_db)):
    return menu_service.get_items_by_ids(db, data.item_ids)


@router.get("/menu-items/{item_id}", response_model=MenuItemResponse)
def internal_get_menu_item(item_id: int, db: Session = Depends(get_db)):
    return menu_service.get_item_by_id(db, item_id)
