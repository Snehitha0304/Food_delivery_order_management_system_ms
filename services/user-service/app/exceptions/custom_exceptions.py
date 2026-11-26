from typing import Any, Optional


class AppException(Exception):
    def __init__(
        self,
        status_code: int = 400,
        detail: str = "An error occurred",
        code: str = "BAD_REQUEST",
        data: Optional[Any] = None,
    ):
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.data = data
        super().__init__(detail)


class BadRequestException(AppException):
    def __init__(self, detail: str = "Bad request", code: str = "BAD_REQUEST"):
        super().__init__(status_code=400, detail=detail, code=code)


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Could not validate credentials", code: str = "UNAUTHORIZED"):
        super().__init__(status_code=401, detail=detail, code=code)


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Operation not permitted", code: str = "FORBIDDEN"):
        super().__init__(status_code=403, detail=detail, code=code)


class NotFoundException(AppException):
    def __init__(self, detail: str = "Resource not found", code: str = "NOT_FOUND"):
        super().__init__(status_code=404, detail=detail, code=code)


class ConflictException(AppException):
    def __init__(self, detail: str = "Resource conflict or invalid state transition", code: str = "CONFLICT"):
        super().__init__(status_code=409, detail=detail, code=code)


class ValidationException(AppException):
    def __init__(self, detail: str = "Validation failed", code: str = "VALIDATION_ERROR"):
        super().__init__(status_code=422, detail=detail, code=code)


class ServiceUnavailableException(AppException):
    def __init__(self, detail: str = "Downstream service unavailable", code: str = "SERVICE_UNAVAILABLE"):
        super().__init__(status_code=503, detail=detail, code=code)
