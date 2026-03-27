export interface ApprovalRequest {
  id: string
  order_id: string
  status: string
  approval_rule_ids: string[]
  requested_at: string
  deadline_at: string
  decided_by: string | null
  decided_at: string | null
  decision_reason: string | null
}

export interface ApprovalListResponse {
  items: ApprovalRequest[]
  total: number
}
