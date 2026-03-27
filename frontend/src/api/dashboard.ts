import { apiClient } from './client'

export interface DashboardStats {
  orders_by_status: Record<string, number>
  orders_by_month: Array<{ month: string; count: number }>
  total_templates: number
  active_resources: number
  pending_approvals: number
  popular_templates: Array<{
    slug: string
    display_name: string
    category: string
    order_count: number
  }>
}

export interface SearchResult {
  query: string
  orders: Array<{ id: string; order_number: string; title: string; status: string }>
  templates: Array<{ slug: string; display_name: string; category: string; status: string }>
  resources: Array<{ id: string; display_name: string; template_slug: string }>
}

export const dashboardApi = {
  async getStats(token: string): Promise<DashboardStats> {
    return (await apiClient.get('/api/v1/dashboard/stats', token)) as DashboardStats
  },

  async search(token: string, query: string, limit = 5): Promise<SearchResult> {
    return (await apiClient.get(
      `/api/v1/search?q=${encodeURIComponent(query)}&limit=${limit}`,
      token,
    )) as SearchResult
  },
}
