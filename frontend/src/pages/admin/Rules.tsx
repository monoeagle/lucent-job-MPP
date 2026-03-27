import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../../store/authStore'
import { adminApi } from '../../api/admin'

type TabKey = 'approvals' | 'availability' | 'restrictions' | 'tenants'

const tabs: { key: TabKey; label: string }[] = [
  { key: 'approvals', label: 'Genehmigungsregeln' },
  { key: 'availability', label: 'Verfuegbarkeitsregeln' },
  { key: 'restrictions', label: 'Kontextbeschraenkungen' },
  { key: 'tenants', label: 'Mandantenzuweisungen' },
]

function ActiveBadge({ active }: { active: boolean }) {
  return (
    <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
      active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
    }`}>
      {active ? 'Aktiv' : 'Inaktiv'}
    </span>
  )
}

function EmptyState({ text }: { text: string }) {
  return <p className="text-sm text-gray-400 py-6 text-center">{text}</p>
}

export default function Rules() {
  const token = useAuthStore((s) => s.token)
  const [activeTab, setActiveTab] = useState<TabKey>('approvals')

  const { data: approvalRules, isLoading: loadingApprovals } = useQuery({
    queryKey: ['admin-approval-rules'],
    queryFn: () => adminApi.listApprovalRules(token!),
    enabled: !!token && activeTab === 'approvals',
  })

  const { data: availabilityRules, isLoading: loadingAvailability } = useQuery({
    queryKey: ['admin-availability-rules'],
    queryFn: () => adminApi.listAvailabilityRules(token!),
    enabled: !!token && activeTab === 'availability',
  })

  const { data: restrictions, isLoading: loadingRestrictions } = useQuery({
    queryKey: ['admin-context-restrictions'],
    queryFn: () => adminApi.listContextRestrictions(token!),
    enabled: !!token && activeTab === 'restrictions',
  })

  const { data: assignments, isLoading: loadingTenants } = useQuery({
    queryKey: ['admin-tenant-assignments'],
    queryFn: () => adminApi.listTenantAssignments(token!),
    enabled: !!token && activeTab === 'tenants',
  })

  const isLoading = loadingApprovals || loadingAvailability || loadingRestrictions || loadingTenants

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Regelverwaltung</h1>

      <div className="border-b border-gray-200 mb-6">
        <nav className="flex -mb-px space-x-6">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`py-2 px-1 border-b-2 text-sm font-medium ${
                activeTab === tab.key
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {isLoading && <p className="text-sm text-gray-500">Laden...</p>}

      {/* Genehmigungsregeln */}
      {activeTab === 'approvals' && approvalRules && (
        approvalRules.length === 0 ? <EmptyState text="Keine Genehmigungsregeln definiert." /> : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Typ</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Schwellwert</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Service</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {approvalRules.map((rule) => (
                <tr key={rule.id}>
                  <td className="px-4 py-3 text-sm font-medium">{rule.name}</td>
                  <td className="px-4 py-3 text-sm">{rule.rule_type}</td>
                  <td className="px-4 py-3 text-sm">{rule.threshold_eur !== null ? `${rule.threshold_eur} EUR` : '—'}</td>
                  <td className="px-4 py-3 text-sm">{rule.service_type_slug ?? 'Alle'}</td>
                  <td className="px-4 py-3"><ActiveBadge active={rule.is_active} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}

      {/* Verfuegbarkeitsregeln */}
      {activeTab === 'availability' && availabilityRules && (
        availabilityRules.length === 0 ? <EmptyState text="Keine Verfuegbarkeitsregeln definiert." /> : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Template</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Typ</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Prioritaet</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {availabilityRules.map((rule) => (
                <tr key={rule.id}>
                  <td className="px-4 py-3 text-sm font-medium">{rule.name}</td>
                  <td className="px-4 py-3 text-sm">{rule.template_slug}</td>
                  <td className="px-4 py-3 text-sm">{rule.rule_type}</td>
                  <td className="px-4 py-3 text-sm">{rule.priority}</td>
                  <td className="px-4 py-3"><ActiveBadge active={rule.is_active} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}

      {/* Kontextbeschraenkungen */}
      {activeTab === 'restrictions' && restrictions && (
        restrictions.length === 0 ? <EmptyState text="Keine Kontextbeschraenkungen definiert." /> : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Parameter</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Typ</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Template</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {restrictions.map((r) => (
                <tr key={r.id}>
                  <td className="px-4 py-3 text-sm font-medium">{r.name}</td>
                  <td className="px-4 py-3 text-sm font-mono text-xs">{r.parameter_key}</td>
                  <td className="px-4 py-3 text-sm">{r.restriction_type}</td>
                  <td className="px-4 py-3 text-sm">{r.template_slug ?? 'Alle'}</td>
                  <td className="px-4 py-3"><ActiveBadge active={r.is_active} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}

      {/* Mandantenzuweisungen */}
      {activeTab === 'tenants' && assignments && (
        assignments.length === 0 ? <EmptyState text="Keine Mandantenzuweisungen definiert." /> : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Benutzer</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Mandant</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Erstellt</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {assignments.map((a) => (
                <tr key={a.id}>
                  <td className="px-4 py-3 text-sm font-medium">{a.user_id}</td>
                  <td className="px-4 py-3 text-sm">{a.tenant_id}</td>
                  <td className="px-4 py-3 text-sm text-gray-400">{new Date(a.created_at).toLocaleDateString('de-DE')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}
    </div>
  )
}
