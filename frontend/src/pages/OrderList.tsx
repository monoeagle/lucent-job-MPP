import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useOrders } from '../hooks/useOrders'
import StatusBadge from '../components/StatusBadge'

const STATUS_FILTERS = [
  { value: '', label: 'Alle' },
  { value: 'draft', label: 'Entwurf' },
  { value: 'submitted', label: 'Eingereicht' },
  { value: 'pending_approval', label: 'Genehmigung' },
  { value: 'provisioning', label: 'Bereitstellung' },
  { value: 'done', label: 'Aktiv' },
  { value: 'cancelled', label: 'Storniert' },
  { value: 'failed', label: 'Fehlgeschlagen' },
]

export default function OrderList() {
  const [statusFilter, setStatusFilter] = useState('')
  const { data, isLoading, error } = useOrders(statusFilter ? { status: statusFilter } : undefined)

  if (isLoading) return <p className="text-gray-500">Lade Bestellungen...</p>
  if (error) return <p className="text-red-500">Fehler beim Laden der Bestellungen.</p>

  const orders = data?.items ?? []

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-1 flex-wrap">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                statusFilter === f.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <Link to="/shop"
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 shrink-0">
          Zum Shop
        </Link>
      </div>

      {orders.length === 0 ? (
        <p className="text-gray-400 text-sm py-8 text-center">Keine Bestellungen gefunden.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              <th className="py-2 font-medium">Nummer</th>
              <th className="py-2 font-medium">Titel</th>
              <th className="py-2 font-medium">Besteller</th>
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
                <td className="py-3 text-gray-500 text-xs">{(o as unknown as { requester_id?: string }).requester_id ?? '—'}</td>
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
