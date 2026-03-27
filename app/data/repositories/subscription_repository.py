import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.data.db.models.order import OrderItemModel
from app.data.db.models.subscription import GroupSubscriptionModel, SubscriptionModel


class SubscriptionRepository:
    class SubscriptionNotFoundError(Exception):
        pass

    class GroupNotFoundError(Exception):
        pass

    def __init__(self, session: Session):
        self.session = session

    # ── Subscription CRUD ─────────────────────────────────────────

    def create_from_order_item(
        self,
        item: OrderItemModel,
        monthly_cost_eur: Decimal | None = None,
    ) -> SubscriptionModel:
        requester_id = item.order.requester_id
        subscription = SubscriptionModel(
            id=str(uuid.uuid4()),
            order_item_id=item.id,
            requester_id=requester_id,
            status="ordered",
            display_name=item.display_name,
            template_slug=item.template_slug,
            template_version=item.template_version,
            parameters=item.parameters,
            monthly_cost_eur=monthly_cost_eur,
        )
        self.session.add(subscription)
        self.session.commit()
        return subscription

    def get_by_id(self, subscription_id: str) -> SubscriptionModel | None:
        return (
            self.session.query(SubscriptionModel)
            .filter_by(id=subscription_id)
            .first()
        )

    def list_subscriptions(
        self,
        requester_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        q = self.session.query(SubscriptionModel)
        if requester_id:
            q = q.filter_by(requester_id=requester_id)
        if status:
            q = q.filter_by(status=status)
        total = q.count()
        items = (
            q.order_by(SubscriptionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    # ── Status transitions ────────────────────────────────────────

    def update_status(self, subscription_id: str, new_status: str) -> SubscriptionModel:
        sub = self.get_by_id(subscription_id)
        if sub is None:
            raise self.SubscriptionNotFoundError(
                f"Subscription '{subscription_id}' not found."
            )
        sub.status = new_status
        if new_status == "active":
            sub.activated_at = datetime.now(timezone.utc)
        elif new_status == "cancelled":
            sub.cancelled_at = datetime.now(timezone.utc)
        self.session.commit()
        return sub

    # ── Pending changes ───────────────────────────────────────────

    def set_pending_changes(self, subscription_id: str, changes: dict) -> SubscriptionModel:
        sub = self.get_by_id(subscription_id)
        if sub is None:
            raise self.SubscriptionNotFoundError(
                f"Subscription '{subscription_id}' not found."
            )
        sub.pending_changes = changes
        self.session.commit()
        return sub

    def apply_pending_changes(self, subscription_id: str) -> SubscriptionModel:
        sub = self.get_by_id(subscription_id)
        if sub is None:
            raise self.SubscriptionNotFoundError(
                f"Subscription '{subscription_id}' not found."
            )
        if sub.pending_changes:
            merged = {**(sub.parameters or {}), **sub.pending_changes}
            sub.parameters = merged
            sub.pending_changes = None
        self.session.commit()
        return sub

    # ── Groups ────────────────────────────────────────────────────

    def create_group(self, name: str, requester_id: str) -> GroupSubscriptionModel:
        group = GroupSubscriptionModel(
            id=str(uuid.uuid4()),
            name=name,
            requester_id=requester_id,
        )
        self.session.add(group)
        self.session.commit()
        return group

    def get_group_by_id(self, group_id: str) -> GroupSubscriptionModel | None:
        return (
            self.session.query(GroupSubscriptionModel)
            .filter_by(id=group_id)
            .first()
        )

    def assign_to_group(self, subscription_id: str, group_id: str) -> SubscriptionModel:
        sub = self.get_by_id(subscription_id)
        if sub is None:
            raise self.SubscriptionNotFoundError(
                f"Subscription '{subscription_id}' not found."
            )
        group = self.get_group_by_id(group_id)
        if group is None:
            raise self.GroupNotFoundError(f"Group '{group_id}' not found.")
        sub.group_subscription_id = group_id
        self.session.commit()
        return sub
