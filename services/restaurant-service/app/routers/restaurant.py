from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.pagination import PageParams, PaginatedResponse
from app.schemas.restaurant import (
    RestaurantCreate,
    RestaurantUpdate,
    RestaurantOpenStatusUpdate,
    RestaurantResponse,
)
from app.security import AuthenticatedUser, get_current_owner
from app.services.restaurant_service import restaurant_service

router = APIRouter(tags=["Restaurants"])


@router.post("/restaurants", response_model=RestaurantResponse, status_code=status.HTTP_201_CREATED)
def create_restaurant(
    data: RestaurantCreate,
    owner: AuthenticatedUser = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return restaurant_service.create_restaurant(db, owner.id, data)


@router.get("/restaurants/me", response_model=RestaurantResponse)
def get_my_restaurant(
    owner: AuthenticatedUser = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return restaurant_service.get_my_restaurant(db, owner.id)


@router.put("/restaurants/me", response_model=RestaurantResponse)
def update_my_restaurant(
    data: RestaurantUpdate,
    owner: AuthenticatedUser = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return restaurant_service.update_my_restaurant(db, owner.id, data)


@router.patch("/restaurants/me/open-status", response_model=RestaurantResponse)
def set_open_status(
    data: RestaurantOpenStatusUpdate,
    owner: AuthenticatedUser = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return restaurant_service.set_open_status(db, owner.id, data)


@router.get("/restaurants", response_model=PaginatedResponse[RestaurantResponse])
def search_restaurants(
    city: Optional[str] = Query(None),
    cuisine: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    params = PageParams(page=page, size=size)
    return restaurant_service.search_restaurants(db, city=city, cuisine=cuisine, name=name, params=params)


@router.get("/restaurants/{id}", response_model=RestaurantResponse)
def get_restaurant_by_id(id: int, db: Session = Depends(get_db)):
    return restaurant_service.get_restaurant_by_id(db, id)
