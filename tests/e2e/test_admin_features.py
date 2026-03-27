"""
End-to-end test: Admin-Dashboard, Audit-Log und Approval-Regeln.
"""
import pytest

from tests.e2e.conftest import auth


class TestAdminDashboard:
    """Prueft den Admin-Dashboard-Endpunkt auf korrekte Struktur und Counts."""

    def test_dashboard_returns_required_keys(self, client, admin_token):
        """Admin-Dashboard liefert alle erwarteten Top-Level-Felder zurueck."""
        resp = client.get(
            "/api/v1/admin/dashboard",
            headers=auth(admin_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "order_counts" in data
        assert "system_health" in data
        assert "pending_approvals" in data
        assert "active_resources" in data
        assert "recent_orders" in data

    def test_dashboard_order_counts_all_statuses_present(self, client, admin_token):
        """order_counts enthaelt alle definierten Bestell-Status."""
        resp = client.get(
            "/api/v1/admin/dashboard",
            headers=auth(admin_token),
        )
        counts = resp.get_json()["order_counts"]
        expected_statuses = [
            "draft", "validated", "submitted", "pending_approval",
            "provisioning", "done", "failed",
        ]
        for status in expected_statuses:
            assert status in counts, f"Status '{status}' fehlt in order_counts"

    def test_dashboard_order_counts_include_new_draft(
        self, client, admin_token
    ):
        """Eine neu erstellte Draft-Bestellung erhoet den Zaehler fuer 'draft'."""
        h = auth(admin_token)
        resp_before = client.get("/api/v1/admin/dashboard", headers=h)
        draft_count_before = resp_before.get_json()["order_counts"]["draft"]

        client.post("/api/v1/orders", json={"title": "Dashboard Zaehltest"}, headers=h)

        resp_after = client.get("/api/v1/admin/dashboard", headers=h)
        draft_count_after = resp_after.get_json()["order_counts"]["draft"]
        assert draft_count_after == draft_count_before + 1

    def test_dashboard_system_health_database_ok(self, client, admin_token):
        """system_health.database ist 'ok' wenn die Datenbankverbindung besteht."""
        resp = client.get(
            "/api/v1/admin/dashboard",
            headers=auth(admin_token),
        )
        health = resp.get_json()["system_health"]
        assert health["database"] == "ok"

    def test_dashboard_system_health_cmdb_status(self, client, admin_token):
        """system_health.cmdb ist 'ok' da der CMDB-Stub konfiguriert ist."""
        resp = client.get(
            "/api/v1/admin/dashboard",
            headers=auth(admin_token),
        )
        health = resp.get_json()["system_health"]
        assert "cmdb" in health
        assert health["cmdb"] == "ok"

    def test_dashboard_recent_orders_list(self, client, admin_token):
        """recent_orders ist eine Liste (kann leer sein); enthaelt erstellte Bestellungen."""
        h = auth(admin_token)
        client.post("/api/v1/orders", json={"title": "Recent Order"}, headers=h)

        resp = client.get("/api/v1/admin/dashboard", headers=h)
        recent = resp.get_json()["recent_orders"]
        assert isinstance(recent, list)
        assert len(recent) >= 1
        # Struktur pruefen
        first = recent[0]
        assert "order_id" in first
        assert "order_number" in first
        assert "status" in first

    def test_dashboard_requires_admin_role(self, client, requester_token):
        """Requester erhaelt HTTP 403 beim Zugriff auf das Admin-Dashboard."""
        resp = client.get(
            "/api/v1/admin/dashboard",
            headers=auth(requester_token),
        )
        assert resp.status_code == 403

    def test_dashboard_requires_authentication(self, client):
        """Unauthentifizierter Zugriff auf das Admin-Dashboard gibt HTTP 401 zurueck."""
        resp = client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 401


class TestAuditLog:
    """Prueft den Audit-Log-Endpunkt auf Struktur und Berechtigungen."""

    def test_audit_log_returns_paginated_structure(self, client, admin_token):
        """Audit-Log-Endpunkt liefert paginierte Antwort mit 'items' und 'total'."""
        resp = client.get(
            "/api/v1/admin/audit-log",
            headers=auth(admin_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["items"], list)

    def test_audit_log_item_structure(self, client, admin_token, seeded_templates):
        """Audit-Log-Eintraege enthalten die erwarteten Felder nach einer Aktion."""
        h = auth(admin_token)
        # Aktion ausfuehren, die einen Audit-Log-Eintrag erzeugt
        client.post("/api/v1/orders", json={"title": "Audit Test Order"}, headers=h)

        resp = client.get("/api/v1/admin/audit-log", headers=h)
        items = resp.get_json()["items"]
        if items:
            entry = items[0]
            expected_fields = {"id", "timestamp", "actor_id", "action", "entity_type"}
            for field in expected_fields:
                assert field in entry, f"Feld '{field}' fehlt im Audit-Log-Eintrag"

    def test_audit_log_export_returns_list(self, client, admin_token):
        """Audit-Log-Export gibt eine Liste von Eintraegen zurueck."""
        resp = client.get(
            "/api/v1/admin/audit-log/export",
            headers=auth(admin_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)

    def test_audit_log_requires_admin(self, client, requester_token):
        """Requester erhaelt HTTP 403 beim Zugriff auf den Audit-Log."""
        resp = client.get(
            "/api/v1/admin/audit-log",
            headers=auth(requester_token),
        )
        assert resp.status_code == 403

    def test_audit_log_export_requires_admin(self, client, requester_token):
        """Requester erhaelt HTTP 403 beim Zugriff auf den Audit-Log-Export."""
        resp = client.get(
            "/api/v1/admin/audit-log/export",
            headers=auth(requester_token),
        )
        assert resp.status_code == 403

    def test_audit_log_pagination(self, client, admin_token):
        """Audit-Log respektiert limit und offset Parameter."""
        resp = client.get(
            "/api/v1/admin/audit-log?limit=5&offset=0",
            headers=auth(admin_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert len(data["items"]) <= 5


class TestApprovalRulesAdmin:
    """Prueft die CRUD-Operationen fuer Approval-Regeln."""

    def test_create_approval_rule(self, client, admin_token):
        """Admin kann eine neue Approval-Regel erstellen."""
        resp = client.post(
            "/api/v1/admin/approval-rules",
            json={
                "name": "Kostenregel 500 EUR",
                "rule_type": "cost_threshold",
                "threshold_eur": 500.00,
                "is_active": True,
            },
            headers=auth(admin_token),
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert "id" in data
        assert data["rule_type"] == "cost_threshold"
        assert data["threshold_eur"] == 500.00

    def test_list_approval_rules(self, client, admin_token):
        """Admin kann alle Approval-Regeln auflisten."""
        resp = client.get(
            "/api/v1/admin/approval-rules",
            headers=auth(admin_token),
        )
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_create_and_list_approval_rule(self, client, admin_token):
        """Neu erstellte Approval-Regel erscheint in der Liste."""
        h = auth(admin_token)
        client.post("/api/v1/admin/approval-rules", json={
            "name": "Service-Typ-Regel",
            "rule_type": "service_type",
            "service_type_slug": "vm-linux",
            "is_active": True,
        }, headers=h)

        resp = client.get("/api/v1/admin/approval-rules", headers=h)
        rules = resp.get_json()
        rule_names = [r["name"] for r in rules]
        assert "Service-Typ-Regel" in rule_names

    def test_approval_rules_require_admin(self, client, requester_token):
        """Requester kann keine Approval-Regeln anlegen."""
        resp = client.post(
            "/api/v1/admin/approval-rules",
            json={"name": "Unauthorized", "rule_type": "cost_threshold", "threshold_eur": 100},
            headers=auth(requester_token),
        )
        assert resp.status_code == 403

    def test_approval_settings_endpoint(self, client, admin_token):
        """Admin kann Approval-Einstellungen abrufen."""
        resp = client.get(
            "/api/v1/admin/approval-settings",
            headers=auth(admin_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "default_deadline_hours" in data
        assert "allow_self_approval" in data
