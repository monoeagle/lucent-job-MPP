import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../../store/authStore'
import { contextApi } from '../../api/context'
import type { OrderContext, Network } from '../../types/context'

interface Props {
  value: OrderContext | null
  onChange: (context: OrderContext) => void
}

export default function ContextSelector({ value, onChange }: Props) {
  const token = useAuthStore((s) => s.token)

  const [locationId, setLocationId] = useState(value?.location_id ?? '')
  const [tenantId, setTenantId] = useState(value?.tenant_id ?? '')
  const [securityZoneId, setSecurityZoneId] = useState(value?.security_zone_id ?? '')
  const [networkId, setNetworkId] = useState(value?.network_id ?? '')

  const { data: locations } = useQuery({
    queryKey: ['context-locations'],
    queryFn: () => contextApi.getLocations(token!),
    enabled: !!token,
  })

  const { data: tenants } = useQuery({
    queryKey: ['context-tenants'],
    queryFn: () => contextApi.getTenants(token!),
    enabled: !!token,
  })

  const { data: securityZones } = useQuery({
    queryKey: ['context-security-zones'],
    queryFn: () => contextApi.getSecurityZones(token!),
    enabled: !!token,
  })

  const { data: networks } = useQuery({
    queryKey: ['context-networks', locationId, securityZoneId],
    queryFn: () => contextApi.getNetworks(token!, locationId, securityZoneId),
    enabled: !!token && !!locationId && !!securityZoneId,
  })

  useEffect(() => {
    if (locationId && tenantId && securityZoneId) {
      onChange({
        location_id: locationId,
        tenant_id: tenantId,
        security_zone_id: securityZoneId,
        network_id: networkId || undefined,
      })
    }
  }, [locationId, tenantId, securityZoneId, networkId, onChange])

  const handleLocationChange = (id: string) => {
    setLocationId(id)
    setNetworkId('')
  }

  const handleSecurityZoneChange = (id: string) => {
    setSecurityZoneId(id)
    setNetworkId('')
  }

  return (
    <div className="space-y-3" data-testid="context-selector">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Standort *</label>
        <select
          value={locationId}
          onChange={(e) => handleLocationChange(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
          data-testid="location-select"
        >
          <option value="">Standort wählen...</option>
          {locations?.map((loc) => (
            <option key={loc.id} value={loc.id}>{loc.name} ({loc.code})</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Mandant *</label>
        <select
          value={tenantId}
          onChange={(e) => setTenantId(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
          data-testid="tenant-select"
        >
          <option value="">Mandant wählen...</option>
          {tenants?.map((t) => (
            <option key={t.id} value={t.id}>{t.name} ({t.code})</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Sicherheitszone *</label>
        <select
          value={securityZoneId}
          onChange={(e) => handleSecurityZoneChange(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
          data-testid="security-zone-select"
        >
          <option value="">Sicherheitszone wählen...</option>
          {securityZones?.map((sz) => (
            <option key={sz.id} value={sz.id}>{sz.name} (Level {sz.level})</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Netzwerk</label>
        <select
          value={networkId}
          onChange={(e) => setNetworkId(e.target.value)}
          disabled={!networks?.length}
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm disabled:bg-gray-100"
          data-testid="network-select"
        >
          <option value="">Kein Netzwerk</option>
          {networks?.map((n: Network) => (
            <option key={n.id} value={n.id}>{n.name} ({n.cidr})</option>
          ))}
        </select>
      </div>
    </div>
  )
}
