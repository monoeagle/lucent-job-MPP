import { Link } from 'react-router-dom'
import { useOrders } from '../../hooks/useOrders'
import StatusBadge from '../StatusBadge'

export default function RecentOrders() {
  const { data } = useOrders({ limit: 5 })
  const orders = data?.items ?? []

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Letzte Bestellungen</h3>
      {orders.length === 0 ? (
        <p className="text-sm text-gray-400">Keine Bestellungen</p>
      ) : (
        <div className="space-y-2">
          {orders.map((o) => (
            <Link
              key={o.id}
              to={`/orders/${o.id}`}
              className="flex items-center justify-between text-sm hover:bg-gray-50 rounded px-2 py-1 -mx-2"
            >
              <div>
                <span className="font-medium">{o.order_number}</span>
                <span className="text-gray-400 ml-2">{o.title}</span>
              </div>
              <StatusBadge status={o.status} />
            </Link>
          ))}
          <Link to="/orders" className="text-xs text-blue-600 hover:text-blue-800">
            Alle anzeigen →
          </Link>
        </div>
      )}
    </div>
  )
}
