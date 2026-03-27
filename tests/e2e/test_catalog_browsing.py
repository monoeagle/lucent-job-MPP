"""
End-to-end test: Katalog-Browsing, Filterung, Template-Details und Admin-Operationen.
"""
import pytest

from tests.e2e.conftest import auth


class TestCatalogBrowsing:
    """Prueft die oeffentlichen (authentifizierten) Katalog-Endpunkte."""

    def test_list_all_templates_returns_correct_total(
        self, client, requester_token, seeded_templates
    ):
        """Gesamtanzahl der Templates stimmt nach dem Seeding."""
        resp = client.get(
            "/api/v1/catalog/templates",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 2
        assert len(data["data"]) == 2

    def test_list_templates_empty_without_seeding(self, client, requester_token):
        """Ohne geseedete Templates ist die Liste leer."""
        resp = client.get(
            "/api/v1/catalog/templates",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 0
        assert data["data"] == []

    def test_filter_by_type_vm(self, client, requester_token, seeded_templates):
        """Filter nach type=vm gibt nur VM-Templates zurueck."""
        resp = client.get(
            "/api/v1/catalog/templates?type=vm",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 1
        assert data["data"][0]["type"] == "vm"
        assert data["data"][0]["slug"] == "vm-linux"

    def test_filter_by_type_database(self, client, requester_token, seeded_templates):
        """Filter nach type=database gibt nur Datenbank-Templates zurueck."""
        resp = client.get(
            "/api/v1/catalog/templates?type=database",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 1
        assert data["data"][0]["slug"] == "db-postgres"

    def test_filter_by_category_compute(self, client, requester_token, seeded_templates):
        """Filter nach category=Compute gibt nur Templates der Kategorie 'Compute' zurueck."""
        resp = client.get(
            "/api/v1/catalog/templates?category=Compute",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 1
        assert data["data"][0]["slug"] == "vm-linux"

    def test_filter_by_category_database(self, client, requester_token, seeded_templates):
        """Filter nach category=Database gibt nur Datenbank-Templates zurueck."""
        resp = client.get(
            "/api/v1/catalog/templates?category=Database",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 1
        assert data["data"][0]["slug"] == "db-postgres"

    def test_search_by_keyword_linux(self, client, requester_token, seeded_templates):
        """Volltextsuche nach 'linux' findet das Linux-VM-Template."""
        resp = client.get(
            "/api/v1/catalog/templates?q=linux",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 1
        assert "linux" in data["data"][0]["display_name"].lower()

    def test_search_returns_empty_for_unknown_term(
        self, client, requester_token, seeded_templates
    ):
        """Suche nach einem nicht vorhandenen Begriff liefert eine leere Liste."""
        resp = client.get(
            "/api/v1/catalog/templates?q=kubernetes-operator-xyz",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        assert resp.get_json()["total"] == 0

    def test_template_detail_includes_all_parameters(
        self, client, requester_token, seeded_templates
    ):
        """Template-Detail enthaelt alle Parameter-Definitionen mit Constraints."""
        resp = client.get(
            "/api/v1/catalog/templates/vm-linux",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        detail = resp.get_json()
        assert detail["slug"] == "vm-linux"
        assert "parameters" in detail
        param_keys = [p["key"] for p in detail["parameters"]]
        assert "cpu_cores" in param_keys
        assert "ram_gb" in param_keys
        assert "os_type" in param_keys
        # Constraint-Werte pruefen
        cpu_param = next(p for p in detail["parameters"] if p["key"] == "cpu_cores")
        assert cpu_param["constraints"]["min"] == 1
        assert cpu_param["constraints"]["max"] == 64

    def test_template_detail_estimated_cost(
        self, client, requester_token, seeded_templates
    ):
        """Template-Detail enthaelt die geschaetzten monatlichen Kosten."""
        resp = client.get(
            "/api/v1/catalog/templates/vm-linux",
            headers=auth(requester_token),
        )
        data = resp.get_json()
        assert data["estimated_cost_eur_per_month"] == 85.00

    def test_categories_endpoint_returns_seeded_categories(
        self, client, requester_token, seeded_templates
    ):
        """Kategorien-Endpunkt liefert alle vorhandenen Kategorien mit Template-Anzahl."""
        resp = client.get(
            "/api/v1/catalog/categories",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        # Antwort ist eine Liste von {"name": ..., "template_count": ...}
        categories = resp.get_json()
        assert isinstance(categories, list)
        names = [c["name"] for c in categories]
        assert "Compute" in names
        assert "Database" in names
        # Jede Kategorie hat genau 1 Template
        for cat in categories:
            assert cat["template_count"] == 1

    def test_nonexistent_template_returns_404(self, client, requester_token, seeded_templates):
        """Zugriff auf ein nicht existierendes Template gibt HTTP 404 zurueck."""
        resp = client.get(
            "/api/v1/catalog/templates/nonexistent-slug-xyz",
            headers=auth(requester_token),
        )
        assert resp.status_code == 404

    def test_validate_valid_parameters_against_template(
        self, client, requester_token, seeded_templates
    ):
        """Gueltiger Parameter-Satz gegen Template validieren gibt valid=True zurueck."""
        resp = client.post(
            "/api/v1/catalog/templates/vm-linux/validate",
            json={"parameters": {"cpu_cores": 4, "ram_gb": 16, "os_type": "ubuntu-22.04"}},
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        result = resp.get_json()
        assert result["valid"] is True
        assert result["violations"] == []

    def test_validate_invalid_parameters_against_template(
        self, client, requester_token, seeded_templates
    ):
        """Ungueltige Parameter gegen Template validieren gibt valid=False mit Violations zurueck."""
        resp = client.post(
            "/api/v1/catalog/templates/vm-linux/validate",
            json={"parameters": {"cpu_cores": 999, "ram_gb": 16, "os_type": "ubuntu-22.04"}},
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        result = resp.get_json()
        assert result["valid"] is False
        assert len(result["violations"]) > 0

    def test_list_template_versions(self, client, requester_token, seeded_templates):
        """Versions-Endpunkt gibt alle registrierten Versionen eines Templates zurueck."""
        resp = client.get(
            "/api/v1/catalog/templates/vm-linux/versions",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        versions = resp.get_json()
        assert isinstance(versions, list)
        assert len(versions) >= 1
        version_numbers = [v["version"] for v in versions]
        assert "1.0.0" in version_numbers

    def test_pagination_limit(self, client, requester_token, seeded_templates):
        """Pagination mit limit=1 gibt genau einen Eintrag zurueck, total bleibt 2."""
        resp = client.get(
            "/api/v1/catalog/templates?limit=1",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 2
        assert len(data["data"]) == 1
        assert data["limit"] == 1


class TestCatalogAdminOperations:
    """Prueft Admin-Operationen am Katalog: Registrierung und Status-Verwaltung."""

    def test_register_template_returns_201_with_id(self, client, admin_token):
        """Neues Template wird mit HTTP 201 und zugewiesener ID registriert."""
        resp = client.post(
            "/api/v1/admin/catalog/templates",
            json={
                "slug": "custom-service",
                "version": "1.0.0",
                "type": "custom",
                "display_name": "Custom Service",
                "category": "Misc",
                "tofu_module_source": "git::https://gitlab.internal/tofu/custom.git",
                "parameters": [
                    {
                        "key": "env_name",
                        "label": "Environment",
                        "type": "string",
                        "required": True,
                        "tofu_variable_name": "env_name",
                        "display_order": 1,
                        "constraints": {},
                    }
                ],
            },
            headers=auth(admin_token),
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert "id" in data
        assert data["slug"] == "custom-service"
        assert data["status"] == "active"

    def test_register_duplicate_template_returns_409(self, client, admin_token, seeded_templates):
        """Doppelte Registrierung desselben slug+version gibt HTTP 409 zurueck."""
        # vm-linux/1.0.0 wurde bereits durch seeded_templates registriert —
        # dieselbe Kombination muss 409 zurueckliefern (nicht 400 durch Validierung)
        from tests.e2e.conftest import LINUX_VM
        resp = client.post(
            "/api/v1/admin/catalog/templates",
            json=LINUX_VM,  # identischer slug + version wie im Seed
            headers=auth(admin_token),
        )
        assert resp.status_code == 409

    def test_register_and_deprecate_template(self, client, admin_token):
        """Template v1 wird erfolgreich auf 'deprecated' gesetzt, sobald v2 aktiv ist."""
        h = auth(admin_token)

        _minimal_param = [
            {
                "key": "instance_name",
                "label": "Instance Name",
                "type": "string",
                "required": True,
                "tofu_variable_name": "instance_name",
                "display_order": 1,
                "constraints": {},
            }
        ]

        # v1 registrieren
        resp = client.post("/api/v1/admin/catalog/templates", json={
            "slug": "lifecycle-svc",
            "version": "1.0.0",
            "type": "custom",
            "display_name": "Lifecycle Service v1",
            "category": "Test",
            "tofu_module_source": "git::https://gitlab.internal/tofu/lifecycle.git?ref=v1",
            "parameters": _minimal_param,
        }, headers=h)
        assert resp.status_code == 201
        v1_id = resp.get_json()["id"]

        # v2 registrieren
        resp = client.post("/api/v1/admin/catalog/templates", json={
            "slug": "lifecycle-svc",
            "version": "2.0.0",
            "type": "custom",
            "display_name": "Lifecycle Service v2",
            "category": "Test",
            "tofu_module_source": "git::https://gitlab.internal/tofu/lifecycle.git?ref=v2",
            "parameters": _minimal_param,
        }, headers=h)
        assert resp.status_code == 201
        v2_id = resp.get_json()["id"]

        # v1 deprecaten mit Verweis auf v2
        resp = client.patch(
            f"/api/v1/admin/catalog/templates/{v1_id}/status",
            json={"status": "deprecated", "deprecated_by": v2_id},
            headers=h,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "deprecated"
        assert data["deprecated_by"] == v2_id

    def test_cannot_deprecate_without_active_replacement(self, client, admin_token, seeded_templates):
        """Deprecation schlaegt fehl, wenn der Nachfolger nicht aktiv ist."""
        h = auth(admin_token)
        # vm-linux mit sich selbst als Nachfolger deprecaten (ID != aktives Template)
        resp = client.patch(
            f"/api/v1/admin/catalog/templates/{seeded_templates[0]['id']}/status",
            json={"status": "deprecated", "deprecated_by": "nonexistent-id"},
            headers=h,
        )
        assert resp.status_code == 400
