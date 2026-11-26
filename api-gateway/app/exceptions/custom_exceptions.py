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


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Unauthorized", code: str = "UNAUTHORIZED"):
        super().__init__(status_code=401, detail=detail, code=code)


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Forbidden", code: str = "FORBIDDEN"):
        super().__init__(status_code=403, detail=detail, code=code)


class NotFoundException(AppException):
    def __init__(self, detail: str = "Route not found", code: str = "NOT_FOUND"):
        super().__init__(status_code=404, detail=detail, code=code)


class ServiceUnavailableException(AppException):
    def __init__(self, detail: str = "Downstream service unavailable", code: str = "SERVICE_UNAVAILABLE"):
        super().__init__(status_code=503, detail=detail, code=code)
