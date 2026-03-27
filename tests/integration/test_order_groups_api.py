# tests/integration/test_order_groups_api.py
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
def seed_template(db_session):
    repo = TemplateRepository(db_session)
    return repo.create({
        "slug": "vm-linux",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Linux VM",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [
            {
                "key": "cpu_cores", "label": "CPU", "type": "integer",
                "required": True, "tofu_variable_name": "cpu_cores",
                "display_order": 1, "constraints": {"min": 1, "max": 64},
            },
        ],
    })


@pytest.fixture
def seed_order(db_session):
    repo = OrderRepository(db_session)
    return repo.create_order("test-requester", "My Draft Order", "Need it", "2026-06-01")


@pytest.fixture
def seed_submitted_order(db_session):
    repo = OrderRepository(db_session)
    order = repo.create_order("test-requester", "Submitted Order", "Reason")
    repo.update_order_status(order.id, "validated")
    repo.update_order_status(order.id, "submitted")
    return order


# ── Create Group ─────────────────────────────────────────────


class TestCreateGroup:
    def test_create_group_returns_201(
        self, client, db_session, seed_order, requester_headers,
    ):
        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/groups",
            headers=requester_headers,
            json={"name": "Web-Cluster", "description": "Frontend VMs"},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["group"]["name"] == "Web-Cluster"
        assert data["group"]["description"] == "Frontend VMs"
        assert data["group"]["order_id"] == seed_order.id
        assert data["group"]["position"] == 1

    def test_create_group_without_description(
        self, client, db_session, seed_order, requester_headers,
    ):
        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/groups",
            headers=requester_headers,
            json={"name": "DB-Cluster"},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["group"]["name"] == "DB-Cluster"
        assert data["group"]["description"] is None

    def test_create_group_non_draft_returns_409(
        self, client, db_session, seed_submitted_order, requester_headers,
    ):
        resp = client.post(
            f"/api/v1/orders/{seed_submitted_order.id}/groups",
            headers=requester_headers,
            json={"name": "Cluster"},
        )
        assert resp.status_code == 409

    def test_create_group_duplicate_name_returns_409(
        self, client, db_session, seed_order, requester_headers,
    ):
        client.post(
            f"/api/v1/orders/{seed_order.id}/groups",
            headers=requester_headers,
            json={"name": "Web-Cluster"},
        )
        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/groups",
            headers=requester_headers,
            json={"name": "Web-Cluster"},
        )
        assert resp.status_code == 409

    def test_create_group_order_not_found_returns_404(
        self, client, db_session, requester_headers,
    ):
        resp = client.post(
            "/api/v1/orders/nonexistent-id/groups",
            headers=requester_headers,
            json={"name": "Cluster"},
        )
        assert resp.status_code == 404

    def test_create_group_max_20_returns_400(
        self, client, db_session, seed_order, requester_headers,
    ):
        for i in range(20):
            client.post(
                f"/api/v1/orders/{seed_order.id}/groups",
                headers=requester_headers,
                json={"name": f"Group-{i}"},
            )
        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/groups",
            headers=requester_headers,
            json={"name": "Group-21"},
        )
        assert resp.status_code == 400


# ── Update Group ─────────────────────────────────────────────


class TestUpdateGroup:
    def test_update_group_returns_200(
        self, client, db_session, seed_order, requester_headers,
    ):
        create_resp = client.post(
            f"/api/v1/orders/{seed_order.id}/groups",
            headers=requester_headers,
            json={"name": "Old Name"},
        )
        group_id = create_resp.get_json()["group"]["id"]

        resp = client.patch(
            f"/api/v1/orders/{seed_order.id}/groups/{group_id}",
            headers=requester_headers,
            json={"name": "New Name", "description": "Updated"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["group"]["name"] == "New Name"
        assert data["group"]["description"] == "Updated"

    def test_update_group_non_draft_returns_409(
        self, client, db_session, seed_submitted_order, requester_headers,
    ):
        resp = client.patch(
            f"/api/v1/orders/{seed_submitted_order.id}/groups/fake-id",
            headers=requester_headers,
            json={"name": "New"},
        )
        assert resp.status_code == 409


# ── Delete Group ─────────────────────────────────────────────


class TestDeleteGroup:
    def test_delete_empty_group_returns_204(
        self, client, db_session, seed_order, requester_headers,
    ):
        create_resp = client.post(
            f"/api/v1/orders/{seed_order.id}/groups",
            headers=requester_headers,
            json={"name": "Empty Group"},
        )
        group_id = create_resp.get_json()["group"]["id"]

        resp = client.delete(
            f"/api/v1/orders/{seed_order.id}/groups/{group_id}",
            headers=requester_headers,
        )
        assert resp.status_code == 204

    def test_delete_non_empty_group_returns_409(
        self, client, db_session, seed_order, seed_template, requester_headers,
    ):
        # Create group
        create_resp = client.post(
            f"/api/v1/orders/{seed_order.id}/groups",
            headers=requester_headers,
            json={"name": "Has Items"},
        )
        group_id = create_resp.get_json()["group"]["id"]

        # Add item and assign to group
        item_resp = client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
            },
        )
        item_id = item_resp.get_json()["item"]["id"]

        # Assign item to group
        client.patch(
            f"/api/v1/orders/{seed_order.id}/items/{item_id}",
            headers=requester_headers,
            json={"group_id": group_id},
        )

        # Try to delete non-empty group
        resp = client.delete(
            f"/api/v1/orders/{seed_order.id}/groups/{group_id}",
            headers=requester_headers,
        )
        assert resp.status_code == 409

    def test_delete_group_non_draft_returns_409(
        self, client, db_session, seed_submitted_order, requester_headers,
    ):
        resp = client.delete(
            f"/api/v1/orders/{seed_submitted_order.id}/groups/fake-id",
            headers=requester_headers,
        )
        assert resp.status_code == 409


