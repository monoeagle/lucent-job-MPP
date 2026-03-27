import { apiClient } from './client'
import type { Location, Tenant, SecurityZone, Network, ResolvedContext, OrderContext } from '../types/context'

export const contextApi = {
  async getLocations(token: string): Promise<Location[]> {
    return (await apiClient.get('/api/v1/context/locations', token)) as Location[]
  },

  async getTenants(token: string): Promise<Tenant[]> {
    return (await apiClient.get('/api/v1/context/tenants', token)) as Tenant[]
  },

  async getSecurityZones(token: string): Promise<SecurityZone[]> {
    return (await apiClient.get('/api/v1/context/security-zones', token)) as SecurityZone[]
  },

  async getNetworks(token: string, locationId: string, securityZoneId: string): Promise<Network[]> {
    const params = new URLSearchParams({ location_id: locationId, security_zone_id: securityZoneId })
    return (await apiClient.get(`/api/v1/context/networks?${params}`, token)) as Network[]
  },

  async resolveContext(token: string, context: OrderContext): Promise<ResolvedContext> {
    return (await apiClient.post('/api/v1/context/resolve', context, token)) as ResolvedContext
  },
}
