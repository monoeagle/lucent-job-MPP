import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../api/dashboard'
import { useAuthStore } from '../store/authStore'

export function useStats() {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => dashboardApi.getStats(token!),
    enabled: !!token,
    staleTime: 60_000,
  })
}

export function useSearch(query: string) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['search', query],
    queryFn: () => dashboardApi.search(token!, query),
    enabled: !!token && query.length >= 2,
    staleTime: 10_000,
  })
}
