import { apiClient } from './client'
import type { TemplateListResponse, ServiceTemplateDetail, CategoriesResponse, VersionsResponse } from '../types/catalog'

export interface CatalogFilters {
  status?: string
  type?: string
  category?: string
  q?: string
  limit?: number
  offset?: number
}

export const catalogApi = {
  async listTemplates(token: string, filters?: CatalogFilters): Promise<TemplateListResponse> {
    const params = new URLSearchParams()
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== '') params.set(key, String(value))
      })
    }
    const query = params.toString()
    const url = `/api/v1/catalog/templates${query ? `?${query}` : ''}`
    return (await apiClient.get(url, token)) as TemplateListResponse
  },

  async getTemplate(token: string, slug: string, version?: string): Promise<ServiceTemplateDetail> {
    const url = version
      ? `/api/v1/catalog/templates/${slug}?version=${version}`
      : `/api/v1/catalog/templates/${slug}`
    return (await apiClient.get(url, token)) as ServiceTemplateDetail
  },

  async getCategories(token: string): Promise<CategoriesResponse> {
    return (await apiClient.get('/api/v1/catalog/categories', token)) as CategoriesResponse
  },

  async getVersions(token: string, slug: string): Promise<VersionsResponse> {
    return (await apiClient.get(`/api/v1/catalog/templates/${slug}/versions`, token)) as VersionsResponse
  },
}
