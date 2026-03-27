# app/services/subscription_service.py

_PENDING_STATUSES = {"change_pending", "cancel_pending"}


class SubscriptionService:
    def __init__(self, subscription_repo):
        self.repo = subscription_repo

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_or_raise(self, sub_id: str):
        """Fetch subscription or raise ValueError."""
        sub = self.repo.get_by_id(sub_id)
        if sub is None:
            raise ValueError(f"Subscription '{sub_id}' not found.")
        return sub

    def _get_for_user(self, sub_id: str, user_id: str):
        """Fetch subscription and verify ownership."""
        sub = self._get_or_raise(sub_id)
        if sub.requester_id != user_id:
            raise PermissionError("No permission to access this subscription.")
        return sub

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def request_change(
        self,
        sub_id: str,
        user_id: str,
        new_params: dict,
        reason: str | None = None,
    ):
        """Request a parameter change on an active subscription.

        Sets pending_changes to new_params and transitions status to
        change_pending. Only the subscription owner may request changes,
        and the subscription must be active.
        """
        sub = self._get_for_user(sub_id, user_id)
        if sub.status != "active":
            raise ValueError(
                f"Subscription must be active to request a change (current: {sub.status})."
            )
        self.repo.set_pending_changes(sub_id, new_params)
        self.repo.update_status(sub_id, "change_pending")

    def request_cancel(
        self,
        sub_id: str,
        user_id: str,
        reason: str | None = None,
    ):
        """Request cancellation of an active subscription.

        Stores the cancel reason in pending_changes and transitions status to
        cancel_pending. Only the owner may cancel, and the subscription must be
        active.
        """
        sub = self._get_for_user(sub_id, user_id)
        if sub.status != "active":
            raise ValueError(
                f"Subscription must be active to request cancellation (current: {sub.status})."
            )
        self.repo.set_pending_changes(sub_id, {"cancel_reason": reason})
        self.repo.update_status(sub_id, "cancel_pending")

    def approve_change(self, sub_id: str):
        """Approve a pending change or cancellation request.

        For change_pending: applies pending params and returns to active.
        For cancel_pending: transitions to cancelled.
        Raises ValueError for any other status.
        """
        sub = self._get_or_raise(sub_id)
        if sub.status not in _PENDING_STATUSES:
            raise ValueError(
                f"Subscription must be in a pending state to approve (current: {sub.status})."
            )
        if sub.status == "change_pending":
            self.repo.apply_pending_changes(sub_id)
            self.repo.update_status(sub_id, "active")
        else:  # cancel_pending
            self.repo.update_status(sub_id, "cancelled")

    def reject_change(self, sub_id: str):
        """Reject a pending change or cancellation request.

        Clears pending_changes and reverts status to active regardless of
        whether the pending state was change_pending or cancel_pending.
        """
        sub = self._get_or_raise(sub_id)
        if sub.status not in _PENDING_STATUSES:
            raise ValueError(
                f"Subscription must be in a pending state to reject (current: {sub.status})."
            )
        self.repo.set_pending_changes(sub_id, None)
        self.repo.update_status(sub_id, "active")

    # ── Creation ──────────────────────────────────────────────────────────────

    def create_from_order(self, order, template_costs: dict) -> list:
        """Create Subscription records (and GroupSubscriptions) from an order.

        For each OrderItem a Subscription is created. Items that belong to an
        OrderItemGroup are also assigned to a shared GroupSubscription. One
        GroupSubscription is created per distinct order group.

        Args:
            order: OrderModel with .items and .groups populated.
            template_costs: mapping of template_slug → monthly_cost_eur (Decimal
                            or float). Missing slugs default to None.

        Returns:
            List of created SubscriptionModel instances (one per item).
        """
        # Pre-build group_id → GroupSubscriptionModel mapping (lazily created)
        group_sub_by_order_group: dict = {}
        for grp in (order.groups or []):
            group_sub = self.repo.create_group(
                name=grp.name,
                requester_id=order.requester_id,
            )
            group_sub_by_order_group[grp.id] = group_sub

        subscriptions = []
        for item in order.items:
            monthly_cost = template_costs.get(item.template_slug)
            sub = self.repo.create_from_order_item(item, monthly_cost)

            if item.group_id and item.group_id in group_sub_by_order_group:
                group_sub = group_sub_by_order_group[item.group_id]
                self.repo.assign_to_group(sub.id, group_sub.id)

            subscriptions.append(sub)

        return subscriptions
