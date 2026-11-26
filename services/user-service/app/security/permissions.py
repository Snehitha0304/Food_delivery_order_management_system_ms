from app.exceptions import ForbiddenException, NotFoundException


def check_address_ownership(address, user_id: int) -> None:
    if not address:
        raise NotFoundException("Address not found", code="ADDRESS_NOT_FOUND")
    if address.user_id != user_id:
        raise ForbiddenException(
            "You cannot modify another user's address",
            code="ADDRESS_OWNERSHIP_VIOLATION",
        )
