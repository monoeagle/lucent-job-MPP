import { useAuthStore } from '../store/authStore'
import { useStats } from '../hooks/useDashboard'
import StatCard from '../components/dashboard/StatCard'
import RecentOrders from '../components/dashboard/RecentOrders'
import OrderStatusChart from '../components/dashboard/OrderStatusChart'
import OrderTimelineChart from '../components/dashboard/OrderTimelineChart'
import PopularServices from '../components/dashboard/PopularServices'
import PendingApprovals from '../components/dashboard/PendingApprovals'

export default function Dashboard() {
  const user = useAuthStore((s) => s.user)
  const { data: stats, isLoading } = useStats()

  const isApprover = user?.roles.includes('approver') || user?.roles.includes('admin')
  const openOrders = (stats?.orders_by_status?.draft ?? 0) + (stats?.orders_by_status?.submitted ?? 0)

  return (
    <div>
      {isLoading ? (
        <p className="text-gray-500">Lade Dashboard...</p>
      ) : stats ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard label="Offene Orders" value={openOrders} />
            <StatCard label="Ausstehende Genehmigungen" value={stats.pending_approvals} color="text-yellow-600" />
            <StatCard label="Aktive Services" value={stats.active_resources} color="text-green-600" />
            <StatCard label="Templates" value={stats.total_templates} color="text-gray-600" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <RecentOrders />
            <OrderStatusChart data={stats.orders_by_status} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <PopularServices templates={stats.popular_templates} />
            <OrderTimelineChart data={stats.orders_by_month} />
          </div>

          {isApprover && <PendingApprovals />}
        </div>
      ) : null}
    </div>
  )
}
