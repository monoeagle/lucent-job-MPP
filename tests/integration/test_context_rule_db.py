# tests/integration/test_context_rule_db.py
import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.db.models.context_rule import (
    AvailabilityRuleModel,
    ContextRestrictionModel,
    UserTenantAssignmentModel,
)


class TestAvailabilityRuleModel:
    def setup_method(self):
        self.engine = get_engine("postgresql://mpp:mpp@localhost:5432/mpp_test")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.Session = get_session_factory(self.engine)

    def teardown_method(self):
        Base.metadata.drop_all(self.engine)

    def test_create_and_read_availability_rule(self):
        session = self.Session()
        rule = AvailabilityRuleModel(
            id=str(uuid.uuid4()),
            name="Berlin Allow Rule",
            template_slug="vm-linux",
            rule_type="allow",
            conditions={"location_id": "loc-berlin", "security_zone_id": "sz-medium"},
            priority=10,
            is_active=True,
        )
        session.add(rule)
        session.commit()

        loaded = session.query(AvailabilityRuleModel).filter_by(id=rule.id).first()
        assert loaded is not None
        assert loaded.name == "Berlin Allow Rule"
        assert loaded.template_slug == "vm-linux"
        assert loaded.rule_type == "allow"
        assert loaded.conditions["location_id"] == "loc-berlin"
        assert loaded.conditions["security_zone_id"] == "sz-medium"
        assert loaded.priority == 10
        assert loaded.is_active is True
        assert loaded.created_at is not None
        assert loaded.updated_at is not None
        session.close()

    def test_query_rules_by_template_slug(self):
        session = self.Session()
        for i, slug in enumerate(["vm-linux", "vm-linux", "vm-windows"]):
            session.add(AvailabilityRuleModel(
                id=str(uuid.uuid4()),
                name=f"Rule {i}",
                template_slug=slug,
                rule_type="allow",
                conditions={"location_id": f"loc-{i}"},
                priority=i,
            ))
        session.commit()

        linux_rules = session.query(AvailabilityRuleModel).filter_by(
            template_slug="vm-linux"
        ).all()
        assert len(linux_rules) == 2

        windows_rules = session.query(AvailabilityRuleModel).filter_by(
            template_slug="vm-windows"
        ).all()
        assert len(windows_rules) == 1
        session.close()


class TestContextRestrictionModel:
    def setup_method(self):
        self.engine = get_engine("postgresql://mpp:mpp@localhost:5432/mpp_test")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.Session = get_session_factory(self.engine)

    def teardown_method(self):
        Base.metadata.drop_all(self.engine)

    def test_create_and_read_context_restriction(self):
        session = self.Session()
        restriction = ContextRestrictionModel(
            id=str(uuid.uuid4()),
            name="Max CPU for medium zone",
            template_slug="vm-linux",
            parameter_key="cpu_cores",
            restriction_type="override_max",
            conditions={"security_zone_id": "sz-medium"},
            effect={"max": 8},
            priority=5,
            is_active=True,
        )
        session.add(restriction)
        session.commit()

        loaded = session.query(ContextRestrictionModel).filter_by(id=restriction.id).first()
        assert loaded is not None
        assert loaded.name == "Max CPU for medium zone"
        assert loaded.template_slug == "vm-linux"
        assert loaded.parameter_key == "cpu_cores"
        assert loaded.restriction_type == "override_max"
        assert loaded.conditions == {"security_zone_id": "sz-medium"}
        assert loaded.effect == {"max": 8}
        assert loaded.priority == 5
        assert loaded.is_active is True
        assert loaded.created_at is not None
        assert loaded.updated_at is not None
        session.close()

    def test_restriction_with_null_template_slug(self):
        session = self.Session()
        restriction = ContextRestrictionModel(
            id=str(uuid.uuid4()),
            name="Global disk restriction",
            template_slug=None,
            parameter_key="disk_type",
            restriction_type="filter_options",
            conditions={"security_zone_id": "sz-high"},
            effect={"allowed_values": ["ssd"]},
        )
        session.add(restriction)
        session.commit()

        loaded = session.query(ContextRestrictionModel).filter_by(id=restriction.id).first()
        assert loaded is not None
        assert loaded.template_slug is None
        session.close()


class TestUserTenantAssignmentModel:
    def setup_method(self):
        self.engine = get_engine("postgresql://mpp:mpp@localhost:5432/mpp_test")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.Session = get_session_factory(self.engine)

    def teardown_method(self):
        Base.metadata.drop_all(self.engine)

    def test_create_and_read_assignment(self):
        session = self.Session()
        assignment = UserTenantAssignmentModel(
            id=str(uuid.uuid4()),
            user_id="user-alice",
            tenant_id="tenant-acme",
        )
        session.add(assignment)
        session.commit()

        loaded = session.query(UserTenantAssignmentModel).filter_by(id=assignment.id).first()
        assert loaded is not None
        assert loaded.user_id == "user-alice"
        assert loaded.tenant_id == "tenant-acme"
        assert loaded.created_at is not None
        session.close()

    def test_unique_constraint_user_tenant(self):
        session = self.Session()
        a1 = UserTenantAssignmentModel(
            id=str(uuid.uuid4()),
            user_id="user-bob",
            tenant_id="tenant-acme",
        )
        a2 = UserTenantAssignmentModel(
            id=str(uuid.uuid4()),
            user_id="user-bob",
            tenant_id="tenant-acme",
        )
        session.add(a1)
        session.commit()
        session.add(a2)
        with pytest.raises(IntegrityError):
            session.commit()
        session.close()
