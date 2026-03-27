import { useQuery } from '@tanstack/react-query'
import { catalogApi, type CatalogFilters } from '../api/catalog'
import { useAuthStore } from '../store/authStore'

export function useTemplates(filters?: CatalogFilters) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['templates', filters],
    queryFn: () => catalogApi.listTemplates(token!, filters),
    enabled: !!token,
  })
}

export function useTemplate(slug: string | null, version?: string) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['template', slug, version],
    queryFn: () => catalogApi.getTemplate(token!, slug!, version),
    enabled: !!token && !!slug,
  })
}

export function useCategories() {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['categories'],
    queryFn: () => catalogApi.getCategories(token!),
    enabled: !!token,
  })
}
