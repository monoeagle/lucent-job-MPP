from functools import wraps

from flask import request, g, current_app

from app.core.errors import UnauthorizedError, ForbiddenError
from app.services.auth_service import AuthService


def _get_auth_service() -> AuthService:
    return AuthService(
        auth_mode=current_app.config["AUTH_MODE"],
        jwt_secret=current_app.config["JWT_SECRET"],
        token_ttl_seconds=current_app.config["STUB_TOKEN_TTL_SECONDS"],
    )


def _extract_token() -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise UnauthorizedError("Nicht authentifiziert.")
    return auth_header[7:]


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        service = _get_auth_service()
        try:
            user = service.verify_token(token)
        except AuthService.TokenExpiredError:
            raise UnauthorizedError("Token abgelaufen.")
        except AuthService.InvalidTokenError:
            raise UnauthorizedError("Ungültiger Token.")
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            user = g.current_user
            if not any(user.has_role(r) for r in roles):
                raise ForbiddenError("Keine Berechtigung.")
            return f(*args, **kwargs)
        return decorated
    return decorator
