import { apiClient } from './client'

export interface Notification {
  id: string
  event_type: string
  recipient_email: string
  recipient_id: string
  subject: string
  body: string
  status: string
  attempts: number
  created_at: string
  sent_at: string | null
  error_message: string | null
  read_at: string | null
}

export interface NotificationListResponse {
  items: Notification[]
  total: number
  limit: number
  offset: number
}

export const notificationsApi = {
  async list(token: string, params?: { limit?: number; offset?: number }): Promise<NotificationListResponse> {
    const qs = new URLSearchParams()
    if (params) Object.entries(params).forEach(([k, v]) => { if (v !== undefined) qs.set(k, String(v)) })
    const query = qs.toString()
    return (await apiClient.get(`/api/v1/notifications${query ? `?${query}` : ''}`, token)) as NotificationListResponse
  },

  async markRead(token: string, id: string): Promise<Notification> {
    return (await apiClient.patch(`/api/v1/notifications/${id}/read`, {}, token)) as Notification
  },

  async markAllRead(token: string): Promise<{ marked_count: number }> {
    return (await apiClient.patch('/api/v1/notifications/read-all', {}, token)) as { marked_count: number }
  },

  async unreadCount(token: string): Promise<{ count: number }> {
    return (await apiClient.get('/api/v1/notifications/unread-count', token)) as { count: number }
  },
}
