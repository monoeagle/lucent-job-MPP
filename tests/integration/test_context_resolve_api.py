class TestContextResolve:
    def test_resolve_valid_context(self, client, requester_headers):
        response = client.post(
            "/api/v1/context/resolve",
            json={
                "location_id": "loc-berlin",
                "tenant_id": "ten-corp",
                "security_zone_id": "sz-medium",
            },
            headers=requester_headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["location"]["id"] == "loc-berlin"
        assert data["tenant"]["id"] == "ten-corp"
        assert data["security_zone"]["id"] == "sz-medium"
        assert isinstance(data["available_networks"], list)

    def test_resolve_unknown_location(self, client, requester_headers):
        response = client.post(
            "/api/v1/context/resolve",
            json={
                "location_id": "loc-unknown",
                "tenant_id": "ten-corp",
                "security_zone_id": "sz-medium",
            },
            headers=requester_headers,
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "violations" in data
        assert any(v["field"] == "location_id" for v in data["violations"])

    def test_resolve_zone_not_at_location(self, client, requester_headers):
        response = client.post(
            "/api/v1/context/resolve",
            json={
                "location_id": "loc-hamburg",
                "tenant_id": "ten-corp",
                "security_zone_id": "sz-high",
            },
            headers=requester_headers,
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "violations" in data
        assert any(v["field"] == "security_zone_id" for v in data["violations"])

    def test_resolve_missing_location_id(self, client, requester_headers):
        response = client.post(
            "/api/v1/context/resolve",
            json={
                "tenant_id": "ten-corp",
                "security_zone_id": "sz-medium",
            },
            headers=requester_headers,
        )
        assert response.status_code == 400


class TestContextLocations:
    def test_list_locations(self, client, requester_headers):
        response = client.get(
            "/api/v1/context/locations",
            headers=requester_headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3


class TestContextTenants:
    def test_list_tenants(self, client, requester_headers):
        response = client.get(
            "/api/v1/context/tenants",
            headers=requester_headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 2


class TestContextSecurityZones:
    def test_list_security_zones(self, client, requester_headers):
        response = client.get(
            "/api/v1/context/security-zones",
            headers=requester_headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3


class TestContextNetworks:
    def test_list_networks_filtered(self, client, requester_headers):
        response = client.get(
            "/api/v1/context/networks?location_id=loc-berlin&security_zone_id=sz-medium",
            headers=requester_headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1


class TestContextUnauthenticated:
    def test_unauthenticated_returns_401(self, client):
        response = client.post("/api/v1/context/resolve", json={})
        assert response.status_code == 401
