from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.menu import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    MenuItemCreate,
    MenuItemUpdate,
    MenuItemAvailabilityUpdate,
    MenuItemResponse,
    RestaurantMenuResponse,
)
from app.security import AuthenticatedUser, get_current_owner
from app.services.menu_service import menu_service

router = APIRouter(tags=["Menu"])


@router.get("/restaurants/{id}/menu", response_model=RestaurantMenuResponse)
def get_restaurant_menu(id: int, db: Session = Depends(get_db)):
    return menu_service.get_restaurant_menu_grouped(db, id)


@router.post("/restaurants/me/menu-categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate,
    owner: AuthenticatedUser = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return menu_service.create_category(db, owner.id, data)


@router.get("/restaurants/me/menu-categories", response_model=list[CategoryResponse])
def get_categories(
    owner: AuthenticatedUser = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return menu_service.get_categories(db, owner.id)


@router.put("/restaurants/me/menu-categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    owner: AuthenticatedUser = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return menu_service.update_category(db, owner.id, category_id, data)


@router.delete("/restaurants/me/menu-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    owner: AuthenticatedUser = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    menu_service.delete_category(db, owner.id, category_id)
    return None


@router.post("/restaurants/me/menu-items", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
def create_menu_item(
    data: MenuItemCreate,
    owner: AuthenticatedUser = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return menu_service.create_menu_item(db, owner.id, data)


@router.put("/menu-items/{id}", response_model=MenuItemResponse)
def update_menu_item(
    id: int,
    data: MenuItemUpdate,
    owner: AuthenticatedUser = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return menu_service.update_menu_item(db, owner.id, id, data)


@router.delete("/menu-items/{id}", response_model=MenuItemResponse)
def soft_delete_menu_item(
    id: int,
    owner: AuthenticatedUser = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return menu_service.soft_delete_menu_item(db, owner.id, id)


@router.patch("/menu-items/{id}/availability", response_model=MenuItemResponse)
def toggle_availability(
    id: int,
    data: MenuItemAvailabilityUpdate,
    owner: AuthenticatedUser = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return menu_service.toggle_item_availability(db, owner.id, id, data)
