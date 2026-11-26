from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.restaurant import RestaurantRatingUpdate, RestaurantResponse
from app.security import verify_internal_api_key
from app.services.restaurant_service import restaurant_service

router = APIRouter(
    prefix="/internal",
    tags=["Internal Service API"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.get("/restaurants/by-owner/{owner_id}", response_model=RestaurantResponse)
def internal_get_restaurant_by_owner(owner_id: int, db: Session = Depends(get_db)):
    return restaurant_service.get_my_restaurant(db, owner_id)


@router.get("/restaurants/{restaurant_id}", response_model=RestaurantResponse)
def internal_get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    return restaurant_service.get_restaurant_by_id(db, restaurant_id)


@router.patch("/restaurants/{restaurant_id}/rating", response_model=RestaurantResponse)
def internal_update_restaurant_rating(
    restaurant_id: int,
    data: RestaurantRatingUpdate,
    db: Session = Depends(get_db),
):
    return restaurant_service.update_avg_rating(db, restaurant_id, data.avg_rating)
