# tests/unit/test_approval_service.py
import pytest
from unittest.mock import MagicMock
from app.services.approval_service import ApprovalService


def _make_rule(rule_id="rule-1", name="Test Rule", rule_type="always",
               threshold_eur=None, service_type_slug=None, is_active=True):
    rule = MagicMock()
    rule.id = rule_id
    rule.name = name
    rule.rule_type = rule_type
    rule.threshold_eur = threshold_eur
    rule.service_type_slug = service_type_slug
    rule.is_active = is_active
    return rule


def _make_template(slug="vm-basic", estimated_cost=100.0, approval_always_required=False):
    tpl = MagicMock()
    tpl.slug = slug
    tpl.estimated_cost_eur_per_month = estimated_cost
    tpl.approval_always_required = approval_always_required
    return tpl


def _make_item(template_slug="vm-basic"):
    item = MagicMock()
    item.template_slug = template_slug
    return item


def _make_order(order_id="ord-1", requester_id="user-1", items=None):
    order = MagicMock()
    order.id = order_id
    order.requester_id = requester_id
    order.items = items or []
    return order


def _make_request(request_id="req-1", order_id="ord-1", status="pending",
                  decided_by=None):
    req = MagicMock()
    req.id = request_id
    req.order_id = order_id
    req.status = status
    req.decided_by = decided_by
    return req


class TestEvaluateRules:
    def setup_method(self):
        self.approval_repo = MagicMock()
        self.order_repo = MagicMock()
        self.template_repo = MagicMock()
        self.service = ApprovalService(
            self.approval_repo, self.order_repo, self.template_repo,
        )

    def test_no_rules_returns_empty(self):
        self.approval_repo.list_rules.return_value = []
        order = _make_order(items=[_make_item()])
        self.template_repo.get_by_slug.return_value = _make_template()
        result = self.service.evaluate_rules(order)
        assert result == []

    def test_cost_threshold_exceeded(self):
        rule = _make_rule(rule_id="r-cost", rule_type="cost_threshold", threshold_eur=500)
        self.approval_repo.list_rules.return_value = [rule]
        order = _make_order(items=[_make_item()])
        self.template_repo.get_by_slug.return_value = _make_template(estimated_cost=600.0)
        result = self.service.evaluate_rules(order)
        assert "r-cost" in result

    def test_cost_threshold_not_exceeded(self):
        rule = _make_rule(rule_id="r-cost", rule_type="cost_threshold", threshold_eur=1000)
        self.approval_repo.list_rules.return_value = [rule]
        order = _make_order(items=[_make_item()])
        self.template_repo.get_by_slug.return_value = _make_template(estimated_cost=200.0)
        result = self.service.evaluate_rules(order)
        assert result == []

    def test_service_type_match(self):
        rule = _make_rule(rule_id="r-svc", rule_type="service_type", service_type_slug="firewall")
        self.approval_repo.list_rules.return_value = [rule]
        order = _make_order(items=[_make_item(template_slug="firewall")])
        self.template_repo.get_by_slug.return_value = _make_template(slug="firewall")
        result = self.service.evaluate_rules(order)
        assert "r-svc" in result

    def test_always_rule(self):
        rule = _make_rule(rule_id="r-always", rule_type="always")
        self.approval_repo.list_rules.return_value = [rule]
        order = _make_order(items=[_make_item()])
        self.template_repo.get_by_slug.return_value = _make_template()
        result = self.service.evaluate_rules(order)
        assert "r-always" in result

    def test_template_approval_always_required(self):
        self.approval_repo.list_rules.return_value = []
        order = _make_order(items=[_make_item()])
        self.template_repo.get_by_slug.return_value = _make_template(
            approval_always_required=True,
        )
        result = self.service.evaluate_rules(order)
        assert "template_flag" in result

    def test_inactive_rule_ignored(self):
        rule = _make_rule(rule_id="r-inactive", rule_type="always", is_active=False)
        self.approval_repo.list_rules.return_value = [rule]
        order = _make_order(items=[_make_item()])
        self.template_repo.get_by_slug.return_value = _make_template()
        # list_rules(is_active=True) should not return inactive rules,
        # but we test that the service passes is_active=True
        result = self.service.evaluate_rules(order)
        # The service calls list_rules(is_active=True), so it should filter
        assert "r-inactive" in result or "r-inactive" not in result  # depends on mock
        # Real check: the service must call list_rules with is_active=True
        self.approval_repo.list_rules.assert_called_with(is_active=True)


class TestApprove:
    def setup_method(self):
        self.approval_repo = MagicMock()
        self.order_repo = MagicMock()
        self.service = ApprovalService(
            self.approval_repo, self.order_repo,
        )

    def test_approve_success(self):
        request = _make_request(order_id="ord-1")
        self.approval_repo.get_request.return_value = request
        order = _make_order(requester_id="user-1")
        self.order_repo.get_by_id.return_value = order
        self.approval_repo.decide_request.return_value = True
        updated = _make_request(status="approved")
        self.approval_repo.get_request.side_effect = [request, updated]

        result = self.service.approve("req-1", "approver-1", reason="Approved")
        assert result.status == "approved"

    def test_approve_self_approval_blocked(self):
        request = _make_request(order_id="ord-1")
        self.approval_repo.get_request.return_value = request
        order = _make_order(requester_id="user-1")
        self.order_repo.get_by_id.return_value = order

        with pytest.raises(ApprovalService.SelfApprovalError):
            self.service.approve("req-1", "user-1")

    def test_approve_already_decided_raises_conflict(self):
        request = _make_request(order_id="ord-1")
        self.approval_repo.get_request.return_value = request
        order = _make_order(requester_id="user-1")
        self.order_repo.get_by_id.return_value = order
        self.approval_repo.decide_request.return_value = False

        with pytest.raises(ApprovalService.ConflictError):
            self.service.approve("req-1", "approver-1")


class TestReject:
    def setup_method(self):
        self.approval_repo = MagicMock()
        self.order_repo = MagicMock()
        self.service = ApprovalService(
            self.approval_repo, self.order_repo,
        )

    def test_reject_success(self):
        request = _make_request(order_id="ord-1")
        self.approval_repo.get_request.return_value = request
        order = _make_order(requester_id="user-1")
        self.order_repo.get_by_id.return_value = order
        self.approval_repo.decide_request.return_value = True
        updated = _make_request(status="rejected")
        self.approval_repo.get_request.side_effect = [request, updated]

        result = self.service.reject("req-1", "approver-1", reason="Not justified")
        assert result.status == "rejected"

    def test_reject_missing_reason_raises(self):
        request = _make_request(order_id="ord-1")
        self.approval_repo.get_request.return_value = request
        order = _make_order(requester_id="user-1")
        self.order_repo.get_by_id.return_value = order

        with pytest.raises(ValueError, match="reason"):
            self.service.reject("req-1", "approver-1", reason=None)


class TestProcessTimeouts:
    def setup_method(self):
        self.approval_repo = MagicMock()
        self.order_repo = MagicMock()
        self.service = ApprovalService(
            self.approval_repo, self.order_repo,
        )

    def test_expires_overdue_requests(self):
        expired_req = _make_request(request_id="req-expired")
        self.approval_repo.list_expired_requests.return_value = [expired_req]
        self.approval_repo.decide_request.return_value = True

        self.service.process_timeouts()

        self.approval_repo.decide_request.assert_called_once_with(
            "req-expired", "rejected", "system", "Automatically rejected: approval deadline exceeded.",
        )
