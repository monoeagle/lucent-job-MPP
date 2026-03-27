# tests/unit/test_subscription_service.py
import pytest
from unittest.mock import MagicMock, call
from app.services.subscription_service import SubscriptionService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_subscription(
    sub_id="sub-1",
    requester_id="user-1",
    status="active",
    parameters=None,
    pending_changes=None,
    group_subscription_id=None,
):
    sub = MagicMock()
    sub.id = sub_id
    sub.requester_id = requester_id
    sub.status = status
    sub.parameters = parameters or {"cpu": 2}
    sub.pending_changes = pending_changes
    sub.group_subscription_id = group_subscription_id
    return sub


def _make_order_item(
    item_id="item-1",
    template_slug="vm-basic",
    template_version="1.0.0",
    display_name="Basic VM",
    parameters=None,
    group_id=None,
    quantity=1,
):
    item = MagicMock()
    item.id = item_id
    item.template_slug = template_slug
    item.template_version = template_version
    item.display_name = display_name
    item.parameters = parameters or {"cpu": 2}
    item.group_id = group_id
    item.quantity = quantity
    item.order = MagicMock()
    item.order.requester_id = "user-1"
    return item


def _make_order(order_id="ord-1", requester_id="user-1", items=None, groups=None):
    order = MagicMock()
    order.id = order_id
    order.requester_id = requester_id
    order.items = items or []
    order.groups = groups or []
    return order


def _make_order_item_group(group_id="grp-1", name="Group A"):
    g = MagicMock()
    g.id = group_id
    g.name = name
    return g


# ── TestRequestChange ─────────────────────────────────────────────────────────


class TestRequestChange:
    def setup_method(self):
        self.repo = MagicMock()
        self.service = SubscriptionService(self.repo)

    def test_sets_pending_changes_and_status(self):
        sub = _make_subscription(status="active")
        self.repo.get_by_id.return_value = sub
        new_params = {"cpu": 4}

        self.service.request_change("sub-1", "user-1", new_params, reason="Need more CPU")

        self.repo.set_pending_changes.assert_called_once_with("sub-1", new_params)
        self.repo.update_status.assert_called_once_with("sub-1", "change_pending")

    def test_raises_value_error_if_not_active(self):
        sub = _make_subscription(status="cancelled")
        self.repo.get_by_id.return_value = sub

        with pytest.raises(ValueError, match="active"):
            self.service.request_change("sub-1", "user-1", {"cpu": 4})

    def test_raises_value_error_if_change_pending(self):
        sub = _make_subscription(status="change_pending")
        self.repo.get_by_id.return_value = sub

        with pytest.raises(ValueError, match="active"):
            self.service.request_change("sub-1", "user-1", {"cpu": 4})

    def test_raises_permission_error_if_wrong_user(self):
        sub = _make_subscription(status="active", requester_id="user-1")
        self.repo.get_by_id.return_value = sub

        with pytest.raises(PermissionError):
            self.service.request_change("sub-1", "user-99", {"cpu": 4})

    def test_raises_value_error_if_not_found(self):
        self.repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            self.service.request_change("sub-missing", "user-1", {"cpu": 4})

    def test_reason_is_included_in_pending_changes(self):
        sub = _make_subscription(status="active")
        self.repo.get_by_id.return_value = sub

        self.service.request_change("sub-1", "user-1", {"cpu": 4}, reason="scaling up")

        call_args = self.repo.set_pending_changes.call_args
        stored_changes = call_args[0][1]
        assert stored_changes == {"cpu": 4}

    def test_reason_none_is_accepted(self):
        sub = _make_subscription(status="active")
        self.repo.get_by_id.return_value = sub

        self.service.request_change("sub-1", "user-1", {"cpu": 4}, reason=None)

        self.repo.set_pending_changes.assert_called_once()
        self.repo.update_status.assert_called_once_with("sub-1", "change_pending")


# ── TestRequestCancel ─────────────────────────────────────────────────────────


