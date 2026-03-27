import { apiClient } from './client'
import type { Subscription, SubscriptionGroup, SubscriptionListResponse } from '../types/subscription'

export const subscriptionsApi = {
  async list(token: string, params?: { status?: string; limit?: number; offset?: number }): Promise<SubscriptionListResponse> {
    const qs = new URLSearchParams()
    if (params) Object.entries(params).forEach(([k, v]) => { if (v !== undefined) qs.set(k, String(v)) })
    const query = qs.toString()
    return (await apiClient.get(`/api/v1/subscriptions${query ? `?${query}` : ''}`, token)) as SubscriptionListResponse
  },

  async get(token: string, id: string): Promise<Subscription> {
    return (await apiClient.get(`/api/v1/subscriptions/${id}`, token)) as Subscription
  },

  async requestChange(token: string, id: string, parameters: Record<string, unknown>, reason: string): Promise<Subscription> {
    return (await apiClient.post(`/api/v1/subscriptions/${id}/change`, { parameters, reason }, token)) as Subscription
  },

  async requestCancel(token: string, id: string, reason: string): Promise<Subscription> {
    return (await apiClient.post(`/api/v1/subscriptions/${id}/cancel`, { reason }, token)) as Subscription
  },

  async listGroups(token: string): Promise<SubscriptionGroup[]> {
    return (await apiClient.get('/api/v1/subscriptions/groups', token)) as SubscriptionGroup[]
  },

  async getGroup(token: string, groupId: string): Promise<SubscriptionGroup> {
    return (await apiClient.get(`/api/v1/subscriptions/groups/${groupId}`, token)) as SubscriptionGroup
  },
}
