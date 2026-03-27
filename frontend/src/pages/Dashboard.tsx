import { Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { useStats } from '../hooks/useDashboard'
import { useUnreadCount } from '../hooks/useNotifications'
import StatCard from '../components/dashboard/StatCard'
import RecentOrders from '../components/dashboard/RecentOrders'
import OrderStatusChart from '../components/dashboard/OrderStatusChart'
import OrderTimelineChart from '../components/dashboard/OrderTimelineChart'
import PopularServices from '../components/dashboard/PopularServices'

export default function Dashboard() {
  const user = useAuthStore((s) => s.user)
  const { data: stats, isLoading } = useStats()
  const { data: unreadData } = useUnreadCount()

  const isApprover = user?.roles.includes('approver') || user?.roles.includes('admin')
  const openOrders = (stats?.orders_by_status?.draft ?? 0) + (stats?.orders_by_status?.submitted ?? 0)
  const unreadCount = unreadData?.count ?? 0

  return (
    <div>
      {isLoading ? (
        <p className="text-gray-500">Lade Dashboard...</p>
      ) : stats ? (
        <div className="space-y-6">
          {/* Stat Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard label="Offene Orders" value={openOrders} />
            <StatCard label="Ausstehende Genehmigungen" value={stats.pending_approvals} color="text-yellow-600" />
            <StatCard label="Aktive Services" value={stats.active_resources} color="text-green-600" />
            <StatCard label="Templates" value={stats.total_templates} color="text-gray-600" />
          </div>

          {/* Quick-Access Kacheln: Notifications + Review Requests */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Link to="/notifications"
              className="block bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md hover:border-blue-300 transition-all">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">Benachrichtigungen</h3>
                  <p className="text-sm text-gray-500 mt-1">Neue Nachrichten und Updates</p>
                </div>
                {unreadCount > 0 ? (
                  <span className="bg-red-500 text-white text-lg font-bold rounded-full w-10 h-10 flex items-center justify-center">
                    {unreadCount > 99 ? '99+' : unreadCount}
                  </span>
                ) : (
                  <span className="text-3xl text-gray-300">🔔</span>
                )}
              </div>
            </Link>

            {isApprover && (
              <Link to="/reviews"
                className="block bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md hover:border-yellow-300 transition-all">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900">Review Requests</h3>
                    <p className="text-sm text-gray-500 mt-1">Ausstehende Genehmigungen bearbeiten</p>
                  </div>
                  {stats.pending_approvals > 0 ? (
                    <span className="bg-yellow-500 text-white text-lg font-bold rounded-full w-10 h-10 flex items-center justify-center">
                      {stats.pending_approvals}
                    </span>
                  ) : (
                    <span className="text-3xl text-gray-300">✅</span>
                  )}
                </div>
              </Link>
            )}
          </div>

          {/* Charts + Lists */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <RecentOrders />
            <OrderStatusChart data={stats.orders_by_status} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <PopularServices templates={stats.popular_templates} />
            <OrderTimelineChart data={stats.orders_by_month} />
          </div>
        </div>
      ) : null}
    </div>
  )
}
