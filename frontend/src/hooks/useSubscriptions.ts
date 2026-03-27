import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { subscriptionsApi } from '../api/subscriptions'
import { useAuthStore } from '../store/authStore'

export function useSubscriptions(params?: { status?: string; limit?: number; offset?: number }) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['subscriptions', params],
    queryFn: () => subscriptionsApi.list(token!, params),
    enabled: !!token,
  })
}

export function useSubscription(id: string | null) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['subscription', id],
    queryFn: () => subscriptionsApi.get(token!, id!),
    enabled: !!token && !!id,
  })
}

export function useRequestChange(id: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ parameters, reason }: { parameters: Record<string, unknown>; reason: string }) =>
      subscriptionsApi.requestChange(token!, id, parameters, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['subscription', id] })
      qc.invalidateQueries({ queryKey: ['subscriptions'] })
    },
  })
}

export function useRequestCancel(id: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (reason: string) => subscriptionsApi.requestCancel(token!, id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['subscription', id] })
      qc.invalidateQueries({ queryKey: ['subscriptions'] })
    },
  })
}

export function useSubscriptionGroups() {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['subscription-groups'],
    queryFn: () => subscriptionsApi.listGroups(token!),
    enabled: !!token,
  })
}