# ── Reorder Groups ───────────────────────────────────────────


class TestReorderGroups:
    def test_reorder_groups_returns_200(
        self, client, db_session, seed_order, requester_headers,
    ):
        r1 = client.post(
            f"/api/v1/orders/{seed_order.id}/groups",
            headers=requester_headers,
            json={"name": "Group-A"},
        )
        r2 = client.post(
            f"/api/v1/orders/{seed_order.id}/groups",
            headers=requester_headers,
            json={"name": "Group-B"},
        )
        gid1 = r1.get_json()["group"]["id"]
        gid2 = r2.get_json()["group"]["id"]

        resp = client.put(
            f"/api/v1/orders/{seed_order.id}/groups/reorder",
            headers=requester_headers,
            json={
                "positions": [
                    {"group_id": gid1, "position": 2},
                    {"group_id": gid2, "position": 1},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        groups_by_id = {g["id"]: g for g in data["groups"]}
        assert groups_by_id[gid1]["position"] == 2
        assert groups_by_id[gid2]["position"] == 1

    def test_reorder_groups_non_draft_returns_409(
        self, client, db_session, seed_submitted_order, requester_headers,
    ):
        resp = client.put(
            f"/api/v1/orders/{seed_submitted_order.id}/groups/reorder",
            headers=requester_headers,
            json={"positions": []},
        )
        assert resp.status_code == 409


# ── Assign Item to Group ─────────────────────────────────────


class TestAssignItemToGroup:
    def test_assign_item_to_group_returns_200(
        self, client, db_session, seed_order, seed_template, requester_headers,
    ):
        # Create group
        group_resp = client.post(
            f"/api/v1/orders/{seed_order.id}/groups",
            headers=requester_headers,
            json={"name": "Web-Cluster"},
        )
        group_id = group_resp.get_json()["group"]["id"]

        # Add item
        item_resp = client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
            },
        )
        item_id = item_resp.get_json()["item"]["id"]

        # Assign to group
        resp = client.patch(
            f"/api/v1/orders/{seed_order.id}/items/{item_id}",
            headers=requester_headers,
            json={"group_id": group_id},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["item"]["group_id"] == group_id

    def test_unassign_item_from_group_returns_200(
        self, client, db_session, seed_order, seed_template, requester_headers,
    ):
        # Create group
        group_resp = client.post(
            f"/api/v1/orders/{seed_order.id}/groups",
            headers=requester_headers,
            json={"name": "Web-Cluster"},
        )
        group_id = group_resp.get_json()["group"]["id"]

        # Add item
        item_resp = client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
            },
        )
        item_id = item_resp.get_json()["item"]["id"]

        # Assign to group
        client.patch(
            f"/api/v1/orders/{seed_order.id}/items/{item_id}",
            headers=requester_headers,
            json={"group_id": group_id},
        )

        # Unassign
        resp = client.patch(
            f"/api/v1/orders/{seed_order.id}/items/{item_id}",
            headers=requester_headers,
            json={"group_id": None},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["item"]["group_id"] is None


# ── GET Order includes groups ────────────────────────────────


class TestGetOrderWithGroups:
    def test_get_order_includes_groups(
        self, client, db_session, seed_order, seed_template, requester_headers,
    ):
        # Create group
        group_resp = client.post(
            f"/api/v1/orders/{seed_order.id}/groups",
            headers=requester_headers,
            json={"name": "Web-Cluster"},
        )
        group_id = group_resp.get_json()["group"]["id"]

        # Add item and assign to group
        item_resp = client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
            },
        )
        item_id = item_resp.get_json()["item"]["id"]
        client.patch(
            f"/api/v1/orders/{seed_order.id}/items/{item_id}",
            headers=requester_headers,
            json={"group_id": group_id},
        )

        # Add ungrouped item
        client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 2},
            },
        )

        # GET order
        resp = client.get(
            f"/api/v1/orders/{seed_order.id}",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "groups" in data
        assert len(data["groups"]) == 1
        assert data["groups"][0]["name"] == "Web-Cluster"
        assert len(data["groups"][0]["items"]) == 1
        assert "ungrouped_items" in data
        assert len(data["ungrouped_items"]) == 1
