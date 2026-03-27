"""Test that seed.py runs without errors and creates expected data."""
import os
import pytest
from sqlalchemy import text

from app.data.db.session import get_engine, get_session_factory, Base
from app.data.db.models import *  # noqa: F401,F403


@pytest.fixture
def clean_db():
    """Provide a clean database, drop all tables before and after."""
    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://mpp:mpp@localhost:5432/mpp_test"
    )
    engine = get_engine(db_url)

    # Clean slate
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    Session = get_session_factory(engine)
    session = Session()
    yield session, db_url
    session.close()

    # Cleanup
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_seed_runs_without_errors(clean_db, monkeypatch):
    """Seed script completes without exceptions."""
    session, db_url = clean_db
    session.close()

    monkeypatch.setenv("DATABASE_URL", db_url)

    # Import and run seed
    from scripts.seed import seed
    seed()  # Should not raise


def test_seed_creates_templates(clean_db, monkeypatch):
    session, db_url = clean_db
    session.close()
    monkeypatch.setenv("DATABASE_URL", db_url)

    from scripts.seed import seed
    seed()

    Session = get_session_factory(get_engine(db_url))
    s = Session()

    from app.data.db.models.service_template import ServiceTemplateModel
    templates = s.query(ServiceTemplateModel).all()
    assert len(templates) == 2
    slugs = {t.slug for t in templates}
    assert slugs == {"vm-windows", "vm-linux"}
    s.close()


def test_seed_creates_orders(clean_db, monkeypatch):
    session, db_url = clean_db
    session.close()
    monkeypatch.setenv("DATABASE_URL", db_url)

    from scripts.seed import seed
    seed()

    Session = get_session_factory(get_engine(db_url))
    s = Session()

    from app.data.db.models.order import OrderModel
    orders = s.query(OrderModel).all()
    assert len(orders) == 8
    s.close()


def test_seed_creates_approval_rules(clean_db, monkeypatch):
    session, db_url = clean_db
    session.close()
    monkeypatch.setenv("DATABASE_URL", db_url)

    from scripts.seed import seed
    seed()

    Session = get_session_factory(get_engine(db_url))
    s = Session()

    from app.data.db.models.approval import ApprovalRuleModel
    rules = s.query(ApprovalRuleModel).all()
    assert len(rules) == 3
    names = {r.name for r in rules}
    assert "Standard-Genehmigung" in names
    assert "Kostengrenze 500 EUR" in names
    s.close()


def test_seed_creates_availability_rules(clean_db, monkeypatch):
    session, db_url = clean_db
    session.close()
    monkeypatch.setenv("DATABASE_URL", db_url)

    from scripts.seed import seed
    seed()

    Session = get_session_factory(get_engine(db_url))
    s = Session()

    from app.data.db.models.context_rule import AvailabilityRuleModel
    rules = s.query(AvailabilityRuleModel).all()
    assert len(rules) == 3
    s.close()


def test_seed_creates_context_restrictions(clean_db, monkeypatch):
    session, db_url = clean_db
    session.close()
    monkeypatch.setenv("DATABASE_URL", db_url)

    from scripts.seed import seed
    seed()

    Session = get_session_factory(get_engine(db_url))
    s = Session()

    from app.data.db.models.context_rule import ContextRestrictionModel
    restrictions = s.query(ContextRestrictionModel).all()
    assert len(restrictions) == 4
    s.close()


def test_seed_creates_tenant_assignments(clean_db, monkeypatch):
    session, db_url = clean_db
    session.close()
    monkeypatch.setenv("DATABASE_URL", db_url)

    from scripts.seed import seed
    seed()

    Session = get_session_factory(get_engine(db_url))
    s = Session()

    from app.data.db.models.context_rule import UserTenantAssignmentModel
    assignments = s.query(UserTenantAssignmentModel).all()
    assert len(assignments) == 11
    s.close()


def test_seed_is_idempotent(clean_db, monkeypatch):
    """Running seed twice should skip on second run (data exists check)."""
    session, db_url = clean_db
    session.close()
    monkeypatch.setenv("DATABASE_URL", db_url)

    from scripts.seed import seed
    seed()
    seed()  # Second run should not raise, just skip

    Session = get_session_factory(get_engine(db_url))
    s = Session()

    from app.data.db.models.service_template import ServiceTemplateModel
    templates = s.query(ServiceTemplateModel).all()
    assert len(templates) == 2  # Still only 2, not 4
    s.close()
