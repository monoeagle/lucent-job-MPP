# tests/integration/test_approval_repository.py
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.approval_repository import ApprovalRepository
from app.data.db.models.order import OrderModel


@pytest.fixture
def repo():
    engine = get_engine("postgresql://mpp:mpp@localhost:5432/mpp_test")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    yield ApprovalRepository(session)
    session.close()
    Base.metadata.drop_all(engine)


def _create_order(repo) -> str:
    """Helper to create an order for FK reference."""
    order_id = str(uuid.uuid4())
    order = OrderModel(
        id=order_id,
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        requester_id="user-test",
        status="submitted",
        title="Test Order",
    )
    repo.session.add(order)
    repo.session.commit()
    return order_id


class TestApprovalRulesCRUD:
    def test_create_rule(self, repo):
        rule = repo.create_rule("High Cost", "cost_threshold", threshold_eur=5000)
        assert rule.id is not None
        assert rule.name == "High Cost"
        assert rule.rule_type == "cost_threshold"
        assert float(rule.threshold_eur) == 5000.0
        assert rule.is_active is True

    def test_list_rules_all(self, repo):
        repo.create_rule("Rule A", "always")
        repo.create_rule("Rule B", "always", is_active=False)
        rules = repo.list_rules()
        assert len(rules) == 2

    def test_list_rules_active_only(self, repo):
        repo.create_rule("Active", "always")
        repo.create_rule("Inactive", "always", is_active=False)
        rules = repo.list_rules(is_active=True)
        assert len(rules) == 1
        assert rules[0].name == "Active"

    def test_get_rule(self, repo):
        rule = repo.create_rule("My Rule", "service_type", service_type_slug="firewall")
        loaded = repo.get_rule(rule.id)
        assert loaded is not None
        assert loaded.name == "My Rule"
        assert loaded.service_type_slug == "firewall"

    def test_get_rule_not_found(self, repo):
        assert repo.get_rule("nonexistent") is None

    def test_update_rule(self, repo):
        rule = repo.create_rule("Old Name", "always")
        updated = repo.update_rule(rule.id, name="New Name", is_active=False)
        assert updated.name == "New Name"
        assert updated.is_active is False

    def test_delete_rule(self, repo):
        rule = repo.create_rule("To Delete", "always")
        repo.delete_rule(rule.id)
        assert repo.get_rule(rule.id) is None

    def test_delete_rule_with_pending_request_raises(self, repo):
        rule = repo.create_rule("Protected", "always")
        order_id = _create_order(repo)
        repo.create_request(order_id, [rule.id], datetime.now(timezone.utc) + timedelta(hours=48))
        with pytest.raises(Exception):
            repo.delete_rule(rule.id)


class TestApprovalRequests:
    def test_create_and_get_request(self, repo):
        order_id = _create_order(repo)
        deadline = datetime.now(timezone.utc) + timedelta(hours=48)
        request = repo.create_request(order_id, ["rule-1", "rule-2"], deadline)
        assert request.id is not None
        assert request.order_id == order_id
        assert request.status == "pending"
        assert request.approval_rule_ids == ["rule-1", "rule-2"]

        loaded = repo.get_request(request.id)
        assert loaded is not None
        assert loaded.order_id == order_id

    def test_get_request_for_order(self, repo):
        order_id = _create_order(repo)
        deadline = datetime.now(timezone.utc) + timedelta(hours=48)
        repo.create_request(order_id, ["rule-1"], deadline)
        loaded = repo.get_request_for_order(order_id)
        assert loaded is not None
        assert loaded.order_id == order_id

    def test_decide_request_approve(self, repo):
        order_id = _create_order(repo)
        deadline = datetime.now(timezone.utc) + timedelta(hours=48)
        request = repo.create_request(order_id, ["rule-1"], deadline)
        result = repo.decide_request(request.id, "approved", "approver-1", "Looks good")
        assert result is True
        loaded = repo.get_request(request.id)
        assert loaded.status == "approved"
        assert loaded.decided_by == "approver-1"
        assert loaded.decision_reason == "Looks good"
        assert loaded.decided_at is not None

    def test_decide_already_decided_returns_false(self, repo):
        order_id = _create_order(repo)
        deadline = datetime.now(timezone.utc) + timedelta(hours=48)
        request = repo.create_request(order_id, ["rule-1"], deadline)
        repo.decide_request(request.id, "approved", "approver-1", "OK")
        result = repo.decide_request(request.id, "rejected", "approver-2", "Too late")
        assert result is False

    def test_list_pending_requests(self, repo):
        order_id = _create_order(repo)
        deadline = datetime.now(timezone.utc) + timedelta(hours=48)
        repo.create_request(order_id, ["rule-1"], deadline)
        pending = repo.list_pending_requests()
        assert len(pending) == 1
        assert pending[0].status == "pending"

    def test_list_expired_requests(self, repo):
        order_id = _create_order(repo)
        past_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        repo.create_request(order_id, ["rule-1"], past_deadline)
        now = datetime.now(timezone.utc)
        expired = repo.list_expired_requests(now)
        assert len(expired) == 1
        assert expired[0].order_id == order_id
