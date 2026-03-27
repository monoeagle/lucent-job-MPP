export interface Location {
  id: string
  name: string
  code: string
  region: string
}

export interface Tenant {
  id: string
  name: string
  code: string
}

export interface SecurityZone {
  id: string
  name: string
  level: number
  description: string
}

export interface Network {
  id: string
  name: string
  cidr: string
  type: string
  location_id: string
  security_zone_id: string
}

export interface OrderContext {
  location_id: string
  tenant_id: string
  security_zone_id: string
  network_id?: string
}

export interface ResolvedContext {
  location: Location
  tenant: Tenant
  security_zone: SecurityZone
  network: Network | null
  available_networks: Network[]
}
