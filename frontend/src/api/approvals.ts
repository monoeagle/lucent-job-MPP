import { apiClient } from './client'
import type { ApprovalRequest, ApprovalListResponse } from '../types/approval'

export const approvalsApi = {
  async listPendingApprovals(token: string): Promise<ApprovalListResponse> {
    return (await apiClient.get('/api/v1/approvals?status=pending', token)) as ApprovalListResponse
  },

  async getApproval(token: string, approvalId: string): Promise<ApprovalRequest> {
    return (await apiClient.get(`/api/v1/approvals/${approvalId}`, token)) as ApprovalRequest
  },

  async approve(token: string, approvalId: string, reason?: string): Promise<ApprovalRequest> {
    return (await apiClient.post(`/api/v1/approvals/${approvalId}/approve`, { reason }, token)) as ApprovalRequest
  },

  async reject(token: string, approvalId: string, reason: string): Promise<ApprovalRequest> {
    return (await apiClient.post(`/api/v1/approvals/${approvalId}/reject`, { reason }, token)) as ApprovalRequest
  },
}
