# tests/unit/test_cmdb_client.py
import os
import pytest
from app.data.clients.cmdb_client import CmdbClient, CmdbStubClient


STUBS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "stubs", "cmdb")


@pytest.fixture
def client():
    return CmdbStubClient(data_path=STUBS_PATH)


class TestCmdbClientInterface:
    def test_base_class_raises_not_implemented(self):
        base = CmdbClient()
        with pytest.raises(NotImplementedError):
            base.get_locations()
        with pytest.raises(NotImplementedError):
            base.get_location("x")
        with pytest.raises(NotImplementedError):
            base.get_networks()
        with pytest.raises(NotImplementedError):
            base.get_network("x")
        with pytest.raises(NotImplementedError):
            base.get_tenants()
        with pytest.raises(NotImplementedError):
            base.get_tenant("x")
        with pytest.raises(NotImplementedError):
            base.get_security_zones()
        with pytest.raises(NotImplementedError):
            base.get_security_zone("x")
        with pytest.raises(NotImplementedError):
            base.get_networks_for_context("x", "y")
        with pytest.raises(NotImplementedError):
            base.health()


class TestCmdbStubClientLocations:
    def test_get_locations_returns_all(self, client):
        locations = client.get_locations()
        assert len(locations) == 3
        ids = [loc["id"] for loc in locations]
        assert "loc-berlin" in ids
        assert "loc-munich" in ids
        assert "loc-hamburg" in ids

    def test_get_location_found(self, client):
        loc = client.get_location("loc-berlin")
        assert loc is not None
        assert loc["name"] == "Berlin HQ"
        assert loc["code"] == "BER"

    def test_get_location_not_found(self, client):
        assert client.get_location("loc-nonexistent") is None


class TestCmdbStubClientNetworks:
    def test_get_networks_all(self, client):
        networks = client.get_networks()
        assert len(networks) == 7

    def test_get_networks_filter_by_location(self, client):
        networks = client.get_networks(location_id="loc-berlin")
        assert len(networks) == 3
        assert all(n["location_id"] == "loc-berlin" for n in networks)

    def test_get_networks_filter_by_security_zone(self, client):
        networks = client.get_networks(security_zone_id="sz-medium")
        assert len(networks) == 3
        assert all(n["security_zone_id"] == "sz-medium" for n in networks)

    def test_get_networks_filter_by_both(self, client):
        networks = client.get_networks(location_id="loc-berlin", security_zone_id="sz-medium")
        assert len(networks) == 1
        assert networks[0]["id"] == "net-ber-dmz"

    def test_get_networks_filter_no_match(self, client):
        networks = client.get_networks(location_id="loc-hamburg", security_zone_id="sz-high")
        assert networks == []

    def test_get_network_found(self, client):
        net = client.get_network("net-ber-dmz")
        assert net is not None
        assert net["name"] == "Berlin DMZ"

    def test_get_network_not_found(self, client):
        assert client.get_network("net-nonexistent") is None


class TestCmdbStubClientTenants:
    def test_get_tenants_returns_all(self, client):
        tenants = client.get_tenants()
        assert len(tenants) == 2
        codes = [t["code"] for t in tenants]
        assert "CORP" in codes
        assert "DEV" in codes

    def test_get_tenant_found(self, client):
        tenant = client.get_tenant("ten-corp")
        assert tenant is not None
        assert tenant["name"] == "Corporate IT"

    def test_get_tenant_not_found(self, client):
        assert client.get_tenant("ten-nonexistent") is None


class TestCmdbStubClientSecurityZones:
    def test_get_security_zones_returns_all(self, client):
        zones = client.get_security_zones()
        assert len(zones) == 3

    def test_get_security_zone_found(self, client):
        zone = client.get_security_zone("sz-high")
        assert zone is not None
        assert zone["name"] == "HIGH"
        assert zone["level"] == 3

    def test_get_security_zone_not_found(self, client):
        assert client.get_security_zone("sz-nonexistent") is None


class TestCmdbStubClientContextNetworks:
    def test_get_networks_for_context(self, client):
        networks = client.get_networks_for_context("loc-berlin", "sz-medium")
        assert len(networks) == 1
        assert networks[0]["id"] == "net-ber-dmz"

    def test_get_networks_for_context_multiple(self, client):
        networks = client.get_networks_for_context("loc-berlin", "sz-low")
        assert len(networks) == 1
        assert networks[0]["id"] == "net-ber-intern"

    def test_get_networks_for_context_no_match(self, client):
        networks = client.get_networks_for_context("loc-hamburg", "sz-high")
        assert networks == []


class TestCmdbStubClientHealth:
    def test_health_returns_true(self, client):
        assert client.health() is True

    def test_health_returns_false_on_bad_path(self):
        bad_client = CmdbStubClient(data_path="/nonexistent/path")
        assert bad_client.health() is False
