from flask import Blueprint, jsonify, current_app, g
from sqlalchemy import text

bp = Blueprint("health", __name__, url_prefix="/api/v1")


@bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "auth_mode": current_app.config["AUTH_MODE"],
    })


@bp.route("/ready", methods=["GET"])
def readiness_check():
    """Liveness + DB-Erreichbarkeit. 503, wenn die Datenbank nicht antwortet."""
    try:
        g.db_session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "error"

    if database == "ok":
        return jsonify({"status": "ready", "database": database}), 200
    return jsonify({"status": "unavailable", "database": database}), 503
