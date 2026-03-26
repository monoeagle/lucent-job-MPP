from flask import jsonify, request


class AppError(Exception):
    def __init__(self, error_code: str, message: str, status_code: int = 400,
                 details: dict | None = None):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ValidationError(AppError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("VALIDATION_FAILED", message, 400, details)


class NotFoundError(AppError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("NOT_FOUND", message, 404, details)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Nicht authentifiziert."):
        super().__init__("UNAUTHORIZED", message, 401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Keine Berechtigung."):
        super().__init__("FORBIDDEN", message, 403)


class ConflictError(AppError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("CONFLICT", message, 409, details)


def _error_response(error_code: str, message: str, status_code: int,
                    details: dict | None = None):
    request_id = getattr(request, "request_id", "unknown")
    body = {
        "error_code": error_code,
        "message": message,
        "details": details,
        "request_id": request_id,
    }
    return jsonify(body), status_code


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        return _error_response(
            error.error_code, error.message, error.status_code, error.details
        )

    @app.errorhandler(404)
    def handle_404(error):
        return _error_response("NOT_FOUND", "Die angeforderte Ressource wurde nicht gefunden.", 404)

    @app.errorhandler(405)
    def handle_405(error):
        return _error_response("METHOD_NOT_ALLOWED", "Diese HTTP-Methode ist nicht erlaubt.", 405)

    @app.errorhandler(500)
    def handle_500(error):
        app.logger.error("Unhandled error: %s", error, exc_info=True)
        return _error_response(
            "INTERNAL_ERROR", "Ein interner Serverfehler ist aufgetreten.", 500
        )
