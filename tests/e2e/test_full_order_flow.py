"""
End-to-end test: Vollstaendiger Bestelllebenszyklus vom Login bis zum Export.
Kein Mocking — reale Flask-App gegen echte PostgreSQL-Testdatenbank.
"""
import pytest

from tests.e2e.conftest import auth


class TestFullOrderLifecycle:
    """
    Happy-Path: Login → Katalog → Bestellung erstellen → Artikel hinzufuegen
    → Validieren → Einreichen → Export.
    """

    def test_login_returns_token(self, client):
        """Login im Stub-Modus liefert ein JWT zurueck."""
        resp = client.post("/api/v1/auth/login", json={"username": "test-requester"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "token" in data
        assert data["token"]

    def test_me_endpoint_reflects_logged_in_user(self, client, requester_token):
        """GET /auth/me liefert korrekte Benutzerinformationen zurueck."""
        resp = client.get("/api/v1/auth/me", headers=auth(requester_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["username"] == "test-requester"
        assert "roles" in data

    def test_browse_catalog_after_seeding(self, client, requester_token, seeded_templates):
        """Katalogliste enthaelt beide geseedeten Templates."""
        resp = client.get("/api/v1/catalog/templates", headers=auth(requester_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 2
        slugs = [t["slug"] for t in data["data"]]
        assert "vm-linux" in slugs
        assert "db-postgres" in slugs

    def test_view_template_detail(self, client, requester_token, seeded_templates):
        """Template-Detail liefert vollstaendige Parameter-Definition zurueck."""
        resp = client.get(
            "/api/v1/catalog/templates/vm-linux",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        detail = resp.get_json()
        assert detail["slug"] == "vm-linux"
        assert detail["type"] == "vm"
        assert len(detail["parameters"]) == 3
        param_keys = [p["key"] for p in detail["parameters"]]
        assert "cpu_cores" in param_keys
        assert "ram_gb" in param_keys
        assert "os_type" in param_keys

    def test_create_draft_order(self, client, requester_token, seeded_templates):
        """Eine neue Bestellung startet im Status 'draft' mit generierter Bestellnummer."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={
            "title": "Web-Cluster Q2",
            "business_reason": "Neues Web-Cluster fuer Q2-Launch",
        }, headers=h)
        assert resp.status_code == 201
        order = resp.get_json()
        assert order["status"] == "draft"
        assert order["title"] == "Web-Cluster Q2"
        assert order["order_number"].startswith("ORD-")
        assert order["items"] == []

    def test_add_item_increments_position(self, client, requester_token, seeded_templates):
        """Zwei hinzugefuegte Artikel erhalten aufsteigende Positionswerte."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={"title": "Position Test"}, headers=h)
        order_id = resp.get_json()["id"]

        resp1 = client.post(f"/api/v1/orders/{order_id}/items", json={
            "template_slug": "vm-linux",
            "template_version": "1.0.0",
            "parameters": {"cpu_cores": 2, "ram_gb": 4, "os_type": "ubuntu-22.04"},
        }, headers=h)
        assert resp1.status_code == 201
        item1 = resp1.get_json()["item"]
        assert item1["position"] == 1
        assert item1["display_name"] == "Linux Virtual Machine"
        assert item1["template_slug"] == "vm-linux"

        resp2 = client.post(f"/api/v1/orders/{order_id}/items", json={
            "template_slug": "db-postgres",
            "template_version": "1.0.0",
            "parameters": {"pg_version": "16", "storage_gb": 50},
        }, headers=h)
        assert resp2.status_code == 201
        item2 = resp2.get_json()["item"]
        assert item2["position"] == 2

    def test_full_lifecycle_create_validate_submit_export(
        self, client, requester_token, seeded_templates
    ):
        """
        Vollstaendiger Durchlauf: Bestellung erstellen, zwei Artikel hinzufuegen,
        validieren, einreichen, als Tofu-JSON exportieren.
        """
        h = auth(requester_token)

        # Schritt 1: Draft-Bestellung erstellen
        resp = client.post("/api/v1/orders", json={
            "title": "Web-Cluster Q2",
            "business_reason": "Neues Web-Cluster fuer Q2-Launch",
        }, headers=h)
        assert resp.status_code == 201
        order_id = resp.get_json()["id"]

        # Schritt 2: Linux-VM-Artikel hinzufuegen
        resp = client.post(f"/api/v1/orders/{order_id}/items", json={
            "template_slug": "vm-linux",
            "template_version": "1.0.0",
            "parameters": {"cpu_cores": 4, "ram_gb": 16, "os_type": "ubuntu-22.04"},
        }, headers=h)
        assert resp.status_code == 201

        # Schritt 3: PostgreSQL-Artikel hinzufuegen
        resp = client.post(f"/api/v1/orders/{order_id}/items", json={
            "template_slug": "db-postgres",
            "template_version": "1.0.0",
            "parameters": {"pg_version": "16", "storage_gb": 50},
        }, headers=h)
        assert resp.status_code == 201

        # Schritt 4: Bestellung hat genau 2 Artikel
        resp = client.get(f"/api/v1/orders/{order_id}", headers=h)
        assert resp.status_code == 200
        assert len(resp.get_json()["items"]) == 2

        # Schritt 5: Validierung erfolgreich
        resp = client.post(f"/api/v1/orders/{order_id}/validate", headers=h)
        assert resp.status_code == 200
        validation = resp.get_json()
        assert validation["all_valid"] is True
        assert validation["order_status"] == "validated"
        assert len(validation["item_results"]) == 2

        # Schritt 6: Einreichen
        resp = client.post(f"/api/v1/orders/{order_id}/submit", headers=h)
        assert resp.status_code == 200
        submit = resp.get_json()
        assert submit["status"] in ("submitted", "pending_approval")
        assert submit["item_count"] == 2
        assert submit["order_number"].startswith("ORD-")

        # Schritt 7: Tofu-Export
        resp = client.get(f"/api/v1/orders/{order_id}/export/tofu", headers=h)
        assert resp.status_code == 200
        export = resp.get_json()
        assert export["order_id"] == order_id
        assert len(export["items"]) == 2

        vm_item = next(i for i in export["items"] if i["template_slug"] == "vm-linux")
        assert vm_item["variables"]["cpu_cores"] == 4
        assert vm_item["variables"]["ram_gb"] == 16
        assert vm_item["variables"]["os_type"] == "ubuntu-22.04"
        assert vm_item["module_source"].startswith("git::")

        db_item = next(i for i in export["items"] if i["template_slug"] == "db-postgres")
        assert db_item["variables"]["pg_version"] == "16"
        assert db_item["variables"]["storage_gb"] == 50

    def test_order_list_shows_own_orders(self, client, requester_token, seeded_templates):
        """Liste der Bestellungen gibt mindestens die neu erstellte Bestellung zurueck."""
        h = auth(requester_token)
        client.post("/api/v1/orders", json={"title": "Listed Order"}, headers=h)

        resp = client.get("/api/v1/orders", headers=h)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 1
        assert "items" in data
        titles = [o["title"] for o in data["items"]]
        assert "Listed Order" in titles

    def test_order_status_endpoint(self, client, requester_token, seeded_templates):
        """GET /orders/{id}/status liefert aktuellen Status und Item-Details."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={"title": "Status Test"}, headers=h)
        order_id = resp.get_json()["id"]

        resp = client.get(f"/api/v1/orders/{order_id}/status", headers=h)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["order_id"] == order_id
        assert data["status"] == "draft"


class TestOrderValidationErrors:
    """Prueft, dass die Validierung ungueltige Parameter korrekt zurueckweist."""

    def test_validation_rejects_cpu_above_maximum(
        self, client, requester_token, seeded_templates
    ):
        """Validierung schlaegt fehl, wenn cpu_cores den erlaubten Maximalwert (64) uebersteigt."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={
            "title": "Bad Order",
            "business_reason": "Test",
        }, headers=h)
        order_id = resp.get_json()["id"]

        client.post(f"/api/v1/orders/{order_id}/items", json={
            "template_slug": "vm-linux",
            "template_version": "1.0.0",
            "parameters": {"cpu_cores": 999, "ram_gb": 16, "os_type": "ubuntu-22.04"},
        }, headers=h)

        resp = client.post(f"/api/v1/orders/{order_id}/validate", headers=h)
        assert resp.status_code == 200
        validation = resp.get_json()
        assert validation["all_valid"] is False
        item_result = validation["item_results"][0]
        assert item_result["validation_state"] == "invalid"
        assert len(item_result["violations"]) > 0
        # Verletzung referenziert 'parameter_key': 'cpu_cores'
        violation_param_keys = [v.get("parameter_key") for v in item_result["violations"]]
        assert "cpu_cores" in violation_param_keys

    def test_validation_rejects_invalid_enum_value(
        self, client, requester_token, seeded_templates
    ):
        """Validierung schlaegt fehl, wenn ein Enum-Wert nicht in den erlaubten Optionen enthalten ist."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={"title": "Enum Test"}, headers=h)
        order_id = resp.get_json()["id"]

        client.post(f"/api/v1/orders/{order_id}/items", json={
            "template_slug": "vm-linux",
            "template_version": "1.0.0",
            "parameters": {
                "cpu_cores": 2,
                "ram_gb": 4,
                "os_type": "windows-server-2022",  # nicht in erlaubten Optionen
            },
        }, headers=h)

        resp = client.post(f"/api/v1/orders/{order_id}/validate", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["all_valid"] is False

    def test_validation_rejects_missing_required_parameter(
        self, client, requester_token, seeded_templates
    ):
        """Validierung schlaegt fehl, wenn ein Pflichtfeld (os_type) fehlt."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={
            "title": "Incomplete",
            "business_reason": "Test",
        }, headers=h)
        order_id = resp.get_json()["id"]

        client.post(f"/api/v1/orders/{order_id}/items", json={
            "template_slug": "vm-linux",
            "template_version": "1.0.0",
            "parameters": {"cpu_cores": 4, "ram_gb": 8},  # os_type fehlt
        }, headers=h)

        resp = client.post(f"/api/v1/orders/{order_id}/validate", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["all_valid"] is False

    def test_submit_rejected_if_not_validated(
        self, client, requester_token, seeded_templates
    ):
        """Submit einer nicht-validierten Bestellung gibt HTTP 409 zurueck."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={
            "title": "Draft Only",
            "business_reason": "Test",
        }, headers=h)
        order_id = resp.get_json()["id"]

        resp = client.post(f"/api/v1/orders/{order_id}/submit", headers=h)
        assert resp.status_code == 409

    def test_export_draft_order_rejected(self, client, requester_token, seeded_templates):
        """Export einer Draft-Bestellung gibt HTTP 409 zurueck."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={"title": "Draft Export"}, headers=h)
        order_id = resp.get_json()["id"]

        resp = client.get(f"/api/v1/orders/{order_id}/export/tofu", headers=h)
        assert resp.status_code == 409

    def test_add_item_unknown_template_rejected(
        self, client, requester_token, seeded_templates
    ):
        """Artikel-Hinzufuegen mit unbekanntem Template-Slug gibt HTTP 400 zurueck."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={"title": "Bad Slug"}, headers=h)
        order_id = resp.get_json()["id"]

        resp = client.post(f"/api/v1/orders/{order_id}/items", json={
            "template_slug": "nonexistent-slug",
            "template_version": "1.0.0",
            "parameters": {},
        }, headers=h)
        assert resp.status_code == 400


class TestOrderCrudOperations:
    """Prueft CRUD-Operationen auf Bestellungen und deren Artikeln."""

    def test_update_order_title_in_draft(self, client, requester_token, seeded_templates):
        """Titel einer Draft-Bestellung kann geaendert werden."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={"title": "Original Title"}, headers=h)
        order_id = resp.get_json()["id"]

        resp = client.patch(
            f"/api/v1/orders/{order_id}",
            json={"title": "Updated Title"},
            headers=h,
        )
        assert resp.status_code == 200
        assert resp.get_json()["title"] == "Updated Title"

    def test_update_order_business_reason(self, client, requester_token, seeded_templates):
        """Bestellbegruendung einer Draft-Bestellung kann nachtraeglich gesetzt werden."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={"title": "Reason Test"}, headers=h)
        order_id = resp.get_json()["id"]

        resp = client.patch(
            f"/api/v1/orders/{order_id}",
            json={"business_reason": "Nachtraeglich hinzugefuegt"},
            headers=h,
        )
        assert resp.status_code == 200
        assert resp.get_json()["business_reason"] == "Nachtraeglich hinzugefuegt"

    def test_remove_item_from_order(self, client, requester_token, seeded_templates):
        """Artikel aus Draft-Bestellung entfernen gibt 204 zurueck; Bestellung hat danach 0 Artikel."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={"title": "Remove Test"}, headers=h)
        order_id = resp.get_json()["id"]

        resp = client.post(f"/api/v1/orders/{order_id}/items", json={
            "template_slug": "vm-linux",
            "template_version": "1.0.0",
            "parameters": {"cpu_cores": 2, "ram_gb": 4, "os_type": "ubuntu-22.04"},
        }, headers=h)
        item_id = resp.get_json()["item"]["id"]

        resp = client.delete(
            f"/api/v1/orders/{order_id}/items/{item_id}",
            headers=h,
        )
        assert resp.status_code == 204

        resp = client.get(f"/api/v1/orders/{order_id}", headers=h)
        assert len(resp.get_json()["items"]) == 0

    def test_delete_draft_order(self, client, requester_token, seeded_templates):
        """Loeschen einer Draft-Bestellung gibt 204 zurueck; danach gibt GET 404 zurueck."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={"title": "To Delete"}, headers=h)
        order_id = resp.get_json()["id"]

        resp = client.delete(f"/api/v1/orders/{order_id}", headers=h)
        assert resp.status_code == 204

        resp = client.get(f"/api/v1/orders/{order_id}", headers=h)
        assert resp.status_code == 404

    def test_cannot_update_submitted_order(self, client, requester_token, seeded_templates):
        """PATCH auf eine eingereichte Bestellung gibt HTTP 409 zurueck."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={
            "title": "Locked Order",
            "business_reason": "Test",
        }, headers=h)
        order_id = resp.get_json()["id"]

        client.post(f"/api/v1/orders/{order_id}/items", json={
            "template_slug": "vm-linux",
            "template_version": "1.0.0",
            "parameters": {"cpu_cores": 2, "ram_gb": 4, "os_type": "ubuntu-22.04"},
        }, headers=h)
        client.post(f"/api/v1/orders/{order_id}/validate", headers=h)
        client.post(f"/api/v1/orders/{order_id}/submit", headers=h)

        resp = client.patch(
            f"/api/v1/orders/{order_id}",
            json={"title": "Attempted Change"},
            headers=h,
        )
        assert resp.status_code == 409

    def test_cannot_delete_submitted_order(self, client, requester_token, seeded_templates):
        """DELETE auf eine eingereichte Bestellung gibt HTTP 409 zurueck."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={
            "title": "No Delete After Submit",
            "business_reason": "Test",
        }, headers=h)
        order_id = resp.get_json()["id"]

        client.post(f"/api/v1/orders/{order_id}/items", json={
            "template_slug": "vm-linux",
            "template_version": "1.0.0",
            "parameters": {"cpu_cores": 2, "ram_gb": 4, "os_type": "ubuntu-22.04"},
        }, headers=h)
        client.post(f"/api/v1/orders/{order_id}/validate", headers=h)
        client.post(f"/api/v1/orders/{order_id}/submit", headers=h)

        resp = client.delete(f"/api/v1/orders/{order_id}", headers=h)
        assert resp.status_code == 409

    def test_get_nonexistent_order_returns_404(self, client, requester_token):
        """GET auf eine nicht existierende Order-ID gibt HTTP 404 zurueck."""
        resp = client.get(
            "/api/v1/orders/00000000-0000-0000-0000-000000000000",
            headers=auth(requester_token),
        )
        assert resp.status_code == 404

    def test_update_item_parameters(self, client, requester_token, seeded_templates):
        """Parameter eines Artikels koennen in einer Draft-Bestellung aktualisiert werden."""
        h = auth(requester_token)
        resp = client.post("/api/v1/orders", json={"title": "Update Item Test"}, headers=h)
        order_id = resp.get_json()["id"]

        resp = client.post(f"/api/v1/orders/{order_id}/items", json={
            "template_slug": "vm-linux",
            "template_version": "1.0.0",
            "parameters": {"cpu_cores": 2, "ram_gb": 4, "os_type": "ubuntu-22.04"},
        }, headers=h)
        item_id = resp.get_json()["item"]["id"]

        resp = client.patch(
            f"/api/v1/orders/{order_id}/items/{item_id}",
            json={"parameters": {"cpu_cores": 8, "ram_gb": 32, "os_type": "rhel-9"}},
            headers=h,
        )
        assert resp.status_code == 200
        updated_item = resp.get_json()["item"]
        assert updated_item["parameters"]["cpu_cores"] == 8
        assert updated_item["parameters"]["os_type"] == "rhel-9"
