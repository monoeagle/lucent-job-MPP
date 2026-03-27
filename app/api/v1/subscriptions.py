from flask import Blueprint, jsonify, request, g

from app.core.auth import login_required, role_required
from app.core.errors import NotFoundError, ForbiddenError, ConflictError
from app.data.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import SubscriptionService

bp = Blueprint("subscriptions", __name__, url_prefix="/api/v1")
admin_bp = Blueprint("subscriptions_admin", __name__, url_prefix="/api/v1/admin")


def _get_service() -> SubscriptionService:
    repo = SubscriptionRepository(g.db_session)
    return SubscriptionService(repo)


def _get_repo() -> SubscriptionRepository:
    return SubscriptionRepository(g.db_session)


def _serialize(sub) -> dict:
    return {
        "id": sub.id,
        "order_item_id": sub.order_item_id,
        "group_subscription_id": sub.group_subscription_id,
        "requester_id": sub.requester_id,
        "status": sub.status,
        "display_name": sub.display_name,
        "template_slug": sub.template_slug,
        "template_version": sub.template_version,
        "parameters": sub.parameters,
        "pending_changes": sub.pending_changes,
        "monthly_cost_eur": str(sub.monthly_cost_eur) if sub.monthly_cost_eur is not None else None,
        "activated_at": sub.activated_at.isoformat() if sub.activated_at else None,
        "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
        "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
    }


def _serialize_group(group) -> dict:
    return {
        "id": group.id,
        "order_item_group_id": group.order_item_group_id,
        "name": group.name,
        "requester_id": group.requester_id,
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None,
        "subscriptions": [_serialize(s) for s in group.subscriptions],
    }


# ── User endpoints ────────────────────────────────────────────────────────────

@bp.route("/subscriptions", methods=["GET"])
@login_required
def list_subscriptions():
    repo = _get_repo()
    user = g.current_user
    status = request.args.get("status")
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)

    requester_id = None if user.is_admin else user.username
    result = repo.list_subscriptions(
        requester_id=requester_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return jsonify({
        "items": [_serialize(s) for s in result["items"]],
        "total": result["total"],
        "limit": result["limit"],
        "offset": result["offset"],
    }), 200


# NOTE: /subscriptions/groups must be registered BEFORE /subscriptions/<subscription_id>
# so Flask does not match "groups" as a subscription ID.

@bp.route("/subscriptions/groups", methods=["GET"])
@login_required
def list_groups():
    from app.data.db.models.subscription import GroupSubscriptionModel
    user = g.current_user
    requester_id = None if user.is_admin else user.username

    q = g.db_session.query(GroupSubscriptionModel)
    if requester_id:
        q = q.filter_by(requester_id=requester_id)
    groups = q.order_by(GroupSubscriptionModel.created_at.desc()).all()
    return jsonify({"items": [_serialize_group(grp) for grp in groups]}), 200


@bp.route("/subscriptions/groups/<group_id>", methods=["GET"])
@login_required
def get_group(group_id):
    repo = _get_repo()
    group = repo.get_group_by_id(group_id)
    if group is None:
        raise NotFoundError("Group not found.")

    user = g.current_user
    if group.requester_id != user.username and not user.is_admin:
        raise ForbiddenError("Keine Berechtigung.")

    return jsonify(_serialize_group(group)), 200


@bp.route("/subscriptions/<subscription_id>", methods=["GET"])
@login_required
def get_subscription(subscription_id):
    repo = _get_repo()
    sub = repo.get_by_id(subscription_id)
    if sub is None:
        raise NotFoundError("Subscription not found.")

    user = g.current_user
    if sub.requester_id != user.username and not user.is_admin:
        raise ForbiddenError("Keine Berechtigung.")

    return jsonify(_serialize(sub)), 200


@bp.route("/subscriptions/<subscription_id>/change", methods=["POST"])
@login_required
def request_change(subscription_id):
    repo = _get_repo()
    sub = repo.get_by_id(subscription_id)
    if sub is None:
        raise NotFoundError("Subscription not found.")

    user = g.current_user
    if sub.requester_id != user.username and not user.is_admin:
        raise ForbiddenError("Keine Berechtigung.")

    data = request.get_json() or {}
    parameters = data.get("parameters", {})
    reason = data.get("reason")

    service = _get_service()
    try:
        service.request_change(
            sub_id=subscription_id,
            user_id=user.username,
            new_params=parameters,
            reason=reason,
        )
    except PermissionError as e:
        raise ForbiddenError(str(e))
    except ValueError as e:
        raise ConflictError(str(e))

    updated = repo.get_by_id(subscription_id)
    return jsonify(_serialize(updated)), 200


@bp.route("/subscriptions/<subscription_id>/cancel", methods=["POST"])
@login_required
def request_cancel(subscription_id):
    repo = _get_repo()
    sub = repo.get_by_id(subscription_id)
    if sub is None:
        raise NotFoundError("Subscription not found.")

    user = g.current_user
    if sub.requester_id != user.username and not user.is_admin:
        raise ForbiddenError("Keine Berechtigung.")

    data = request.get_json() or {}
    reason = data.get("reason")

    service = _get_service()
    try:
        service.request_cancel(
            sub_id=subscription_id,
            user_id=user.username,
            reason=reason,
        )
    except PermissionError as e:
        raise ForbiddenError(str(e))
    except ValueError as e:
        raise ConflictError(str(e))

    updated = repo.get_by_id(subscription_id)
    return jsonify(_serialize(updated)), 200


# ── Admin endpoints ───────────────────────────────────────────────────────────

@admin_bp.route("/subscriptions", methods=["GET"])
@role_required("admin")
def admin_list_subscriptions():
    repo = _get_repo()
    status = request.args.get("status")
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)

    result = repo.list_subscriptions(
        requester_id=None,
        status=status,
        limit=limit,
        offset=offset,
    )
    return jsonify({
        "items": [_serialize(s) for s in result["items"]],
        "total": result["total"],
        "limit": result["limit"],
        "offset": result["offset"],
    }), 200
