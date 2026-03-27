// frontend/src/types/order.ts

export interface ValidationViolation {
  parameter_key: string
  rule: string
  message: string
}

export interface OrderItem {
  id: string
  template_slug: string
  template_version: string
  display_name: string
  parameters: Record<string, unknown>
  position: number
  validation_state: 'unchecked' | 'valid' | 'invalid'
  validation_errors: ValidationViolation[]
  created_at: string
  updated_at: string
  group_id: string | null
  quantity: number
  instance_parameters: Record<string, unknown>[]
}

export interface OrderItemGroup {
  id: string
  order_id: string
  name: string
  description: string | null
  position: number
  items: OrderItem[]
}

export interface Order {
  id: string
  order_number: string
  requester_id: string
  status: string
  title: string
  business_reason: string | null
  desired_date: string | null
  items: OrderItem[]
  context: Record<string, string> | null
  submitted_at: string | null
  created_at: string
  updated_at: string
  groups: OrderItemGroup[]
  ungrouped_items: OrderItem[]
}

export interface OrderListItem {
  id: string
  order_number: string
  status: string
  title: string
  item_count: number
  created_at: string
  updated_at: string
}

export interface OrderListResponse {
  total: number
  limit: number
  offset: number
  items: OrderListItem[]
}

export interface SubmitResponse {
  order_id: string
  order_number: string
  status: string
  item_count: number
  submitted_at: string
  message: string
}

export interface ValidationResult {
  order_id: string
  order_status: string
  all_valid: boolean
  item_results: Array<{
    item_id: string
    template_slug: string
    template_version: string
    position: number
    validation_state: string
    violations: ValidationViolation[]
  }>
}

export interface TofuExport {
  order_id: string
  order_number: string
  exported_at: string
  readonly_notice: string | null
  items: Array<{
    order_item_id: string
    template_slug: string
    template_version: string
    position: number
    module_source: string | null
    variables: Record<string, unknown> | null
    error: { code: string; message: string } | null
  }>
}
