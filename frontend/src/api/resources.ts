import { apiClient } from './client'

export interface Resource {
  id: string
  order_id: string
  order_number: string
  display_name: string
  template_slug: string
  parameters: Record<string, unknown>
  status: string
  created_at: string
}

export interface ResourceListResponse {
  items: Resource[]
  total: number
}

export const resourcesApi = {
  async listResources(token: string, params?: { limit?: number; offset?: number }): Promise<ResourceListResponse> {
    const qs = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined) qs.set(k, String(v))
      })
    }
    const query = qs.toString()
    return (await apiClient.get(`/api/v1/resources${query ? `?${query}` : ''}`, token)) as ResourceListResponse
  },
}
