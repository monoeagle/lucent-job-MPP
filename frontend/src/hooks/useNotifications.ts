import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notificationsApi } from '../api/notifications'
import { useAuthStore } from '../store/authStore'

export function useNotifications(params?: { limit?: number; offset?: number }) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['notifications', params],
    queryFn: () => notificationsApi.list(token!, params),
    enabled: !!token,
  })
}

export function useUnreadCount() {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['notifications-unread-count'],
    queryFn: () => notificationsApi.unreadCount(token!),
    enabled: !!token,
    refetchInterval: 60_000,
  })
}

export function useMarkRead() {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(token!, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] })
      qc.invalidateQueries({ queryKey: ['notifications-unread-count'] })
    },
  })
}

export function useMarkAllRead() {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => notificationsApi.markAllRead(token!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] })
      qc.invalidateQueries({ queryKey: ['notifications-unread-count'] })
    },
  })
}
