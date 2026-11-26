from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.address import AddressResponse
from app.schemas.user import InternalUserCreate, UserResponse
from app.security import verify_internal_api_key
from app.services.customer_service import customer_service

router = APIRouter(
    prefix="/internal",
    tags=["Internal Service API"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def internal_create_user(data: InternalUserCreate, db: Session = Depends(get_db)):
    return customer_service.create_user_profile(db, data)


@router.get("/users/agents", response_model=List[UserResponse])
def internal_list_delivery_agents(db: Session = Depends(get_db)):
    return customer_service.list_delivery_agents(db)


@router.get("/users/{user_id}", response_model=UserResponse)
def internal_get_user(user_id: int, db: Session = Depends(get_db)):
    return customer_service.get_profile(db, user_id)


@router.get("/addresses/{address_id}", response_model=AddressResponse)
def internal_get_address(address_id: int, db: Session = Depends(get_db)):
    return customer_service.get_address_by_id(db, address_id)
