// frontend/src/pages/Subscriptions.tsx
import { useState } from 'react'
import { useSubscriptions, useSubscriptionGroups } from '../hooks/useSubscriptions'
import SubscriptionCard from '../components/subscriptions/SubscriptionCard'
import SubscriptionGroupSection from '../components/subscriptions/SubscriptionGroupSection'

export default function Subscriptions() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const { data, isLoading } = useSubscriptions({ status: statusFilter })
  const { data: groups } = useSubscriptionGroups()

  const subscriptions = data?.items ?? []
  const groupList = groups ?? []
  const groupedIds = new Set(groupList.flatMap((g) => g.subscriptions.map((s) => s.id)))
  const ungrouped = subscriptions.filter((s) => !groupedIds.has(s.id))

  const statuses = ['active', 'ordered', 'pending_approval', 'change_pending', 'cancel_pending', 'cancelled']

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Subscriptions</h1>

      <div className="flex gap-2 mb-4 flex-wrap">
        <button onClick={() => setStatusFilter(undefined)}
          className={`px-3 py-1 rounded-full text-sm ${!statusFilter ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
          Alle
        </button>
        {statuses.map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded-full text-sm ${statusFilter === s ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
            {s}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-gray-500">Lade Subscriptions...</p>
      ) : (
        <div className="space-y-4">
          {groupList.length > 0 && (
            <div className="space-y-3">
              {groupList.map((group) => (
                <SubscriptionGroupSection key={group.id} group={group} />
              ))}
            </div>
          )}

          {ungrouped.length > 0 && (
            <div className="space-y-2">
              {groupList.length > 0 && <h3 className="text-sm font-medium text-gray-500">Einzeln</h3>}
              {ungrouped.map((sub) => (
                <SubscriptionCard key={sub.id} subscription={sub} />
              ))}
            </div>
          )}

          {subscriptions.length === 0 && groupList.length === 0 && (
            <p className="text-gray-400">Keine Subscriptions vorhanden.</p>
          )}
        </div>
      )}
    </div>
  )
}
