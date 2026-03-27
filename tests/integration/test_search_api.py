# tests/integration/test_search_api.py
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.order_repository import OrderRepository
from app.data.repositories.template_repository import TemplateRepository


@pytest.fixture
def db_session(app):
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def seed_search_data(db_session):
    """Create 2 templates and 2 orders for search tests."""
    tmpl_repo = TemplateRepository(db_session)
    tmpl_repo.create({
        "slug": "vm-linux",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Linux VM",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [],
        "status": "active",
    })
    tmpl_repo.create({
        "slug": "db-postgres",
        "version": "1.0.0",
        "type": "database",
        "display_name": "PostgreSQL Database",
        "category": "Database",
        "tofu_module_source": "git::https://gitlab.internal/tofu/db.git",
        "parameters": [],
        "status": "active",
    })

    order_repo = OrderRepository(db_session)
    order_repo.create_order("test-requester", "Linux VM Bestellung")
    order_repo.create_order("test-requester", "Database Setup")


class TestGlobalSearch:
    def test_search_finds_templates(self, client, db_session, seed_search_data, requester_headers):
        resp = client.get("/api/v1/search?q=linux", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        slugs = [t["slug"] for t in data["templates"]]
        assert "vm-linux" in slugs

    def test_search_finds_orders(self, client, db_session, seed_search_data, requester_headers):
        resp = client.get("/api/v1/search?q=Database", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        titles = [o["title"] for o in data["orders"]]
        assert any("Database" in t for t in titles)

    def test_search_empty_query_returns_empty(self, client, db_session, seed_search_data, requester_headers):
        resp = client.get("/api/v1/search?q=", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["orders"] == []
        assert data["templates"] == []

    def test_search_no_results(self, client, db_session, seed_search_data, requester_headers):
        resp = client.get("/api/v1/search?q=xyzzy_gibberish_42", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["orders"] == []
        assert data["templates"] == []

    def test_search_unauthenticated_returns_401(self, client, db_session):
        resp = client.get("/api/v1/search?q=linux")
        assert resp.status_code == 401
