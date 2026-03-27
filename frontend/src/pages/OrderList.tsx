import { Link } from 'react-router-dom'
import { useOrders } from '../hooks/useOrders'
import StatusBadge from '../components/StatusBadge'

export default function OrderList() {
  const { data, isLoading, error } = useOrders()

  if (isLoading) return <p className="text-gray-500">Lade Bestellungen...</p>
  if (error) return <p className="text-red-500">Fehler beim Laden der Bestellungen.</p>

  const orders = data?.items ?? []

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Bestellungen</h1>
        <Link to="/orders/new"
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700">
          Neue Bestellung
        </Link>
      </div>

      {orders.length === 0 ? (
        <p className="text-gray-500">Keine Bestellungen vorhanden.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              <th className="py-2 font-medium">Nummer</th>
              <th className="py-2 font-medium">Titel</th>
              <th className="py-2 font-medium">Status</th>
              <th className="py-2 font-medium">Positionen</th>
              <th className="py-2 font-medium">Erstellt</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-3">
                  <Link to={`/orders/${o.id}`} className="text-blue-600 hover:underline">
                    {o.order_number}
                  </Link>
                </td>
                <td className="py-3">{o.title}</td>
                <td className="py-3"><StatusBadge status={o.status} /></td>
                <td className="py-3">{o.item_count}</td>
                <td className="py-3 text-gray-400">{new Date(o.created_at).toLocaleDateString('de-DE')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
