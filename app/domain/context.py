from dataclasses import dataclass, field


@dataclass
class OrderContext:
    location_id: str
    tenant_id: str
    security_zone_id: str
    network_id: str | None = None


@dataclass
class ResolvedContext:
    location: dict
    tenant: dict
    security_zone: dict
    network: dict | None
    available_networks: list[dict] = field(default_factory=list)
