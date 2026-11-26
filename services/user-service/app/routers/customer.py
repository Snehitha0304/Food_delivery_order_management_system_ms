from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.address import AddressCreate, AddressResponse
from app.schemas.customer import CustomerProfileUpdate
from app.schemas.user import UserResponse
from app.security import AuthenticatedUser, get_current_customer
from app.services.customer_service import customer_service

router = APIRouter(tags=["Customer"])


@router.get("/customer/profile", response_model=UserResponse, summary="View customer profile")
def get_customer_profile(
    customer: AuthenticatedUser = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    return customer_service.get_profile(db, customer.id)


@router.put("/customer/profile", response_model=UserResponse, summary="Update customer profile")
def update_customer_profile(
    data: CustomerProfileUpdate,
    customer: AuthenticatedUser = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    return customer_service.update_profile(db, customer.id, data)


@router.get("/addresses", response_model=List[AddressResponse], summary="List delivery addresses")
def get_addresses(
    customer: AuthenticatedUser = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    return customer_service.get_addresses(db, customer.id)


@router.post(
    "/addresses",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add delivery address",
)
def create_address(
    data: AddressCreate,
    customer: AuthenticatedUser = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    return customer_service.create_address(db, customer.id, data)


@router.put(
    "/addresses/{id}/default",
    response_model=AddressResponse,
    summary="Mark address as default",
)
def set_default_address(
    id: int,
    customer: AuthenticatedUser = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    return customer_service.set_default_address(db, customer.id, id)


@router.delete(
    "/addresses/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete delivery address",
)
def delete_address(
    id: int,
    customer: AuthenticatedUser = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    customer_service.delete_address(db, customer.id, id)
    return None
