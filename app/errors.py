class AuthError(Exception):
    def __init__(self, status_code: int, error: str, message: str):
        self.status_code = status_code
        self.error = error
        self.message = message
        super().__init__(message)

    def to_dict(self) -> dict:
        return {"ok": False, "error": self.error, "message": self.message}
