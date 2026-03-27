import { apiClient } from './client'
import type { Order, OrderListResponse, SubmitResponse, ValidationResult, TofuExport, OrderItemGroup } from '../types/order'

export interface CreateOrderBody {
  title: string
  business_reason?: string
  desired_date?: string
  context?: Record<string, string>
}

export interface AddItemBody {
  template_slug: string
  template_version: string
  parameters: Record<string, unknown>
  quantity?: number
  instance_parameters?: Record<string, unknown>[]
}

export interface CreateGroupBody {
  name: string
  description?: string
}

export interface UpdateGroupBody {
  name?: string
  description?: string
}

export const ordersApi = {
  async listOrders(token: string, params?: { status?: string; limit?: number; offset?: number }): Promise<OrderListResponse> {
    const qs = new URLSearchParams()
    if (params) Object.entries(params).forEach(([k, v]) => { if (v !== undefined) qs.set(k, String(v)) })
    const query = qs.toString()
    return (await apiClient.get(`/api/v1/orders${query ? `?${query}` : ''}`, token)) as OrderListResponse
  },

  async getOrder(token: string, orderId: string): Promise<Order> {
    return (await apiClient.get(`/api/v1/orders/${orderId}`, token)) as Order
  },

  async createOrder(token: string, body: CreateOrderBody): Promise<Order> {
    return (await apiClient.post('/api/v1/orders', body, token)) as Order
  },

  async updateOrder(token: string, orderId: string, body: Partial<CreateOrderBody>): Promise<Order> {
    return (await apiClient.patch(`/api/v1/orders/${orderId}`, body, token)) as Order
  },

  async deleteOrder(token: string, orderId: string): Promise<void> {
    await apiClient.del(`/api/v1/orders/${orderId}`, token)
  },

  async addItem(token: string, orderId: string, body: AddItemBody): Promise<unknown> {
    return apiClient.post(`/api/v1/orders/${orderId}/items`, body, token)
  },

  async updateItem(token: string, orderId: string, itemId: string, parameters: Record<string, unknown>): Promise<unknown> {
    return apiClient.patch(`/api/v1/orders/${orderId}/items/${itemId}`, { parameters }, token)
  },

  async removeItem(token: string, orderId: string, itemId: string): Promise<void> {
    await apiClient.del(`/api/v1/orders/${orderId}/items/${itemId}`, token)
  },

  async validateOrder(token: string, orderId: string): Promise<ValidationResult> {
    return (await apiClient.post(`/api/v1/orders/${orderId}/validate`, undefined, token)) as ValidationResult
  },

  async submitOrder(token: string, orderId: string): Promise<SubmitResponse> {
    return (await apiClient.post(`/api/v1/orders/${orderId}/submit`, undefined, token)) as SubmitResponse
  },

  async getStatus(token: string, orderId: string): Promise<unknown> {
    return apiClient.get(`/api/v1/orders/${orderId}/status`, token)
  },

  async getExport(token: string, orderId: string): Promise<TofuExport> {
    return (await apiClient.get(`/api/v1/orders/${orderId}/export/tofu`, token)) as TofuExport
  },

  async createGroup(token: string, orderId: string, body: CreateGroupBody): Promise<OrderItemGroup> {
    return (await apiClient.post(`/api/v1/orders/${orderId}/groups`, body, token)) as OrderItemGroup
  },

  async updateGroup(token: string, orderId: string, groupId: string, body: UpdateGroupBody): Promise<OrderItemGroup> {
    return (await apiClient.patch(`/api/v1/orders/${orderId}/groups/${groupId}`, body, token)) as OrderItemGroup
  },

  async deleteGroup(token: string, orderId: string, groupId: string): Promise<void> {
    await apiClient.del(`/api/v1/orders/${orderId}/groups/${groupId}`, token)
  },

  async reorderGroups(token: string, orderId: string, positions: { group_id: string; position: number }[]): Promise<unknown> {
    return apiClient.put(`/api/v1/orders/${orderId}/groups/reorder`, { positions }, token)
  },

  async assignItemToGroup(token: string, orderId: string, itemId: string, groupId: string | null): Promise<unknown> {
    return apiClient.patch(`/api/v1/orders/${orderId}/items/${itemId}`, { group_id: groupId }, token)
  },
}