class TestRequestCancel:
    def setup_method(self):
        self.repo = MagicMock()
        self.service = SubscriptionService(self.repo)

    def test_sets_cancel_pending_status(self):
        sub = _make_subscription(status="active")
        self.repo.get_by_id.return_value = sub

        self.service.request_cancel("sub-1", "user-1", reason="No longer needed")

        self.repo.update_status.assert_called_once_with("sub-1", "cancel_pending")

    def test_stores_reason_in_pending_changes(self):
        sub = _make_subscription(status="active")
        self.repo.get_by_id.return_value = sub

        self.service.request_cancel("sub-1", "user-1", reason="shutdown")

        self.repo.set_pending_changes.assert_called_once_with(
            "sub-1", {"cancel_reason": "shutdown"}
        )

    def test_raises_if_not_active(self):
        sub = _make_subscription(status="ordered")
        self.repo.get_by_id.return_value = sub

        with pytest.raises(ValueError, match="active"):
            self.service.request_cancel("sub-1", "user-1")

    def test_raises_if_already_cancel_pending(self):
        sub = _make_subscription(status="cancel_pending")
        self.repo.get_by_id.return_value = sub

        with pytest.raises(ValueError, match="active"):
            self.service.request_cancel("sub-1", "user-1")

    def test_raises_permission_error_if_wrong_user(self):
        sub = _make_subscription(status="active", requester_id="user-1")
        self.repo.get_by_id.return_value = sub

        with pytest.raises(PermissionError):
            self.service.request_cancel("sub-1", "user-99")

    def test_raises_if_not_found(self):
        self.repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            self.service.request_cancel("sub-missing", "user-1")

    def test_reason_none_stores_empty_cancel_reason(self):
        sub = _make_subscription(status="active")
        self.repo.get_by_id.return_value = sub

        self.service.request_cancel("sub-1", "user-1", reason=None)

        self.repo.set_pending_changes.assert_called_once_with(
            "sub-1", {"cancel_reason": None}
        )


# ── TestCreateFromOrder ───────────────────────────────────────────────────────


class TestCreateFromOrder:
    def setup_method(self):
        self.repo = MagicMock()
        self.service = SubscriptionService(self.repo)

    def test_creates_subscription_per_item(self):
        item1 = _make_order_item(item_id="item-1")
        item2 = _make_order_item(item_id="item-2", template_slug="db-postgres")
        order = _make_order(items=[item1, item2])

        self.service.create_from_order(order, template_costs={})

        assert self.repo.create_from_order_item.call_count == 2

    def test_passes_monthly_cost_from_template_costs(self):
        item = _make_order_item(item_id="item-1", template_slug="vm-basic")
        order = _make_order(items=[item])
        costs = {"vm-basic": 49.99}

        self.service.create_from_order(order, template_costs=costs)

        self.repo.create_from_order_item.assert_called_once_with(item, 49.99)

    def test_passes_none_cost_when_template_not_in_costs(self):
        item = _make_order_item(item_id="item-1", template_slug="unknown-tpl")
        order = _make_order(items=[item])

        self.service.create_from_order(order, template_costs={})

        self.repo.create_from_order_item.assert_called_once_with(item, None)

    def test_creates_group_for_grouped_items(self):
        grp = _make_order_item_group(group_id="grp-1", name="Group A")
        item = _make_order_item(item_id="item-1", group_id="grp-1")
        order = _make_order(items=[item], groups=[grp])

        group_sub = MagicMock()
        group_sub.id = "gsub-1"
        self.repo.create_group.return_value = group_sub
        created_sub = MagicMock()
        created_sub.id = "sub-1"
        self.repo.create_from_order_item.return_value = created_sub

        self.service.create_from_order(order, template_costs={})

        self.repo.create_group.assert_called_once_with(
            name="Group A",
            requester_id="user-1",
        )
        self.repo.assign_to_group.assert_called_once_with("sub-1", "gsub-1")

    def test_ungrouped_items_are_not_assigned_to_group(self):
        item = _make_order_item(item_id="item-1", group_id=None)
        order = _make_order(items=[item])

        self.service.create_from_order(order, template_costs={})

        self.repo.assign_to_group.assert_not_called()

    def test_multiple_items_in_same_group_share_group_subscription(self):
        grp = _make_order_item_group(group_id="grp-1", name="Group A")
        item1 = _make_order_item(item_id="item-1", group_id="grp-1")
        item2 = _make_order_item(item_id="item-2", group_id="grp-1")
        order = _make_order(items=[item1, item2], groups=[grp])

        group_sub = MagicMock()
        group_sub.id = "gsub-1"
        self.repo.create_group.return_value = group_sub

        sub1 = MagicMock()
        sub1.id = "sub-1"
        sub2 = MagicMock()
        sub2.id = "sub-2"
        self.repo.create_from_order_item.side_effect = [sub1, sub2]

        self.service.create_from_order(order, template_costs={})

        # Group created only once
        assert self.repo.create_group.call_count == 1
        # Both subs assigned to same group
        self.repo.assign_to_group.assert_any_call("sub-1", "gsub-1")
        self.repo.assign_to_group.assert_any_call("sub-2", "gsub-1")

    def test_empty_order_creates_nothing(self):
        order = _make_order(items=[])

        self.service.create_from_order(order, template_costs={})

        self.repo.create_from_order_item.assert_not_called()
        self.repo.create_group.assert_not_called()

    def test_returns_list_of_created_subscriptions(self):
        item = _make_order_item(item_id="item-1")
        order = _make_order(items=[item])

        created_sub = MagicMock()
        created_sub.id = "sub-1"
        self.repo.create_from_order_item.return_value = created_sub

        result = self.service.create_from_order(order, template_costs={})

        assert len(result) == 1
        assert result[0].id == "sub-1"


