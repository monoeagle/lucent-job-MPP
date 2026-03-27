import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useSubscription, useRequestCancel } from '../hooks/useSubscriptions'
import StatusBadge from '../components/StatusBadge'

export default function SubscriptionDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: sub, isLoading } = useSubscription(id ?? null)
  const requestCancel = useRequestCancel(id ?? '')

  const [cancelDialogOpen, setCancelDialogOpen] = useState(false)
  const [cancelReason, setCancelReason] = useState('')

  const handleCancel = () => {
    if (!cancelReason.trim()) return
    requestCancel.mutate(cancelReason, {
      onSuccess: () => { setCancelDialogOpen(false); setCancelReason('') },
    })
  }

  if (isLoading) return <p className="text-gray-500">Lade Subscription...</p>
  if (!sub) return <p className="text-red-500">Subscription nicht gefunden.</p>

  const isActive = sub.status === 'active'

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold">{sub.display_name}</h1>
          <p className="text-sm text-gray-400">{sub.template_slug} v{sub.template_version}</p>
        </div>
        <StatusBadge status={sub.status} />
      </div>

      {sub.monthly_cost_eur && (
        <p className="text-sm text-gray-600 mb-4">{sub.monthly_cost_eur} EUR/Monat</p>
      )}

      <div className="bg-gray-50 rounded-lg p-4 mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Konfiguration</h3>
        <div className="space-y-2">
          {Object.entries(sub.parameters).map(([key, val]) => (
            <div key={key} className="flex justify-between text-sm">
              <span className="text-gray-600">{key}</span>
              <span className="font-medium">{String(val)}</span>
            </div>
          ))}
        </div>
      </div>

      {sub.pending_changes && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-semibold text-yellow-700 mb-2">Ausstehende Aenderung</h3>
          <p className="text-sm text-yellow-600">Typ: {sub.pending_changes.type}</p>
          {sub.pending_changes.reason && (
            <p className="text-sm text-yellow-600">Grund: {sub.pending_changes.reason}</p>
          )}
        </div>
      )}

      <div className="mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Timeline</h3>
        <div className="text-sm space-y-1 text-gray-600">
          <p>Erstellt: {new Date(sub.created_at).toLocaleString('de-DE')}</p>
          {sub.activated_at && <p>Aktiviert: {new Date(sub.activated_at).toLocaleString('de-DE')}</p>}
          {sub.cancelled_at && <p>Gekuendigt: {new Date(sub.cancelled_at).toLocaleString('de-DE')}</p>}
        </div>
      </div>

      {isActive && (
        <div className="flex gap-3">
          <button className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700">
            Aendern
          </button>
          <button onClick={() => setCancelDialogOpen(true)}
            className="px-4 py-2 bg-red-600 text-white rounded-md text-sm hover:bg-red-700">
            Kuendigen
          </button>
        </div>
      )}

      {cancelDialogOpen && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96 shadow-xl">
            <h3 className="text-lg font-semibold mb-4">Subscription kuendigen</h3>
            <textarea value={cancelReason} onChange={(e) => setCancelReason(e.target.value)}
              placeholder="Grund fuer die Kuendigung"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm mb-4" rows={3} />
            <div className="flex gap-2 justify-end">
              <button onClick={() => { setCancelDialogOpen(false); setCancelReason('') }}
                className="px-4 py-2 text-sm text-gray-600">Abbrechen</button>
              <button onClick={handleCancel} disabled={!cancelReason.trim() || requestCancel.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded-md text-sm disabled:opacity-50">Kuendigen</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
