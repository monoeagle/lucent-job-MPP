export interface ApprovalOrderItem {
  display_name: string
  template_slug: string
  template_version: string
  parameters: Record<string, unknown>
  quantity: number
}

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
  requester_id?: string
  order_title?: string
  order_number?: string
  business_reason?: string | null
  order_items?: ApprovalOrderItem[]
}

export interface ApprovalListResponse {
  items: ApprovalRequest[]
  total: number
}
