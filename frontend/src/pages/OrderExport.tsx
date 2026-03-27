import { useParams, Link } from 'react-router-dom'
import { useOrderExport } from '../hooks/useOrders'

export default function OrderExport() {
  const { orderId } = useParams<{ orderId: string }>()
  const { data: exportData, isLoading, error } = useOrderExport(orderId ?? null)

  if (isLoading) return <p className="text-gray-500">Lade Export...</p>
  if (error || !exportData) return <p className="text-red-500">Fehler beim Laden des Exports.</p>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="text-sm text-gray-400">{exportData.order_number}</p>
          <h1 className="text-2xl font-bold">Tofu Export</h1>
        </div>
        <Link to={`/orders/${orderId}`}
          className="text-sm text-blue-600 hover:underline">
          Zurück zur Bestellung
        </Link>
      </div>

      {exportData.readonly_notice && (
        <p className="text-sm text-yellow-600 bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4">
          {exportData.readonly_notice}
        </p>
      )}

      <pre className="bg-gray-900 text-green-400 rounded-lg p-6 overflow-x-auto text-sm leading-relaxed">
        {JSON.stringify(exportData, null, 2)}
      </pre>
    </div>
  )
}
