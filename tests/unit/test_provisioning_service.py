# tests/unit/test_provisioning_service.py
import pytest
from unittest.mock import MagicMock, call
from app.services.provisioning_service import ProvisioningService
from app.domain.provisioning import ProvisioningStatus
from app.domain.order import OrderStatus


def _make_item(item_id="item-1", order_id="ord-1", provisioning_status="not_started",
               job_id=None, parameters=None):
    item = MagicMock()
    item.id = item_id
    item.order_id = order_id
    item.provisioning_status = provisioning_status
    item.job_id = job_id
    item.parameters = parameters or {"cpu": 4, "memory": 8}
    return item


def _make_order(order_id="ord-1", status="submitted", items=None):
    order = MagicMock()
    order.id = order_id
    order.status = status
    order.items = items or []
    return order


def _build_service():
    order_repo = MagicMock()
    dispatch_log_repo = MagicMock()
    gitlab_client = MagicMock()
    svc = ProvisioningService(order_repo, dispatch_log_repo, gitlab_client)
    return svc, order_repo, dispatch_log_repo, gitlab_client


# ── dispatch_order ────────────────────────────────────────────────

class TestDispatchOrder:
    def test_dispatches_all_not_started_items(self):
        svc, order_repo, dispatch_log_repo, gitlab = _build_service()
        item1 = _make_item(item_id="item-1", provisioning_status="not_started")
        item2 = _make_item(item_id="item-2", provisioning_status="not_started")
        item3 = _make_item(item_id="item-3", provisioning_status="pending")
        order = _make_order(items=[item1, item2, item3])
        order_repo.get_by_id.return_value = order
        gitlab.trigger_pipeline.return_value = {"id": 100}

        svc.dispatch_order("ord-1")

        assert gitlab.trigger_pipeline.call_count == 2


# ── dispatch_item ─────────────────────────────────────────────────

class TestDispatchItem:
    def test_success_stores_job_id_and_sets_pending(self):
        svc, order_repo, dispatch_log_repo, gitlab = _build_service()
        item = _make_item(provisioning_status="not_started")
        order = _make_order(items=[item])
        order_repo.get_by_id.return_value = order
        order_repo.get_item_by_id.return_value = item
        gitlab.trigger_pipeline.return_value = {"id": 42}

        svc.dispatch_item("ord-1", "item-1")

        assert item.provisioning_status == ProvisioningStatus.PENDING
        assert item.job_id == "42"
        dispatch_log_repo.create_log.assert_called_once()
        log_call = dispatch_log_repo.create_log.call_args
        assert log_call.kwargs.get("status") == "success" or log_call[1].get("status") == "success" \
            or (log_call[0][4] if len(log_call[0]) > 4 else None) == "success"

    def test_already_pending_skips(self):
        svc, order_repo, dispatch_log_repo, gitlab = _build_service()
        item = _make_item(provisioning_status="pending")
        order = _make_order(items=[item])
        order_repo.get_by_id.return_value = order
        order_repo.get_item_by_id.return_value = item

        svc.dispatch_item("ord-1", "item-1")

        gitlab.trigger_pipeline.assert_not_called()

    def test_gitlab_error_creates_failed_log(self):
        svc, order_repo, dispatch_log_repo, gitlab = _build_service()
        item = _make_item(provisioning_status="not_started")
        order = _make_order(items=[item])
        order_repo.get_by_id.return_value = order
        order_repo.get_item_by_id.return_value = item
        gitlab.trigger_pipeline.side_effect = Exception("GitLab down")

        svc.dispatch_item("ord-1", "item-1")

        dispatch_log_repo.create_log.assert_called_once()
        log_call = dispatch_log_repo.create_log.call_args
        assert "GitLab down" in str(log_call)


# ── sync_item_status ─────────────────────────────────────────────

class TestSyncItemStatus:
    def test_running_maps_to_provisioning(self):
        svc, order_repo, dispatch_log_repo, gitlab = _build_service()
        item = _make_item(provisioning_status="pending", job_id="99")
        order_repo.get_item_by_id.return_value = item
        gitlab.get_pipeline_status.return_value = {"status": "running"}

        svc.sync_item_status("item-1")

        assert item.provisioning_status == ProvisioningStatus.PROVISIONING

    def test_success_maps_to_done(self):
        svc, order_repo, dispatch_log_repo, gitlab = _build_service()
        item = _make_item(provisioning_status="provisioning", job_id="99")
        order = _make_order(items=[item])
        order_repo.get_item_by_id.return_value = item
        order_repo.get_by_id.return_value = order
        gitlab.get_pipeline_status.return_value = {"status": "success"}

        svc.sync_item_status("item-1")

        assert item.provisioning_status == ProvisioningStatus.DONE


# ── handle_webhook ────────────────────────────────────────────────

class TestHandleWebhook:
    def test_updates_status_from_webhook(self):
        svc, order_repo, dispatch_log_repo, gitlab = _build_service()
        item = _make_item(provisioning_status="pending", job_id="200")
        order = _make_order(items=[item])
        order_repo.get_item_by_id.return_value = item
        order_repo.get_by_id.return_value = order

        # Mock finding item by job_id
        order_repo.find_item_by_job_id = MagicMock(return_value=item)

        svc.handle_webhook(pipeline_id=200, status="success")

        assert item.provisioning_status == ProvisioningStatus.DONE


# ── update_order_aggregate_status ─────────────────────────────────

class TestUpdateOrderAggregateStatus:
    def test_all_done_sets_order_done(self):
        svc, order_repo, dispatch_log_repo, gitlab = _build_service()
        item1 = _make_item(item_id="i1", provisioning_status="done")
        item2 = _make_item(item_id="i2", provisioning_status="done")
        order = _make_order(items=[item1, item2], status="provisioning")
        order_repo.get_by_id.return_value = order

        svc.update_order_aggregate_status("ord-1")

        order_repo.update_order_status.assert_called_once_with("ord-1", OrderStatus.DONE)

    def test_one_failed_sets_order_failed(self):
        svc, order_repo, dispatch_log_repo, gitlab = _build_service()
        item1 = _make_item(item_id="i1", provisioning_status="done")
        item2 = _make_item(item_id="i2", provisioning_status="failed")
        order = _make_order(items=[item1, item2], status="provisioning")
        order_repo.get_by_id.return_value = order

        svc.update_order_aggregate_status("ord-1")

        order_repo.update_order_status.assert_called_once_with("ord-1", OrderStatus.FAILED)

    def test_mixed_pending_no_change(self):
        svc, order_repo, dispatch_log_repo, gitlab = _build_service()
        item1 = _make_item(item_id="i1", provisioning_status="done")
        item2 = _make_item(item_id="i2", provisioning_status="provisioning")
        order = _make_order(items=[item1, item2], status="provisioning")
        order_repo.get_by_id.return_value = order

        svc.update_order_aggregate_status("ord-1")

        order_repo.update_order_status.assert_not_called()
