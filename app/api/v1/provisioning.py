# app/api/v1/provisioning.py
from flask import Blueprint, jsonify, request, g, current_app

from app.core.auth import role_required
from app.data.repositories.dispatch_log_repository import DispatchLogRepository
from app.data.repositories.order_repository import OrderRepository
from app.services.provisioning_service import ProvisioningService
from app.services.credential_service import CredentialService

bp = Blueprint("provisioning", __name__, url_prefix="/api/v1")
admin_bp = Blueprint("provisioning_admin", __name__, url_prefix="/api/v1/admin")


def _get_provisioning_service() -> ProvisioningService:
    order_repo = OrderRepository(g.db_session)
    dispatch_log_repo = DispatchLogRepository(g.db_session)
    gitlab_client = getattr(current_app, "gitlab_client", None)
    return ProvisioningService(order_repo, dispatch_log_repo, gitlab_client)


def _serialize_log(log) -> dict:
    return {
        "id": log.id,
        "order_id": log.order_id,
        "order_item_id": log.order_item_id,
        "job_id": log.job_id,
        "dispatch_method": log.dispatch_method,
        "dispatched_at": log.dispatched_at.isoformat() if log.dispatched_at else None,
        "attempt_count": log.attempt_count,
        "status": log.status,
        "error_message": log.error_message,
    }


# ── Webhook (no auth) ────────────────────────────────────────

@bp.route("/webhooks/gitlab", methods=["POST"])
def gitlab_webhook():
    data = request.get_json(silent=True) or {}
    obj = data.get("object_attributes", {})
    pipeline_id = obj.get("id")
    status = obj.get("status")

    if pipeline_id and status:
        try:
            service = _get_provisioning_service()
            service.handle_webhook(pipeline_id, status)
        except Exception:
            pass  # Webhook must always return 200

    return jsonify({"received": True}), 200


# ── Admin endpoints ──────────────────────────────────────────

@admin_bp.route("/dispatcher/config", methods=["GET"])
@role_required("admin")
def get_dispatcher_config():
    return jsonify({
        "dispatch_method": "gitlab_pipeline",
        "gitlab_project_id": current_app.config.get("GITLAB_PROJECT_ID", ""),
        "gitlab_url": current_app.config.get("GITLAB_URL", ""),
    }), 200


@admin_bp.route("/orders/<order_id>/dispatch-log", methods=["GET"])
@role_required("admin")
def get_dispatch_log(order_id):
    repo = DispatchLogRepository(g.db_session)
    logs = repo.get_logs_for_order(order_id)
    return jsonify([_serialize_log(log) for log in logs]), 200


@admin_bp.route("/orders/<order_id>/items/<item_id>/dispatch", methods=["POST"])
@role_required("admin")
def dispatch_item(order_id, item_id):
    service = _get_provisioning_service()
    service.dispatch_item(order_id, item_id)
    return jsonify({"message": "Dispatch initiated."}), 202


@admin_bp.route("/orders/<order_id>/items/<item_id>/credentials", methods=["POST"])
@role_required("admin")
def create_credential_link(order_id, item_id):
    data = request.get_json(silent=True) or {}
    credentials = data.get("credentials")
    if not credentials:
        return jsonify({"error": "credentials required"}), 400

    service = CredentialService(g.db_session)
    model, token = service.create_link(item_id, credentials)
    return jsonify({
        "token": token,
        "url": f"/api/v1/credentials/{token}",
        "expires_at": model.expires_at.isoformat(),
    }), 201


@bp.route("/credentials/<token>", methods=["GET"])
def retrieve_credentials(token):
    service = CredentialService(g.db_session)
    try:
        result = service.retrieve_credentials(token)
        return jsonify(result), 200
    except service.LinkNotFoundError:
        return jsonify({"error": "Credential link not found."}), 404
    except (service.LinkExpiredError, service.LinkConsumedError):
        return jsonify({"error": "Credential link is no longer available."}), 410
