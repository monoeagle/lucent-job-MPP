export interface Subscription {
  id: string
  order_item_id: string
  group_subscription_id: string | null
  requester_id: string
  status: string
  display_name: string
  template_slug: string
  template_version: string
  parameters: Record<string, unknown>
  pending_changes: {
    type: string
    parameters?: Record<string, unknown>
    reason?: string
    requested_at?: string
  } | null
  monthly_cost_eur: number | null
  activated_at: string | null
  cancelled_at: string | null
  created_at: string
  updated_at: string
}

export interface SubscriptionGroup {
  id: string
  name: string
  requester_id: string
  subscriptions: Subscription[]
  created_at: string
}

export interface SubscriptionListResponse {
  items: Subscription[]
  total: number
  limit: number
  offset: number
}
