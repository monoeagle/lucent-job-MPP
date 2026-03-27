import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../../store/authStore'
import { adminApi } from '../../api/admin'
import StatusBadge from '../../components/StatusBadge'

export default function AdminDashboard() {
  const token = useAuthStore((s) => s.token)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: () => adminApi.getDashboard(token!),
    enabled: !!token,
  })

  if (isLoading) return <p className="text-sm text-gray-500">Laden...</p>
  if (!data) return <p className="text-sm text-gray-500">Keine Daten verfügbar.</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Admin Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {Object.entries(data.order_counts).map(([status, count]) => (
          <div key={status} className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="text-sm text-gray-500 capitalize">{status}</p>
            <p className="text-2xl font-bold" data-testid={`count-${status}`}>{count}</p>
          </div>
        ))}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-sm text-gray-500">Ausstehende Genehmigungen</p>
          <p className="text-2xl font-bold" data-testid="pending-approvals">{data.pending_approvals}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-sm text-gray-500">Aktive Ressourcen</p>
          <p className="text-2xl font-bold" data-testid="active-resources">{data.active_resources}</p>
        </div>
      </div>

      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-3">Systemstatus</h2>
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
          <p className="text-sm">
            Status: <StatusBadge status={data.system_health.status} />
          </p>
          <p className="text-sm text-gray-600">Uptime: {data.system_health.uptime}</p>
          <p className="text-sm text-gray-600">Version: {data.system_health.version}</p>
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-3">Letzte Bestellungen</h2>
        {data.recent_orders.length === 0 ? (
          <p className="text-sm text-gray-500">Keine Bestellungen.</p>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nr.</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Titel</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Erstellt</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.recent_orders.map((order) => (
                <tr key={order.id}>
                  <td className="px-4 py-3 text-sm">{order.order_number}</td>
                  <td className="px-4 py-3 text-sm">{order.title}</td>
                  <td className="px-4 py-3"><StatusBadge status={order.status} /></td>
                  <td className="px-4 py-3 text-sm">{new Date(order.created_at).toLocaleDateString('de-DE')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
