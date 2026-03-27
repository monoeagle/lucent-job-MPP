import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useOrders } from '../hooks/useOrders'
import { approvalsApi } from '../api/approvals'
import { useAuthStore } from '../store/authStore'
import StatusBadge from '../components/StatusBadge'

type Tab = 'orders' | 'approvals'

function OrdersTab() {
  const { data, isLoading, error } = useOrders()

  if (isLoading) return <p className="text-gray-500">Lade Bestellungen...</p>
  if (error) return <p className="text-red-500">Fehler beim Laden der Bestellungen.</p>

  const orders = data?.items ?? []

  if (orders.length === 0) {
    return <p className="text-gray-500">Keine Bestellungen vorhanden.</p>
  }

  return (
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
            <td className="py-3">
              <StatusBadge status={o.status} />
            </td>
            <td className="py-3">{o.item_count}</td>
            <td className="py-3 text-gray-400">
              {new Date(o.created_at).toLocaleDateString('de-DE')}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function ApprovalsTab() {
  const token = useAuthStore((s) => s.token)
  const user = useAuthStore((s) => s.user)

  const { data, isLoading, error } = useQuery({
    queryKey: ['my-approvals'],
    queryFn: () => approvalsApi.listAllApprovals(token!),
    enabled: !!token,
  })

  if (isLoading) return <p className="text-gray-500">Lade Genehmigungen...</p>
  if (error) return <p className="text-red-500">Fehler beim Laden der Genehmigungen.</p>

  const items = (data?.items ?? []).filter(
    (a) => a.decided_by === user?.username && (a.status === 'approved' || a.status === 'rejected'),
  )

  if (items.length === 0) {
    return <p className="text-gray-500">Keine Genehmigungsentscheidungen vorhanden.</p>
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-gray-200 text-left text-gray-500">
          <th className="py-2 font-medium">Bestellung</th>
          <th className="py-2 font-medium">Status</th>
          <th className="py-2 font-medium">Entschieden am</th>
          <th className="py-2 font-medium">Begründung</th>
        </tr>
      </thead>
      <tbody>
        {items.map((a) => (
          <tr key={a.id} className="border-b border-gray-100 hover:bg-gray-50">
            <td className="py-3">{a.order_id}</td>
            <td className="py-3">
              <StatusBadge status={a.status} />
            </td>
            <td className="py-3 text-gray-400">
              {a.decided_at ? new Date(a.decided_at).toLocaleDateString('de-DE') : '—'}
            </td>
            <td className="py-3 text-gray-600">{a.decision_reason ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default function MyRequests() {
  const [activeTab, setActiveTab] = useState<Tab>('orders')

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Meine Anfragen</h1>

      <div className="flex gap-2 mb-6 border-b border-gray-200">
        <button
          onClick={() => setActiveTab('orders')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            activeTab === 'orders'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Meine Bestellungen
        </button>
        <button
          onClick={() => setActiveTab('approvals')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            activeTab === 'approvals'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Meine Genehmigungen
        </button>
      </div>

      {activeTab === 'orders' ? <OrdersTab /> : <ApprovalsTab />}
    </div>
  )
}