# ── TestApproveChange ─────────────────────────────────────────────────────────


class TestApproveChange:
    def setup_method(self):
        self.repo = MagicMock()
        self.service = SubscriptionService(self.repo)

    def test_applies_pending_changes_and_sets_active(self):
        sub = _make_subscription(status="change_pending")
        self.repo.get_by_id.return_value = sub

        self.service.approve_change("sub-1")

        self.repo.apply_pending_changes.assert_called_once_with("sub-1")
        self.repo.update_status.assert_called_once_with("sub-1", "active")

    def test_approve_cancel_sets_cancelled(self):
        sub = _make_subscription(status="cancel_pending")
        self.repo.get_by_id.return_value = sub

        self.service.approve_change("sub-1")

        self.repo.update_status.assert_called_once_with("sub-1", "cancelled")
        self.repo.apply_pending_changes.assert_not_called()

    def test_raises_if_not_found(self):
        self.repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            self.service.approve_change("sub-missing")

    def test_raises_if_not_pending(self):
        sub = _make_subscription(status="active")
        self.repo.get_by_id.return_value = sub

        with pytest.raises(ValueError, match="pending"):
            self.service.approve_change("sub-1")


# ── TestRejectChange ──────────────────────────────────────────────────────────


class TestRejectChange:
    def setup_method(self):
        self.repo = MagicMock()
        self.service = SubscriptionService(self.repo)

    def test_reverts_to_active_and_clears_pending(self):
        sub = _make_subscription(status="change_pending")
        self.repo.get_by_id.return_value = sub

        self.service.reject_change("sub-1")

        self.repo.set_pending_changes.assert_called_once_with("sub-1", None)
        self.repo.update_status.assert_called_once_with("sub-1", "active")

    def test_reverts_cancel_pending_to_active(self):
        sub = _make_subscription(status="cancel_pending")
        self.repo.get_by_id.return_value = sub

        self.service.reject_change("sub-1")

        self.repo.set_pending_changes.assert_called_once_with("sub-1", None)
        self.repo.update_status.assert_called_once_with("sub-1", "active")

    def test_raises_if_not_found(self):
        self.repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            self.service.reject_change("sub-missing")

    def test_raises_if_not_pending(self):
        sub = _make_subscription(status="active")
        self.repo.get_by_id.return_value = sub

        with pytest.raises(ValueError, match="pending"):
            self.service.reject_change("sub-1")
