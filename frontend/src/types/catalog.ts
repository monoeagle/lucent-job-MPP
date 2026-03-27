// frontend/src/types/catalog.ts

export interface EnumOption {
  value: string
  label: string
  enabled: boolean
  metadata?: Record<string, unknown>
}

export interface ParameterConstraints {
  min?: number
  max?: number
  step?: number
  unit?: string
  min_length?: number
  max_length?: number
  pattern?: string
  allowed_values?: string[]
  options?: EnumOption[]
  min_bytes?: number
  max_bytes?: number
  display_unit?: string
}

export interface DependencyRule {
  parameter_key: string
  operator: string
  value: unknown
  effect: string
}

export interface ParameterDefinition {
  key: string
  label: string
  description: string | null
  type: string
  required: boolean
  default_value: unknown
  tofu_variable_name: string
  display_order: number
  group: string | null
  constraints: ParameterConstraints
  depends_on: DependencyRule[]
  affects_options_of: string[]
}

export interface CrossParameterRule {
  rule_id: string
  description: string
  parameter_keys: string[]
  expression: string
  error_message: string
}

export interface ServiceTemplate {
  id: string
  slug: string
  version: string
  type: string
  display_name: string
  description: string | null
  category: string
  icon_identifier: string | null
  status: string
  created_at: string
  deprecated_at: string | null
  deprecated_by: { id: string; slug: string; version: string } | null
  estimated_cost_eur_per_month: number | null
  approval_always_required: boolean
}

export interface ServiceTemplateDetail extends ServiceTemplate {
  tofu_module_source: string
  parameters: ParameterDefinition[]
  cross_parameter_rules: CrossParameterRule[]
  metadata: Record<string, unknown>
}

export interface TemplateListResponse {
  data: ServiceTemplate[]
  total: number
  limit: number
  offset: number
}

export interface CategoryItem {
  name: string
  template_count: number
}

export interface CategoriesResponse {
  categories: CategoryItem[]
}

export interface TemplateVersion {
  id: string
  version: string
  status: string
  created_at: string
  deprecated_at?: string
}

export interface VersionsResponse {
  slug: string
  versions: TemplateVersion[]
}
