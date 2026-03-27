"""
End-to-end test: Rollenbasierte Zugriffskontrolle ueber alle Endpunkte.
Prueft, dass Requester, Admin und unauthentifizierte Anfragen korrekt
behandelt werden.
"""
import pytest

from tests.e2e.conftest import auth


class TestUnauthenticatedAccess:
    """Anfragen ohne Bearer-Token muessen mit HTTP 401 abgelehnt werden."""

    def test_catalog_requires_auth(self, client):
        assert client.get("/api/v1/catalog/templates").status_code == 401

    def test_orders_list_requires_auth(self, client):
        assert client.get("/api/v1/orders").status_code == 401

    def test_orders_create_requires_auth(self, client):
        assert client.post("/api/v1/orders", json={"title": "Test"}).status_code == 401

    def test_admin_dashboard_requires_auth(self, client):
        assert client.get("/api/v1/admin/dashboard").status_code == 401

    def test_admin_audit_log_requires_auth(self, client):
        assert client.get("/api/v1/admin/audit-log").status_code == 401

    def test_cmdb_locations_requires_auth(self, client):
        assert client.get("/api/v1/cmdb/locations").status_code == 401

    def test_context_resolve_requires_auth(self, client):
        resp = client.post("/api/v1/context/resolve", json={
            "location_id": "loc-berlin",
            "tenant_id": "ten-corp",
            "security_zone_id": "sz-low",
        })
        assert resp.status_code == 401

    def test_invalid_token_rejected(self, client):
        resp = client.get(
            "/api/v1/catalog/templates",
            headers={"Authorization": "Bearer not-a-valid-jwt"},
        )
        assert resp.status_code == 401


