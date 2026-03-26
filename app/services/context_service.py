# app/services/context_service.py
from app.domain.context import ResolvedContext


class ContextService:

    class CmdbUnavailableError(Exception):
        pass

    class ContextValidationError(Exception):
        def __init__(self, violations: list[dict]):
            self.violations = violations
            super().__init__(f"Context validation failed: {violations}")

    def __init__(self, cmdb_client, tenant_repo=None):
        self.cmdb = cmdb_client
        self.tenant_repo = tenant_repo

    def resolve_context(self, location_id: str, tenant_id: str,
                        security_zone_id: str, network_id: str | None = None,
                        user_id: str | None = None) -> ResolvedContext:
        try:
            return self._do_resolve(location_id, tenant_id, security_zone_id,
                                    network_id, user_id)
        except (self.ContextValidationError, self.CmdbUnavailableError):
            raise
        except Exception as e:
            raise self.CmdbUnavailableError(str(e)) from e

    def _do_resolve(self, location_id, tenant_id, security_zone_id,
                    network_id, user_id):
        # 1. Validate location
        location = self.cmdb.get_location(location_id)
        if location is None:
            raise self.ContextValidationError([{
                "field": "location_id",
                "message": f"Location '{location_id}' not found.",
            }])

        # 2. Validate tenant
        tenant = self.cmdb.get_tenant(tenant_id)
        if tenant is None:
            raise self.ContextValidationError([{
                "field": "tenant_id",
                "message": f"Tenant '{tenant_id}' not found.",
            }])

        # 3. Check user allowed for tenant
        if user_id and self.tenant_repo:
            allowed_ids = self.tenant_repo.get_allowed_tenant_ids(user_id)
            if allowed_ids is not None and tenant_id not in allowed_ids:
                raise self.ContextValidationError([{
                    "field": "tenant_id",
                    "message": f"User is not allowed to order for tenant '{tenant_id}'.",
                }])

        # 4. Validate security zone
        security_zone = self.cmdb.get_security_zone(security_zone_id)
        if security_zone is None:
            raise self.ContextValidationError([{
                "field": "security_zone_id",
                "message": f"Security zone '{security_zone_id}' not found.",
            }])

        # 5. Check zone available at location
        available_networks = self.cmdb.get_networks_for_context(
            location_id, security_zone_id)
        if not available_networks:
            raise self.ContextValidationError([{
                "field": "security_zone_id",
                "message": f"Security zone '{security_zone_id}' is not available at location '{location_id}'.",
            }])

        # 6. Validate network if provided
        network = None
        if network_id:
            network = self.cmdb.get_network(network_id)
            if network is None:
                raise self.ContextValidationError([{
                    "field": "network_id",
                    "message": f"Network '{network_id}' not found.",
                }])
            if network["location_id"] != location_id:
                raise self.ContextValidationError([{
                    "field": "network_id",
                    "message": f"Network '{network_id}' does not belong to the selected location.",
                }])
            if network["security_zone_id"] != security_zone_id:
                raise self.ContextValidationError([{
                    "field": "network_id",
                    "message": f"Network '{network_id}' does not belong to the selected security zone.",
                }])

        return ResolvedContext(
            location=location,
            tenant=tenant,
            security_zone=security_zone,
            network=network,
            available_networks=available_networks,
        )

    def get_allowed_tenants(self, user_id: str) -> list[dict]:
        try:
            all_tenants = self.cmdb.get_tenants()
        except Exception as e:
            raise self.CmdbUnavailableError(str(e)) from e

        if self.tenant_repo is None:
            return all_tenants

        allowed_ids = self.tenant_repo.get_allowed_tenant_ids(user_id)
        if allowed_ids is None:
            return all_tenants

        return [t for t in all_tenants if t["id"] in allowed_ids]
