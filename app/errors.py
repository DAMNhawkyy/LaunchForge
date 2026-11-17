"""Our own errors, so any layer can say "stop, show this message"."""


class AppError(Exception):
    def __init__(self, status_code: int, message: str, code: str = "ERROR"):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.code = code


class NotLoggedIn(Exception):
    """Raised when a page needs a signed-in user. Turned into a redirect to /login."""
