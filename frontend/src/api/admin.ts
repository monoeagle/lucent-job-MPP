import { apiClient } from './client'

export interface DashboardData {
  order_counts: Record<string, number>
  pending_approvals: number
  active_resources: number
  system_health: { status?: string; uptime?: string; version?: string; database?: string; cmdb?: string }
  recent_orders: Array<{
    id: string
    order_number: string
    title: string
    status: string
    created_at: string
  }>
}

export interface AuditLogEntry {
  id: string
  action: string
  entity_type: string
  entity_id: string
  user_id: string
  details: Record<string, unknown> | null
  created_at: string
}

export interface AuditLogResponse {
  items: AuditLogEntry[]
  total: number
}

export interface ApprovalRule {
  id: string
  name: string
  description: string
  conditions: Record<string, unknown>
  approver_roles: string[]
  active: boolean
  created_at: string
}

export interface AvailabilityRule {
  id: string
  name: string
  template_slug: string
  conditions: Record<string, unknown>
  active: boolean
}

export interface ContextRestriction {
  id: string
  name: string
  restriction_type: string
  conditions: Record<string, unknown>
  active: boolean
}

export interface TenantAssignment {
  id: string
  tenant_id: string
  tenant_name: string
  template_slug: string
  active: boolean
}

export const adminApi = {
  async getDashboard(token: string): Promise<DashboardData> {
    return (await apiClient.get('/api/v1/admin/dashboard', token)) as DashboardData
  },

  async getAuditLog(
    token: string,
    params?: { action?: string; entity_type?: string; from?: string; to?: string; limit?: number; offset?: number },
  ): Promise<AuditLogResponse> {
    const qs = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined) qs.set(k, String(v))
      })
    }
    const query = qs.toString()
    return (await apiClient.get(`/api/v1/admin/audit-log${query ? `?${query}` : ''}`, token)) as AuditLogResponse
  },

  async exportAuditLog(token: string, params?: { from?: string; to?: string }): Promise<Blob> {
    const qs = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined) qs.set(k, String(v))
      })
    }
    const query = qs.toString()
    const response = await fetch(`/api/v1/admin/audit-log/export${query ? `?${query}` : ''}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.blob()
  },

  async listApprovalRules(token: string): Promise<ApprovalRule[]> {
    return (await apiClient.get('/api/v1/admin/rules/approvals', token)) as ApprovalRule[]
  },

  async createApprovalRule(token: string, rule: Omit<ApprovalRule, 'id' | 'created_at'>): Promise<ApprovalRule> {
    return (await apiClient.post('/api/v1/admin/rules/approvals', rule, token)) as ApprovalRule
  },

  async deleteApprovalRule(token: string, ruleId: string): Promise<void> {
    await apiClient.del(`/api/v1/admin/rules/approvals/${ruleId}`, token)
  },

  async listAvailabilityRules(token: string): Promise<AvailabilityRule[]> {
    return (await apiClient.get('/api/v1/admin/rules/availability', token)) as AvailabilityRule[]
  },

  async listContextRestrictions(token: string): Promise<ContextRestriction[]> {
    return (await apiClient.get('/api/v1/admin/rules/context-restrictions', token)) as ContextRestriction[]
  },

  async listTenantAssignments(token: string): Promise<TenantAssignment[]> {
    return (await apiClient.get('/api/v1/admin/rules/tenant-assignments', token)) as TenantAssignment[]
  },
}
