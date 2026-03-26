class TestCmdbLocations:
    def test_list_locations(self, client, requester_headers):
        response = client.get("/api/v1/cmdb/locations", headers=requester_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3

    def test_get_location_by_id(self, client, requester_headers):
        response = client.get("/api/v1/cmdb/locations/loc-berlin", headers=requester_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == "loc-berlin"
        assert data["name"] == "Berlin HQ"

    def test_get_unknown_location(self, client, requester_headers):
        response = client.get("/api/v1/cmdb/locations/loc-nope", headers=requester_headers)
        assert response.status_code == 404


class TestCmdbNetworks:
    def test_list_networks_filtered_by_location(self, client, requester_headers):
        response = client.get(
            "/api/v1/cmdb/networks?location_id=loc-berlin",
            headers=requester_headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3
        assert all(n["location_id"] == "loc-berlin" for n in data)

    def test_list_networks_filtered_by_location_and_zone(self, client, requester_headers):
        response = client.get(
            "/api/v1/cmdb/networks?location_id=loc-berlin&security_zone_id=sz-medium",
            headers=requester_headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["id"] == "net-ber-dmz"

    def test_get_network_by_id(self, client, requester_headers):
        response = client.get("/api/v1/cmdb/networks/net-ber-dmz", headers=requester_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == "net-ber-dmz"
        assert data["cidr"] == "10.10.1.0/24"


class TestCmdbTenants:
    def test_list_tenants(self, client, requester_headers):
        response = client.get("/api/v1/cmdb/tenants", headers=requester_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2


class TestCmdbSecurityZones:
    def test_list_security_zones(self, client, requester_headers):
        response = client.get("/api/v1/cmdb/security-zones", headers=requester_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3


class TestCmdbHealth:
    def test_health(self, client, requester_headers):
        response = client.get("/api/v1/cmdb/health", headers=requester_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert data["mode"] == "stub"
        assert data["entities"]["locations"] == 3
        assert data["entities"]["networks"] == 7
        assert data["entities"]["tenants"] == 2
        assert data["entities"]["security_zones"] == 3


class TestCmdbUnauthenticated:
    def test_unauthenticated_returns_401(self, client):
        response = client.get("/api/v1/cmdb/locations")
        assert response.status_code == 401
