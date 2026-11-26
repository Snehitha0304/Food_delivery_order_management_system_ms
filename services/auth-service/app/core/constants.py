from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    RESTAURANT_OWNER = "RESTAURANT_OWNER"
    CUSTOMER = "CUSTOMER"
    DELIVERY_AGENT = "DELIVERY_AGENT"
