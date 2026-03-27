"""
End-to-end test: CMDB-Browsing und Kontext-Aufloesung.
Testet den Stub-CMDB-Client gegen die tatsaechlichen Stub-Datendateien unter stubs/cmdb/.
"""
import pytest

from tests.e2e.conftest import auth


class TestCmdbBrowsing:
    """
    Prueft CMDB-Endpunkte (Locations, Netzwerke, Tenants, Security Zones).
    Stub-Daten: 3 Locations, 7 Netzwerke, 2 Tenants, 3 Security Zones.
    """

    def test_list_locations_returns_all_three(self, client, requester_token):
        """Stub-Daten enthalten genau 3 Standorte."""
        resp = client.get(
            "/api/v1/cmdb/locations",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        locations = resp.get_json()
        assert len(locations) == 3
        ids = [loc["id"] for loc in locations]
        assert "loc-berlin" in ids
        assert "loc-munich" in ids
        assert "loc-hamburg" in ids

    def test_get_single_location(self, client, requester_token):
        """Einzelner Standort kann per ID abgerufen werden."""
        resp = client.get(
            "/api/v1/cmdb/locations/loc-berlin",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        location = resp.get_json()
        assert location["id"] == "loc-berlin"
        assert location["name"] == "Berlin HQ"
        assert location["code"] == "BER"

    def test_get_nonexistent_location_returns_404(self, client, requester_token):
        """Zugriff auf einen nicht existierenden Standort gibt HTTP 404 zurueck."""
        resp = client.get(
            "/api/v1/cmdb/locations/loc-nonexistent",
            headers=auth(requester_token),
        )
        assert resp.status_code == 404

    def test_list_all_networks(self, client, requester_token):
        """Alle Netzwerke werden ohne Filter zurueckgegeben."""
        resp = client.get(
            "/api/v1/cmdb/networks",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        networks = resp.get_json()
        assert len(networks) >= 6

    def test_list_networks_filtered_by_location(self, client, requester_token):
        """Netzwerke gefiltert nach location_id enthalten nur Netzwerke dieses Standorts."""
        resp = client.get(
            "/api/v1/cmdb/networks?location_id=loc-berlin",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        networks = resp.get_json()
        assert len(networks) >= 1
        assert all(n["location_id"] == "loc-berlin" for n in networks)
        # Berlin hat 3 Netzwerke: DMZ, Internal, Mgmt
        assert len(networks) == 3

    def test_list_networks_filtered_by_security_zone(self, client, requester_token):
        """Netzwerke gefiltert nach security_zone_id enthalten nur Netzwerke dieser Zone."""
        resp = client.get(
            "/api/v1/cmdb/networks?security_zone_id=sz-low",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        networks = resp.get_json()
        assert len(networks) >= 1
        assert all(n["security_zone_id"] == "sz-low" for n in networks)

    def test_list_security_zones_returns_all_three(self, client, requester_token):
        """Stub-Daten enthalten genau 3 Security Zones."""
        resp = client.get(
            "/api/v1/cmdb/security-zones",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        zones = resp.get_json()
        assert len(zones) == 3
        zone_ids = [z["id"] for z in zones]
        assert "sz-low" in zone_ids
        assert "sz-medium" in zone_ids
        assert "sz-high" in zone_ids

    def test_get_single_security_zone(self, client, requester_token):
        """Einzelne Security Zone kann per ID abgerufen werden."""
        resp = client.get(
            "/api/v1/cmdb/security-zones/sz-high",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        zone = resp.get_json()
        assert zone["id"] == "sz-high"
        assert zone["level"] == 3

    def test_list_tenants(self, client, requester_token):
        """Stub-Daten enthalten Tenants (mindestens ten-corp und ten-dev)."""
        resp = client.get(
            "/api/v1/cmdb/tenants",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        tenants = resp.get_json()
        assert len(tenants) >= 2
        tenant_ids = [t["id"] for t in tenants]
        assert "ten-corp" in tenant_ids
        assert "ten-dev" in tenant_ids

    def test_cmdb_health_returns_ok(self, client, requester_token):
        """CMDB-Health-Endpunkt meldet Status ok im Stub-Modus."""
        resp = client.get(
            "/api/v1/cmdb/health",
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["mode"] == "stub"
        assert "entities" in data


class TestContextResolution:
    """Prueft den /context/resolve-Endpunkt mit gueltigem und ungueltigem Kontext."""

    def test_resolve_valid_context_berlin_corp_low(self, client, requester_token):
        """Gueltige Kontext-Aufloesung: Berlin, Corporate IT, Security Zone Low."""
        resp = client.post(
            "/api/v1/context/resolve",
            json={
                "location_id": "loc-berlin",
                "tenant_id": "ten-corp",
                "security_zone_id": "sz-low",
            },
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        ctx = resp.get_json()
        assert ctx["location"]["id"] == "loc-berlin"
        assert ctx["location"]["name"] == "Berlin HQ"
        assert ctx["tenant"]["id"] == "ten-corp"
        assert ctx["security_zone"]["id"] == "sz-low"
        assert len(ctx["available_networks"]) >= 1

    def test_resolve_valid_context_berlin_corp_medium(self, client, requester_token):
        """Gueltige Kontext-Aufloesung: Berlin, Corporate IT, Security Zone Medium (DMZ)."""
        resp = client.post(
            "/api/v1/context/resolve",
            json={
                "location_id": "loc-berlin",
                "tenant_id": "ten-corp",
                "security_zone_id": "sz-medium",
            },
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        ctx = resp.get_json()
        assert ctx["security_zone"]["id"] == "sz-medium"

    def test_resolve_returns_available_networks_for_zone(self, client, requester_token):
        """Aufgeloester Kontext enthaelt die verfuegbaren Netzwerke der Zone am Standort."""
        resp = client.post(
            "/api/v1/context/resolve",
            json={
                "location_id": "loc-berlin",
                "tenant_id": "ten-corp",
                "security_zone_id": "sz-high",
            },
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        ctx = resp.get_json()
        network_ids = [n["id"] for n in ctx["available_networks"]]
        # Berlin Mgmt ist das einzige High-Security-Netzwerk in Berlin
        assert "net-ber-mgmt" in network_ids

    def test_resolve_invalid_location_returns_400(self, client, requester_token):
        """Nicht existierender Standort fuehrt zu HTTP 400 mit Fehlercode."""
        resp = client.post(
            "/api/v1/context/resolve",
            json={
                "location_id": "loc-nonexistent",
                "tenant_id": "ten-corp",
                "security_zone_id": "sz-low",
            },
            headers=auth(requester_token),
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error_code" in data or "violations" in data

    def test_resolve_invalid_tenant_returns_400(self, client, requester_token):
        """Nicht existierender Tenant fuehrt zu HTTP 400."""
        resp = client.post(
            "/api/v1/context/resolve",
            json={
                "location_id": "loc-berlin",
                "tenant_id": "ten-nonexistent",
                "security_zone_id": "sz-low",
            },
            headers=auth(requester_token),
        )
        assert resp.status_code == 400

    def test_resolve_zone_not_available_at_location_returns_400(self, client, requester_token):
        """
        Security Zone 'sz-high' hat kein Netzwerk in Hamburg — Aufloesung gibt HTTP 400 zurueck.
        Laut Stub-Daten: sz-high existiert nur in Berlin (net-ber-mgmt).
        """
        resp = client.post(
            "/api/v1/context/resolve",
            json={
                "location_id": "loc-hamburg",
                "tenant_id": "ten-corp",
                "security_zone_id": "sz-high",
            },
            headers=auth(requester_token),
        )
        assert resp.status_code == 400
        data = resp.get_json()
        # Violations enthalten Hinweis auf security_zone_id
        if "violations" in data:
            fields = [v.get("field") for v in data["violations"]]
            assert "security_zone_id" in fields

    def test_resolve_missing_required_fields_returns_400(self, client, requester_token):
        """Fehlende Pflichtfelder in der Kontext-Aufloesung geben HTTP 400 zurueck."""
        resp = client.post(
            "/api/v1/context/resolve",
            json={"location_id": "loc-berlin"},  # tenant_id und security_zone_id fehlen
            headers=auth(requester_token),
        )
        assert resp.status_code == 400

    def test_resolve_with_specific_network(self, client, requester_token):
        """Kontext mit spezifischer network_id wird korrekt aufgeloest."""
        resp = client.post(
            "/api/v1/context/resolve",
            json={
                "location_id": "loc-berlin",
                "tenant_id": "ten-corp",
                "security_zone_id": "sz-low",
                "network_id": "net-ber-intern",
            },
            headers=auth(requester_token),
        )
        assert resp.status_code == 200
        ctx = resp.get_json()
        assert ctx["network"]["id"] == "net-ber-intern"

    def test_resolve_network_wrong_location_returns_400(self, client, requester_token):
        """Netzwerk aus anderem Standort fuehrt zu HTTP 400."""
        resp = client.post(
            "/api/v1/context/resolve",
            json={
                "location_id": "loc-munich",
                "tenant_id": "ten-corp",
                "security_zone_id": "sz-low",
                "network_id": "net-ber-intern",  # Berlin-Netzwerk, nicht Munich
            },
            headers=auth(requester_token),
        )
        assert resp.status_code == 400
