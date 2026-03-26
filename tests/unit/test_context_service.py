# tests/unit/test_context_service.py
import pytest
from unittest.mock import MagicMock
from app.services.context_service import ContextService
from app.domain.context import ResolvedContext


# ── fixtures ────────────────────────────────────────────────────────

LOCATION = {"id": "loc-berlin", "name": "Berlin HQ", "code": "BER", "region": "DE-NORTH"}
TENANT = {"id": "ten-corp", "name": "Corporate IT", "code": "CORP"}
ZONE = {"id": "sz-medium", "name": "MEDIUM", "level": 2}
NETWORK = {"id": "net-ber-dmz", "name": "Berlin DMZ", "cidr": "10.10.1.0/24",
           "location_id": "loc-berlin", "security_zone_id": "sz-medium"}
NETWORK_OTHER_LOC = {"id": "net-muc-dmz", "name": "Munich DMZ", "cidr": "10.20.1.0/24",
                     "location_id": "loc-munich", "security_zone_id": "sz-medium"}
NETWORK_OTHER_ZONE = {"id": "net-ber-intern", "name": "Berlin Internal", "cidr": "10.10.10.0/24",
                      "location_id": "loc-berlin", "security_zone_id": "sz-low"}


@pytest.fixture
def cmdb():
    mock = MagicMock()
    mock.get_location.return_value = LOCATION
    mock.get_tenant.return_value = TENANT
    mock.get_security_zone.return_value = ZONE
    mock.get_network.return_value = NETWORK
    mock.get_networks_for_context.return_value = [NETWORK]
    return mock


@pytest.fixture
def tenant_repo():
    mock = MagicMock()
    mock.get_allowed_tenant_ids.return_value = None  # no restrictions
    return mock


@pytest.fixture
def svc(cmdb):
    return ContextService(cmdb_client=cmdb)


@pytest.fixture
def svc_with_tenant_repo(cmdb, tenant_repo):
    return ContextService(cmdb_client=cmdb, tenant_repo=tenant_repo)


# ── resolve_context: happy path ────────────────────────────────────

class TestResolveContextValid:
    def test_resolve_valid_context_without_network(self, svc, cmdb):
        result = svc.resolve_context("loc-berlin", "ten-corp", "sz-medium")

        assert isinstance(result, ResolvedContext)
        assert result.location == LOCATION
        assert result.tenant == TENANT
        assert result.security_zone == ZONE
        assert result.network is None
        assert result.available_networks == [NETWORK]

    def test_resolve_valid_context_with_network(self, svc, cmdb):
        result = svc.resolve_context("loc-berlin", "ten-corp", "sz-medium",
                                     network_id="net-ber-dmz")

        assert result.network == NETWORK
        assert result.available_networks == [NETWORK]

    def test_cmdb_calls(self, svc, cmdb):
        svc.resolve_context("loc-berlin", "ten-corp", "sz-medium")

        cmdb.get_location.assert_called_once_with("loc-berlin")
        cmdb.get_tenant.assert_called_once_with("ten-corp")
        cmdb.get_security_zone.assert_called_once_with("sz-medium")
        cmdb.get_networks_for_context.assert_called_once_with("loc-berlin", "sz-medium")


# ── resolve_context: validation errors ─────────────────────────────

class TestResolveContextValidationErrors:
    def test_location_not_found(self, svc, cmdb):
        cmdb.get_location.return_value = None

        with pytest.raises(ContextService.ContextValidationError) as exc_info:
            svc.resolve_context("loc-invalid", "ten-corp", "sz-medium")

        violations = exc_info.value.violations
        assert len(violations) == 1
        assert violations[0]["field"] == "location_id"
        assert "not found" in violations[0]["message"].lower()

    def test_tenant_not_found(self, svc, cmdb):
        cmdb.get_tenant.return_value = None

        with pytest.raises(ContextService.ContextValidationError) as exc_info:
            svc.resolve_context("loc-berlin", "ten-invalid", "sz-medium")

        violations = exc_info.value.violations
        assert len(violations) == 1
        assert violations[0]["field"] == "tenant_id"

    def test_security_zone_not_found(self, svc, cmdb):
        cmdb.get_security_zone.return_value = None

        with pytest.raises(ContextService.ContextValidationError) as exc_info:
            svc.resolve_context("loc-berlin", "ten-corp", "sz-invalid")

        violations = exc_info.value.violations
        assert len(violations) == 1
        assert violations[0]["field"] == "security_zone_id"

    def test_zone_not_available_at_location(self, svc, cmdb):
        cmdb.get_networks_for_context.return_value = []

        with pytest.raises(ContextService.ContextValidationError) as exc_info:
            svc.resolve_context("loc-berlin", "ten-corp", "sz-medium")

        violations = exc_info.value.violations
        assert len(violations) == 1
        assert violations[0]["field"] == "security_zone_id"
        assert "not available" in violations[0]["message"].lower()

    def test_network_not_found(self, svc, cmdb):
        cmdb.get_network.return_value = None

        with pytest.raises(ContextService.ContextValidationError) as exc_info:
            svc.resolve_context("loc-berlin", "ten-corp", "sz-medium",
                                network_id="net-invalid")

        violations = exc_info.value.violations
        assert len(violations) == 1
        assert violations[0]["field"] == "network_id"
        assert "not found" in violations[0]["message"].lower()

    def test_network_not_at_location(self, svc, cmdb):
        cmdb.get_network.return_value = NETWORK_OTHER_LOC

        with pytest.raises(ContextService.ContextValidationError) as exc_info:
            svc.resolve_context("loc-berlin", "ten-corp", "sz-medium",
                                network_id="net-muc-dmz")

        violations = exc_info.value.violations
        assert len(violations) == 1
        assert violations[0]["field"] == "network_id"
        assert "location" in violations[0]["message"].lower()

    def test_network_not_in_zone(self, svc, cmdb):
        cmdb.get_network.return_value = NETWORK_OTHER_ZONE

        with pytest.raises(ContextService.ContextValidationError) as exc_info:
            svc.resolve_context("loc-berlin", "ten-corp", "sz-medium",
                                network_id="net-ber-intern")

        violations = exc_info.value.violations
        assert len(violations) == 1
        assert violations[0]["field"] == "network_id"
        assert "security zone" in violations[0]["message"].lower()


