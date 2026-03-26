# tests/unit/test_context_domain.py
import pytest
from app.domain.context import OrderContext, ResolvedContext


class TestOrderContext:
    def test_create_with_required_fields(self):
        ctx = OrderContext(
            location_id="loc-berlin",
            tenant_id="ten-corp",
            security_zone_id="sz-medium",
        )
        assert ctx.location_id == "loc-berlin"
        assert ctx.tenant_id == "ten-corp"
        assert ctx.security_zone_id == "sz-medium"
        assert ctx.network_id is None

    def test_create_with_network(self):
        ctx = OrderContext(
            location_id="loc-berlin",
            tenant_id="ten-corp",
            security_zone_id="sz-medium",
            network_id="net-ber-dmz",
        )
        assert ctx.network_id == "net-ber-dmz"

    def test_missing_required_field_raises(self):
        with pytest.raises(TypeError):
            OrderContext(location_id="loc-berlin", tenant_id="ten-corp")

        with pytest.raises(TypeError):
            OrderContext(location_id="loc-berlin", security_zone_id="sz-medium")

        with pytest.raises(TypeError):
            OrderContext(tenant_id="ten-corp", security_zone_id="sz-medium")


class TestResolvedContext:
    def test_create_resolved_context(self):
        rc = ResolvedContext(
            location={"id": "loc-berlin", "name": "Berlin HQ"},
            tenant={"id": "ten-corp", "name": "Corporate IT"},
            security_zone={"id": "sz-medium", "name": "MEDIUM"},
            network={"id": "net-ber-dmz", "name": "Berlin DMZ"},
            available_networks=[{"id": "net-ber-dmz", "name": "Berlin DMZ"}],
        )
        assert rc.location["id"] == "loc-berlin"
        assert rc.tenant["id"] == "ten-corp"
        assert rc.security_zone["id"] == "sz-medium"
        assert rc.network["id"] == "net-ber-dmz"
        assert len(rc.available_networks) == 1

    def test_create_without_network(self):
        rc = ResolvedContext(
            location={"id": "loc-berlin"},
            tenant={"id": "ten-corp"},
            security_zone={"id": "sz-medium"},
            network=None,
            available_networks=[],
        )
        assert rc.network is None
        assert rc.available_networks == []

    def test_available_networks_defaults_to_empty(self):
        rc = ResolvedContext(
            location={"id": "loc-berlin"},
            tenant={"id": "ten-corp"},
            security_zone={"id": "sz-medium"},
            network=None,
        )
        assert rc.available_networks == []
