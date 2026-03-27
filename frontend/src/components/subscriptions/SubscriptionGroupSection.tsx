// frontend/src/components/subscriptions/SubscriptionGroupSection.tsx
import { useState } from 'react'
import type { SubscriptionGroup } from '../../types/subscription'
import SubscriptionCard from './SubscriptionCard'

interface Props {
  group: SubscriptionGroup
}

export default function SubscriptionGroupSection({ group }: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const activeCount = group.subscriptions.filter((s) => s.status === 'active').length

  return (
    <div className="border border-gray-300 rounded-lg bg-gray-50">
      <div className="flex items-center justify-between p-3 cursor-pointer"
           onClick={() => setCollapsed(!collapsed)}>
        <div className="flex items-center gap-2">
          <span className="text-sm">{collapsed ? '▶' : '▼'}</span>
          <span className="font-medium">{group.name}</span>
          <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">
            {activeCount}/{group.subscriptions.length} aktiv
          </span>
        </div>
      </div>
      {!collapsed && (
        <div className="px-3 pb-3 space-y-2">
          {group.subscriptions.map((sub) => (
            <SubscriptionCard key={sub.id} subscription={sub} />
          ))}
        </div>
      )}
    </div>
  )
}
