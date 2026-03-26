from flask import Blueprint, jsonify, current_app

bp = Blueprint("health", __name__, url_prefix="/api/v1")


@bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "auth_mode": current_app.config["AUTH_MODE"],
    })
