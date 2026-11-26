import logging
from typing import List
from sqlalchemy.orm import Session

from app.exceptions import ConflictException, NotFoundException
from app.models.address import Address
from app.models.user import User
from app.repositories.address_repository import address_repository
from app.repositories.user_repository import user_repository
from app.schemas.address import AddressCreate, AddressResponse
from app.schemas.customer import CustomerProfileUpdate
from app.schemas.user import InternalUserCreate, UserResponse
from app.security.permissions import check_address_ownership

logger = logging.getLogger("user-service.audit")


class CustomerService:
    def create_user_profile(self, db: Session, data: InternalUserCreate) -> UserResponse:
        existing = user_repository.get_by_email(db, data.email)
        if existing:
            raise ConflictException(
                f"User profile with email '{data.email}' already exists",
                code="EMAIL_ALREADY_EXISTS",
            )
        user_kwargs = {
            "email": data.email,
            "full_name": data.full_name,
            "phone": data.phone,
            "role": data.role,
            "is_active": data.is_active,
        }
        if data.id is not None:
            user_kwargs["id"] = data.id
        created = user_repository.create(db, User(**user_kwargs))
        logger.info(f"AUDIT: User profile created ID={created.id} email={created.email}")
        return UserResponse.model_validate(created)

    def get_profile(self, db: Session, user_id: int) -> UserResponse:
        user = user_repository.get_by_id(db, user_id)
        if not user:
            raise NotFoundException("User not found", code="USER_NOT_FOUND")
        return UserResponse.model_validate(user)

    def update_profile(self, db: Session, user_id: int, data: CustomerProfileUpdate) -> UserResponse:
        user = user_repository.get_by_id(db, user_id)
        if not user:
            raise NotFoundException("User not found", code="USER_NOT_FOUND")

        update_dict = data.model_dump(exclude_unset=True)
        updated = user_repository.update(db, user, update_dict)
        logger.info(f"AUDIT: Customer {user_id} updated profile")
        return UserResponse.model_validate(updated)

    def get_addresses(self, db: Session, user_id: int) -> List[AddressResponse]:
        addresses = address_repository.get_by_user_id(db, user_id)
        return [AddressResponse.model_validate(a) for a in addresses]

    def create_address(self, db: Session, user_id: int, data: AddressCreate) -> AddressResponse:
        if data.is_default:
            address_repository.clear_default_for_user(db, user_id)

        address = Address(
            user_id=user_id,
            line1=data.line1,
            line2=data.line2,
            city=data.city,
            pincode=data.pincode,
            is_default=data.is_default,
        )
        created = address_repository.create(db, address)
        logger.info(f"AUDIT: Customer {user_id} created address ID={created.id}")
        return AddressResponse.model_validate(created)

    def set_default_address(self, db: Session, user_id: int, address_id: int) -> AddressResponse:
        address = address_repository.get_by_id(db, address_id)
        check_address_ownership(address, user_id)

        address_repository.clear_default_for_user(db, user_id)
        updated = address_repository.update(db, address, {"is_default": True})
        logger.info(f"AUDIT: Customer {user_id} set address {address_id} as default")
        return AddressResponse.model_validate(updated)

    def delete_address(self, db: Session, user_id: int, address_id: int) -> None:
        address = address_repository.get_by_id(db, address_id)
        check_address_ownership(address, user_id)

        address_repository.delete(db, address)
        logger.info(f"AUDIT: Customer {user_id} deleted address {address_id}")

    def get_address_by_id(self, db: Session, address_id: int) -> AddressResponse:
        address = address_repository.get_by_id(db, address_id)
        if not address:
            raise NotFoundException("Address not found", code="ADDRESS_NOT_FOUND")
        return AddressResponse.model_validate(address)

    def list_delivery_agents(self, db: Session) -> List[UserResponse]:
        agents = user_repository.list_delivery_agents(db, only_active=False)
        return [UserResponse.model_validate(a) for a in agents]


customer_service = CustomerService()
