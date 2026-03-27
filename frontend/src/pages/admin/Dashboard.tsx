import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../../store/authStore'
import { adminApi } from '../../api/admin'
import { useStats } from '../../hooks/useDashboard'
import StatusBadge from '../../components/StatusBadge'
import OrderStatusChart from '../../components/dashboard/OrderStatusChart'
import OrderTimelineChart from '../../components/dashboard/OrderTimelineChart'
import StatCard from '../../components/dashboard/StatCard'

export default function AdminDashboard() {
  const token = useAuthStore((s) => s.token)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: () => adminApi.getDashboard(token!),
    enabled: !!token,
  })

  const { data: stats } = useStats()

  if (isLoading) return <p className="text-sm text-gray-500">Laden...</p>
  if (!data) return <p className="text-sm text-gray-500">Keine Daten verfuegbar.</p>

  return (
    <div>
      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {Object.entries(data.order_counts).map(([status, count]) => (
          <StatCard key={status} label={status} value={count as number} />
        ))}
        <StatCard label="Ausstehende Genehmigungen" value={data.pending_approvals} color="text-yellow-600" />
        <StatCard label="Aktive Ressourcen" value={data.active_resources} color="text-green-600" />
      </div>

      {/* Charts */}
      {stats && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          <OrderStatusChart data={stats.orders_by_status} />
          <OrderTimelineChart data={stats.orders_by_month} />
        </div>
      )}

      {/* System Health */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-3">Systemstatus</h2>
        <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-2">
          <p className="text-sm">
            Status: <StatusBadge status={data.system_health.status} />
          </p>
          <p className="text-sm text-gray-600">Uptime: {data.system_health.uptime}</p>
          <p className="text-sm text-gray-600">Version: {data.system_health.version}</p>
        </div>
      </div>

      {/* Recent Orders */}
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
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Besteller</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Erstellt</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.recent_orders.map((order: { id: string; order_number: string; title: string; status: string; created_at: string; requester_id?: string }) => (
                <tr key={order.id}>
                  <td className="px-4 py-3 text-sm">{order.order_number}</td>
                  <td className="px-4 py-3 text-sm">{order.title}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{order.requester_id ?? '—'}</td>
                  <td className="px-4 py-3"><StatusBadge status={order.status} /></td>
                  <td className="px-4 py-3 text-sm text-gray-400">{new Date(order.created_at).toLocaleDateString('de-DE')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
