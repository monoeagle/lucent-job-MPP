import { useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { useUnreadCount } from '../hooks/useNotifications'
import MyServices from './MyServices'
import MyRequests from './MyRequests'
import Notifications from './Notifications'
import Approvals from './Approvals'

type WorkspaceTab = 'services' | 'requests' | 'notifications' | 'reviews'

const TABS: Array<{ key: WorkspaceTab; label: string; roles?: string[] }> = [
  { key: 'services', label: 'My Services' },
  { key: 'requests', label: 'My Requests' },
  { key: 'notifications', label: 'Notifications' },
  { key: 'reviews', label: 'Review Requests', roles: ['approver', 'admin'] },
]

export default function Workspace() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = (searchParams.get('tab') as WorkspaceTab) || 'services'
  const user = useAuthStore((s) => s.user)
  const { data: unreadData } = useUnreadCount()
  const unreadCount = unreadData?.count ?? 0

  const visibleTabs = TABS.filter((tab) => {
    if (!tab.roles) return true
    return tab.roles.some((role) => user?.roles.includes(role))
  })

  const setTab = (tab: WorkspaceTab) => {
    setSearchParams({ tab })
  }

  return (
    <div>
      {/* Tab bar */}
      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {visibleTabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {tab.label}
            {tab.key === 'notifications' && unreadCount > 0 && (
              <span className="ml-2 bg-red-500 text-white text-xs rounded-full w-5 h-5 inline-flex items-center justify-center">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'services' && <MyServices />}
      {activeTab === 'requests' && <MyRequests />}
      {activeTab === 'notifications' && <Notifications />}
      {activeTab === 'reviews' && <Approvals />}
    </div>
  )
}