# ── resolve_context: tenant authorization ──────────────────────────

class TestResolveContextTenantAuth:
    def test_user_not_allowed_for_tenant(self, svc_with_tenant_repo, cmdb, tenant_repo):
        tenant_repo.get_allowed_tenant_ids.return_value = ["ten-dev"]

        with pytest.raises(ContextService.ContextValidationError) as exc_info:
            svc_with_tenant_repo.resolve_context(
                "loc-berlin", "ten-corp", "sz-medium", user_id="user-1")

        violations = exc_info.value.violations
        assert len(violations) == 1
        assert violations[0]["field"] == "tenant_id"
        assert "not allowed" in violations[0]["message"].lower()

    def test_user_allowed_for_tenant(self, svc_with_tenant_repo, cmdb, tenant_repo):
        tenant_repo.get_allowed_tenant_ids.return_value = ["ten-corp", "ten-dev"]

        result = svc_with_tenant_repo.resolve_context(
            "loc-berlin", "ten-corp", "sz-medium", user_id="user-1")

        assert result.tenant == TENANT

    def test_no_restrictions_means_all_allowed(self, svc_with_tenant_repo, cmdb, tenant_repo):
        tenant_repo.get_allowed_tenant_ids.return_value = None

        result = svc_with_tenant_repo.resolve_context(
            "loc-berlin", "ten-corp", "sz-medium", user_id="user-1")

        assert result.tenant == TENANT


# ── get_allowed_tenants ────────────────────────────────────────────

class TestGetAllowedTenants:
    def test_no_restrictions_returns_all(self, svc_with_tenant_repo, cmdb, tenant_repo):
        all_tenants = [TENANT, {"id": "ten-dev", "name": "Development", "code": "DEV"}]
        cmdb.get_tenants.return_value = all_tenants
        tenant_repo.get_allowed_tenant_ids.return_value = None

        result = svc_with_tenant_repo.get_allowed_tenants("user-1")

        assert result == all_tenants

    def test_with_restrictions_filters(self, svc_with_tenant_repo, cmdb, tenant_repo):
        all_tenants = [TENANT, {"id": "ten-dev", "name": "Development", "code": "DEV"}]
        cmdb.get_tenants.return_value = all_tenants
        tenant_repo.get_allowed_tenant_ids.return_value = ["ten-corp"]

        result = svc_with_tenant_repo.get_allowed_tenants("user-1")

        assert len(result) == 1
        assert result[0]["id"] == "ten-corp"

    def test_without_tenant_repo_returns_all(self, svc, cmdb):
        all_tenants = [TENANT]
        cmdb.get_tenants.return_value = all_tenants

        result = svc.get_allowed_tenants("user-1")

        assert result == all_tenants


# ── CMDB unavailable ──────────────────────────────────────────────

class TestCmdbUnavailable:
    def test_cmdb_error_raises_unavailable(self, svc, cmdb):
        cmdb.get_location.side_effect = ConnectionError("CMDB down")

        with pytest.raises(ContextService.CmdbUnavailableError):
            svc.resolve_context("loc-berlin", "ten-corp", "sz-medium")

    def test_cmdb_error_on_get_tenants(self, svc, cmdb):
        cmdb.get_tenants.side_effect = ConnectionError("CMDB down")

        with pytest.raises(ContextService.CmdbUnavailableError):
            svc.get_allowed_tenants("user-1")
