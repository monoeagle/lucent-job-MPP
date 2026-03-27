# tests/integration/test_approval_db.py
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.exc import IntegrityError
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.db.models.approval import ApprovalRuleModel, ApprovalRequestModel


class TestApprovalRuleModel:
    def setup_method(self):
        self.engine = get_engine("postgresql://mpp:mpp@localhost:5432/mpp_test")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.Session = get_session_factory(self.engine)

    def teardown_method(self):
        Base.metadata.drop_all(self.engine)

    def test_create_and_read_approval_rule(self):
        session = self.Session()
        rule = ApprovalRuleModel(
            id=str(uuid.uuid4()),
            name="High Cost Approval",
            rule_type="cost_threshold",
            threshold_eur=5000.00,
            service_type_slug=None,
            is_active=True,
        )
        session.add(rule)
        session.commit()

        loaded = session.query(ApprovalRuleModel).filter_by(id=rule.id).first()
        assert loaded is not None
        assert loaded.name == "High Cost Approval"
        assert loaded.rule_type == "cost_threshold"
        assert float(loaded.threshold_eur) == 5000.00
        assert loaded.service_type_slug is None
        assert loaded.is_active is True
        assert loaded.created_at is not None
        assert loaded.updated_at is not None
        session.close()

    def test_create_service_type_rule(self):
        session = self.Session()
        rule = ApprovalRuleModel(
            id=str(uuid.uuid4()),
            name="Firewall Approval",
            rule_type="service_type",
            threshold_eur=None,
            service_type_slug="firewall-rule",
        )
        session.add(rule)
        session.commit()

        loaded = session.query(ApprovalRuleModel).filter_by(id=rule.id).first()
        assert loaded is not None
        assert loaded.rule_type == "service_type"
        assert loaded.threshold_eur is None
        assert loaded.service_type_slug == "firewall-rule"
        session.close()

    def test_create_always_rule(self):
        session = self.Session()
        rule = ApprovalRuleModel(
            id=str(uuid.uuid4()),
            name="Always Approve",
            rule_type="always",
        )
        session.add(rule)
        session.commit()

        loaded = session.query(ApprovalRuleModel).filter_by(id=rule.id).first()
        assert loaded is not None
        assert loaded.rule_type == "always"
        assert loaded.threshold_eur is None
        assert loaded.service_type_slug is None
        assert loaded.is_active is True
        session.close()


class TestApprovalRequestModel:
    def setup_method(self):
        self.engine = get_engine("postgresql://mpp:mpp@localhost:5432/mpp_test")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.Session = get_session_factory(self.engine)

    def teardown_method(self):
        Base.metadata.drop_all(self.engine)

    def _create_order(self, session):
        """Helper to create an order for FK reference."""
        from app.data.db.models.order import OrderModel
        order_id = str(uuid.uuid4())
        order = OrderModel(
            id=order_id,
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            requester_id="user-test",
            status="submitted",
            title="Test Order",
        )
        session.add(order)
        session.commit()
        return order_id

    def test_create_and_read_approval_request(self):
        session = self.Session()
        order_id = self._create_order(session)
        now = datetime.now(timezone.utc)
        rule_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

        request = ApprovalRequestModel(
            id=str(uuid.uuid4()),
            order_id=order_id,
            status="pending",
            approval_rule_ids=rule_ids,
            requested_at=now,
            deadline_at=now + timedelta(hours=48),
        )
        session.add(request)
        session.commit()

        loaded = session.query(ApprovalRequestModel).filter_by(id=request.id).first()
        assert loaded is not None
        assert loaded.order_id == order_id
        assert loaded.status == "pending"
        assert loaded.approval_rule_ids == rule_ids
        assert loaded.requested_at is not None
        assert loaded.deadline_at is not None
        assert loaded.decided_by is None
        assert loaded.decided_at is None
        assert loaded.decision_reason is None
        session.close()

    def test_unique_constraint_order_id(self):
        session = self.Session()
        order_id = self._create_order(session)
        now = datetime.now(timezone.utc)

        r1 = ApprovalRequestModel(
            id=str(uuid.uuid4()),
            order_id=order_id,
            status="pending",
            approval_rule_ids=["rule-1"],
            requested_at=now,
            deadline_at=now + timedelta(hours=48),
        )
        session.add(r1)
        session.commit()

        r2 = ApprovalRequestModel(
            id=str(uuid.uuid4()),
            order_id=order_id,
            status="pending",
            approval_rule_ids=["rule-2"],
            requested_at=now,
            deadline_at=now + timedelta(hours=48),
        )
        session.add(r2)
        with pytest.raises(IntegrityError):
            session.commit()
        session.close()
