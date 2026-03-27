// frontend/src/components/subscriptions/SubscriptionCard.tsx
import { Link } from 'react-router-dom'
import type { Subscription } from '../../types/subscription'
import StatusBadge from '../StatusBadge'

interface Props {
  subscription: Subscription
}

export default function SubscriptionCard({ subscription: sub }: Props) {
  const paramSummary = Object.entries(sub.parameters)
    .slice(0, 4)
    .map(([k, v]) => `${k}: ${String(v)}`)
    .join(', ')

  return (
    <Link to={`/subscriptions/${sub.id}`}
      className="block border border-gray-200 rounded-lg p-4 bg-white hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{sub.display_name}</span>
          <span className="text-xs text-gray-400">v{sub.template_version}</span>
          <StatusBadge status={sub.status} />
        </div>
        {sub.monthly_cost_eur && (
          <span className="text-xs text-gray-400">{sub.monthly_cost_eur} EUR/Monat</span>
        )}
      </div>
      {paramSummary && <p className="text-xs text-gray-500 truncate">{paramSummary}</p>}
      {sub.pending_changes && (
        <p className="text-xs text-yellow-600 mt-1">Aenderung ausstehend: {sub.pending_changes.type}</p>
      )}
    </Link>
  )
}