class TestRequesterPermissions:
    """Requester darf Bestellungen anlegen, aber keine Admin-Endpunkte aufrufen."""

    def test_requester_can_access_catalog(self, client, requester_token, seeded_templates):
        resp = client.get(
            "/api/v1/catalog/templates",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200

    def test_requester_can_create_order(self, client, requester_token, seeded_templates):
        resp = client.post(
            "/api/v1/orders",
            json={"title": "Requester Order"},
            headers=auth(requester_token),
        )
        assert resp.status_code == 201

    def test_requester_cannot_access_admin_dashboard(self, client, requester_token):
        resp = client.get(
            "/api/v1/admin/dashboard",
            headers=auth(requester_token),
        )
        assert resp.status_code == 403

    def test_requester_cannot_access_admin_audit_log(self, client, requester_token):
        resp = client.get(
            "/api/v1/admin/audit-log",
            headers=auth(requester_token),
        )
        assert resp.status_code == 403

    def test_requester_cannot_access_approval_rules(self, client, requester_token):
        resp = client.get(
            "/api/v1/admin/approval-rules",
            headers=auth(requester_token),
        )
        assert resp.status_code == 403

    def test_requester_cannot_register_template(self, client, requester_token):
        resp = client.post(
            "/api/v1/admin/catalog/templates",
            json={"slug": "unauthorized-template"},
            headers=auth(requester_token),
        )
        assert resp.status_code == 403

    def test_requester_cannot_see_other_users_order(
        self, client, requester_token, admin_token, seeded_templates
    ):
        """Requester hat keinen Zugriff auf Bestellungen anderer Nutzer."""
        # Admin legt eine Bestellung an
        resp = client.post(
            "/api/v1/orders",
            json={"title": "Admin's Private Order"},
            headers=auth(admin_token),
        )
        admin_order_id = resp.get_json()["id"]

        # Requester versucht darauf zuzugreifen
        resp = client.get(
            f"/api/v1/orders/{admin_order_id}",
            headers=auth(requester_token),
        )
        assert resp.status_code == 403

    def test_requester_order_list_is_scoped_to_own_orders(
        self, client, requester_token, admin_token, seeded_templates
    ):
        """Requester sieht in der Liste nur eigene Bestellungen, nicht die des Admins."""
        client.post(
            "/api/v1/orders",
            json={"title": "Admin-Only Order"},
            headers=auth(admin_token),
        )
        client.post(
            "/api/v1/orders",
            json={"title": "My Order"},
            headers=auth(requester_token),
        )

        resp = client.get("/api/v1/orders", headers=auth(requester_token))
        assert resp.status_code == 200
        items = resp.get_json()["items"]
        requester_ids = {o["requester_id"] for o in items}
        # Requester sieht ausschliesslich eigene Bestellungen
        assert requester_ids == {"test-requester"}


class TestAdminPermissions:
    """Admin hat Zugriff auf alle Endpunkte, einschliesslich Admin-Bereiche."""

    def test_admin_can_access_dashboard(self, client, admin_token):
        resp = client.get(
            "/api/v1/admin/dashboard",
            headers=auth(admin_token),
        )
        assert resp.status_code == 200

    def test_admin_can_access_audit_log(self, client, admin_token):
        resp = client.get(
            "/api/v1/admin/audit-log",
            headers=auth(admin_token),
        )
        assert resp.status_code == 200

    def test_admin_can_see_all_orders(
        self, client, requester_token, admin_token, seeded_templates
    ):
        """Admin-Bestellliste enthaelt Bestellungen aller Nutzer."""
        client.post(
            "/api/v1/orders",
            json={"title": "Requester Order"},
            headers=auth(requester_token),
        )
        client.post(
            "/api/v1/orders",
            json={"title": "Admin Order"},
            headers=auth(admin_token),
        )

        resp = client.get("/api/v1/orders", headers=auth(admin_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 2
        requester_ids = {o["requester_id"] for o in data["items"]}
        assert len(requester_ids) > 1

    def test_admin_can_register_template(self, client, admin_token):
        """Admin kann neue Templates im Katalog registrieren."""
        resp = client.post(
            "/api/v1/admin/catalog/templates",
            json={
                "slug": "admin-test-svc",
                "version": "1.0.0",
                "type": "custom",
                "display_name": "Admin Test Service",
                "category": "Test",
                "tofu_module_source": "git::https://gitlab.internal/tofu/admin-test.git",
                "parameters": [
                    {
                        "key": "name",
                        "label": "Name",
                        "type": "string",
                        "required": True,
                        "tofu_variable_name": "name",
                        "display_order": 1,
                        "constraints": {},
                    }
                ],
            },
            headers=auth(admin_token),
        )
        assert resp.status_code == 201
        assert resp.get_json()["slug"] == "admin-test-svc"

    def test_admin_can_view_approval_rules(self, client, admin_token):
        resp = client.get(
            "/api/v1/admin/approval-rules",
            headers=auth(admin_token),
        )
        assert resp.status_code == 200

    def test_admin_can_access_another_users_order(
        self, client, requester_token, admin_token, seeded_templates
    ):
        """Admin kann auf Bestellungen beliebiger Nutzer zugreifen."""
        resp = client.post(
            "/api/v1/orders",
            json={"title": "Requester's Order"},
            headers=auth(requester_token),
        )
        order_id = resp.get_json()["id"]

        resp = client.get(
            f"/api/v1/orders/{order_id}",
            headers=auth(admin_token),
        )
        assert resp.status_code == 200


class TestApproverPermissions:
    """Approver-Rolle erlaubt Zugriff auf Approval-Endpunkte, aber nicht auf Admin-Bereiche."""

    def test_approver_can_list_approvals(self, client, approver_token):
        resp = client.get(
            "/api/v1/approvals",
            headers=auth(approver_token),
        )
        assert resp.status_code == 200

    def test_approver_cannot_access_admin_dashboard(self, client, approver_token):
        resp = client.get(
            "/api/v1/admin/dashboard",
            headers=auth(approver_token),
        )
        assert resp.status_code == 403
