import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../store/authStore'
import { resourcesApi } from '../api/resources'
import { useSubscriptions } from '../hooks/useSubscriptions'
import StatusBadge from '../components/StatusBadge'

type Tab = 'active' | 'subscriptions' | 'all'

export default function MyServices() {
  const token = useAuthStore((s) => s.token)
  const [activeTab, setActiveTab] = useState<Tab>('active')
  const [search, setSearch] = useState('')

  const { data: resourcesData, isLoading: resourcesLoading } = useQuery({
    queryKey: ['resources'],
    queryFn: () => resourcesApi.listResources(token!),
    enabled: !!token,
  })

  const { data: subscriptionsData, isLoading: subscriptionsLoading } = useSubscriptions()

  const resources = resourcesData?.items ?? []
  const subscriptions = subscriptionsData?.items ?? []

  const filteredResources = resources.filter((r) =>
    r.display_name.toLowerCase().includes(search.toLowerCase())
  )

  const filteredSubscriptions = subscriptions.filter((s) =>
    s.display_name.toLowerCase().includes(search.toLowerCase())
  )

  const tabs: { key: Tab; label: string }[] = [
    { key: 'active', label: 'Aktive Services' },
    { key: 'subscriptions', label: 'Subscriptions' },
    { key: 'all', label: 'Alle' },
  ]

  const isLoading = resourcesLoading || subscriptionsLoading

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">My Services</h1>

      <div className="mb-4">
        <input
          type="text"
          placeholder="Suche nach Name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-gray-300 rounded px-3 py-2 text-sm w-full max-w-xs"
        />
      </div>

      <div className="flex space-x-1 mb-6 border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === tab.key
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-500">Laden...</p>
      ) : (
        <div className="space-y-3">
          {(activeTab === 'active' || activeTab === 'all') &&
            filteredResources.map((resource) => (
              <div key={resource.id} className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm">{resource.display_name}</p>
                    <p className="text-xs text-gray-500">{resource.template_slug}</p>
                  </div>
                  <StatusBadge status={resource.status} />
                </div>
              </div>
            ))}

          {(activeTab === 'subscriptions' || activeTab === 'all') &&
            filteredSubscriptions.map((sub) => (
              <div key={sub.id} className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm">{sub.display_name}</p>
                    <p className="text-xs text-gray-500">{sub.template_slug}</p>
                  </div>
                  <StatusBadge status={sub.status} />
                </div>
              </div>
            ))}

          {activeTab === 'active' && filteredResources.length === 0 && (
            <p className="text-sm text-gray-500">Keine aktiven Services vorhanden.</p>
          )}
          {activeTab === 'subscriptions' && filteredSubscriptions.length === 0 && (
            <p className="text-sm text-gray-500">Keine Subscriptions vorhanden.</p>
          )}
          {activeTab === 'all' && filteredResources.length === 0 && filteredSubscriptions.length === 0 && (
            <p className="text-sm text-gray-500">Keine Services vorhanden.</p>
          )}
        </div>
      )}
    </div>
  )
}
