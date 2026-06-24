from fastapi import HTTPException

class PoliceOSINTException(HTTPException):
    def __init__(self, status_code: int, detail: str, error_code: str):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code

class NotFoundError(PoliceOSINTException):
    def __init__(self, resource: str, id: str = ""):
        super().__init__(404, f"{resource} not found" + (f": {id}" if id else ""), "NOT_FOUND")

class UnauthorizedError(PoliceOSINTException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(401, detail, "UNAUTHORIZED")

class ForbiddenError(PoliceOSINTException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(403, detail, "FORBIDDEN")

class ConflictError(PoliceOSINTException):
    def __init__(self, detail: str):
        super().__init__(409, detail, "CONFLICT")
