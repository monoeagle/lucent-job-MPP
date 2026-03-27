import { useState } from 'react'
import { useNotifications, useMarkRead, useMarkAllRead } from '../hooks/useNotifications'
import type { Notification } from '../api/notifications'

const EVENT_BADGES: Record<string, { label: string; color: string }> = {
  order_submitted: { label: 'Order', color: 'bg-blue-100 text-blue-700' },
  order_approved: { label: 'Order', color: 'bg-green-100 text-green-700' },
  order_rejected: { label: 'Order', color: 'bg-red-100 text-red-700' },
  order_provisioned: { label: 'Order', color: 'bg-green-100 text-green-700' },
  order_failed: { label: 'Order', color: 'bg-red-100 text-red-700' },
  approval_requested: { label: 'Approval', color: 'bg-yellow-100 text-yellow-700' },
  approval_decided: { label: 'Approval', color: 'bg-yellow-100 text-yellow-700' },
  template_deprecated: { label: 'System', color: 'bg-gray-100 text-gray-700' },
  system_maintenance: { label: 'System', color: 'bg-gray-100 text-gray-700' },
}

function NotificationItem({ notif, onRead }: { notif: Notification; onRead: () => void }) {
  const isUnread = !notif.read_at
  const badge = EVENT_BADGES[notif.event_type] ?? { label: notif.event_type, color: 'bg-gray-100 text-gray-600' }
  const date = new Date(notif.created_at).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })

  return (
    <div
      data-testid="notification-item"
      data-unread={String(isUnread)}
      onClick={() => isUnread && onRead()}
      className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer ${isUnread ? 'bg-blue-50' : 'hover:bg-gray-50'}`}
    >
      <div className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${isUnread ? 'bg-blue-500' : 'bg-gray-300'}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-xs px-2 py-0.5 rounded-full ${badge.color}`}>{badge.label}</span>
          <span className="text-xs text-gray-400">{date}</span>
        </div>
        <p className={`text-sm ${isUnread ? 'font-semibold text-gray-900' : 'text-gray-600'}`}>{notif.subject}</p>
        <p className="text-xs text-gray-400 mt-0.5 truncate">{notif.body}</p>
      </div>
    </div>
  )
}

export default function Notifications() {
  const [filter, setFilter] = useState<'all' | 'unread'>('all')
  const { data, isLoading } = useNotifications({ limit: 50 })
  const markRead = useMarkRead()
  const markAllRead = useMarkAllRead()

  const notifications = data?.items ?? []
  const filtered = filter === 'unread' ? notifications.filter((n) => !n.read_at) : notifications

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Benachrichtigungen</h1>
        <button onClick={() => markAllRead.mutate()}
          disabled={markAllRead.isPending}
          className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50">
          Alle als gelesen markieren
        </button>
      </div>

      <div className="flex gap-2 mb-4">
        <button onClick={() => setFilter('all')}
          className={`px-3 py-1 rounded-full text-sm ${filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
          Alle
        </button>
        <button onClick={() => setFilter('unread')}
          className={`px-3 py-1 rounded-full text-sm ${filter === 'unread' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
          Ungelesen
        </button>
      </div>

      {isLoading ? (
        <p className="text-gray-500">Lade Benachrichtigungen...</p>
      ) : filtered.length === 0 ? (
        <p className="text-gray-400">Keine Benachrichtigungen vorhanden</p>
      ) : (
        <div className="space-y-1">
          {filtered.map((n) => (
            <NotificationItem key={n.id} notif={n} onRead={() => markRead.mutate(n.id)} />
          ))}
        </div>
      )}
    </div>
  )
}
