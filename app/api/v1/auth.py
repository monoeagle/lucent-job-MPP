from flask import Blueprint, jsonify, request, current_app, g

from app.core.errors import ValidationError, AppError, NotFoundError
from app.services.auth_service import AuthService

bp = Blueprint("auth", __name__, url_prefix="/api/v1")


def _get_auth_service() -> AuthService:
    return AuthService(
        auth_mode=current_app.config["AUTH_MODE"],
        jwt_secret=current_app.config["JWT_SECRET"],
        token_ttl_seconds=current_app.config["STUB_TOKEN_TTL_SECONDS"],
    )


@bp.route("/auth/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username")
    if not username:
        raise ValidationError("username is required")

    password = body.get("password")
    service = _get_auth_service()

    try:
        result = service.login(username, password)
    except AuthService.InvalidCredentialsError:
        raise AppError("INVALID_CREDENTIALS", "invalid credentials", 401)

    response = jsonify(result)
    if current_app.config["AUTH_MODE"] == "stub":
        response.headers["X-Auth-Mode"] = "stub"
    return response


@bp.route("/dev/auth/stub-users", methods=["GET"])
def stub_users():
    if current_app.config["AUTH_MODE"] != "stub":
        raise NotFoundError("Die angeforderte Ressource wurde nicht gefunden.")

    service = _get_auth_service()
    users = service.get_stub_users()
    return jsonify({
        "stub_users": users,
        "static_password": "stub-password",
        "note": "Auth-Stub is active. Never use in production.",
    })
