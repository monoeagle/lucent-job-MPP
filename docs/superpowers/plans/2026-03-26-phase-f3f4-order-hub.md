# Phase F3+F4: Order Hub + Validation + Submit + Export — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Order Hub — the central page for creating, managing, validating, and submitting orders with multiple service items. Includes the ParameterForm for dynamic item configuration, order validation with inline errors, submit flow, status polling, and JSON export view.

**Architecture:** Orders API module + tanstack-query hooks. OrderDetail page as the hub. Item configuration in the existing Drawer component with a dynamic ParameterForm. Validation displays inline per item. Submit transitions to polling mode. Export as readonly JSON view.

**Tech Stack:** React 19, TypeScript, TailwindCSS, tanstack-query, react-hook-form, zod

---

## File Structure

```
frontend/src/
├── types/
│   └── order.ts                        # Order, OrderItem, ValidationViolation types
├── api/
│   └── orders.ts                       # Order API calls (CRUD, items, validate, submit, export)
├── hooks/
│   ├── useOrders.ts                    # tanstack-query hooks for orders
│   └── useOrderStatus.ts              # Polling hook for status updates
├── components/
│   ├── orders/
│   │   ├── OrderItemCard.tsx           # Item card with status, params summary, edit/remove
│   │   ├── OrderActions.tsx            # Validate/Submit/Delete/Export buttons
│   │   └── ValidationErrors.tsx        # Inline violation display per item
│   └── ParameterForm/
│       ├── ParameterForm.tsx           # Dynamic form from template schema
│       ├── IntegerField.tsx
│       ├── EnumField.tsx
│       ├── BooleanField.tsx
│       ├── StringField.tsx
│       └── SizeBytesField.tsx
└── pages/
    ├── OrderList.tsx
    ├── OrderNew.tsx
    ├── OrderDetail.tsx                 # The Hub
    └── OrderExport.tsx
```

---

### Task 1: Order Types

**Files:**
- Create: `frontend/src/types/order.ts`

- [ ] **Step 1: Create types**

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/order.ts
git commit -m "feat(frontend): add order TypeScript types"
```

---

### Task 2: Orders API Module

**Files:**
- Create: `frontend/src/api/orders.ts`
- Test: `frontend/tests/api/orders.test.ts`

- [ ] **Step 1: Write test**

```typescript
// frontend/tests/api/orders.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ordersApi } from '../../src/api/orders'
import { apiClient } from '../../src/api/client'

vi.mock('../../src/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), del: vi.fn() },
}))

describe('ordersApi', () => {
  beforeEach(() => vi.clearAllMocks())

  it('createOrder posts correct body', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ id: '1', status: 'draft' })
    await ordersApi.createOrder('tok', { title: 'Test', business_reason: 'reason' })
    expect(apiClient.post).toHaveBeenCalledWith('/api/v1/orders',
      { title: 'Test', business_reason: 'reason' }, 'tok')
  })

  it('getOrder calls correct URL', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ id: '1' })
    await ordersApi.getOrder('tok', 'order-1')
    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/orders/order-1', 'tok')
  })

  it('addItem posts to correct URL', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ item: { id: 'i1' } })
    await ordersApi.addItem('tok', 'o1', { template_slug: 'vm', template_version: '1.0.0', parameters: {} })
    expect(apiClient.post).toHaveBeenCalledWith('/api/v1/orders/o1/items',
      { template_slug: 'vm', template_version: '1.0.0', parameters: {} }, 'tok')
  })

  it('validateOrder posts to validate URL', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ all_valid: true })
    await ordersApi.validateOrder('tok', 'o1')
    expect(apiClient.post).toHaveBeenCalledWith('/api/v1/orders/o1/validate', undefined, 'tok')
  })

  it('submitOrder posts to submit URL', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ status: 'submitted' })
    await ordersApi.submitOrder('tok', 'o1')
    expect(apiClient.post).toHaveBeenCalledWith('/api/v1/orders/o1/submit', undefined, 'tok')
  })

  it('getExport calls export URL', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ items: [] })
    await ordersApi.getExport('tok', 'o1')
    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/orders/o1/export/tofu', 'tok')
  })

  it('deleteOrder calls del', async () => {
    vi.mocked(apiClient.del).mockResolvedValue(undefined)
    await ordersApi.deleteOrder('tok', 'o1')
    expect(apiClient.del).toHaveBeenCalledWith('/api/v1/orders/o1', 'tok')
  })
})
```

- [ ] **Step 2: Implement**

```typescript
// frontend/src/api/orders.ts
import { apiClient } from './client'
import type { Order, OrderListResponse, SubmitResponse, ValidationResult, TofuExport } from '../types/order'

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
}
```

- [ ] **Step 3: Run tests, commit**

```bash
git add frontend/src/api/orders.ts frontend/tests/api/orders.test.ts
git commit -m "feat(frontend): add orders API module"
```

---

### Task 3: Order Hooks + Status Polling

**Files:**
- Create: `frontend/src/hooks/useOrders.ts`
- Create: `frontend/src/hooks/useOrderStatus.ts`

- [ ] **Step 1: Implement**

```typescript
// frontend/src/hooks/useOrders.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ordersApi, type CreateOrderBody, type AddItemBody } from '../api/orders'
import { useAuthStore } from '../store/authStore'

export function useOrders(params?: { status?: string; limit?: number; offset?: number }) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['orders', params],
    queryFn: () => ordersApi.listOrders(token!, params),
    enabled: !!token,
  })
}

export function useOrder(orderId: string | null) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['order', orderId],
    queryFn: () => ordersApi.getOrder(token!, orderId!),
    enabled: !!token && !!orderId,
  })
}

export function useCreateOrder() {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateOrderBody) => ordersApi.createOrder(token!, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orders'] }),
  })
}

export function useAddItem(orderId: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: AddItemBody) => ordersApi.addItem(token!, orderId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}

export function useUpdateItem(orderId: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ itemId, parameters }: { itemId: string; parameters: Record<string, unknown> }) =>
      ordersApi.updateItem(token!, orderId, itemId, parameters),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}

export function useRemoveItem(orderId: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) => ordersApi.removeItem(token!, orderId, itemId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}

export function useValidateOrder(orderId: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => ordersApi.validateOrder(token!, orderId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}

export function useSubmitOrder(orderId: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => ordersApi.submitOrder(token!, orderId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}

export function useDeleteOrder() {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (orderId: string) => ordersApi.deleteOrder(token!, orderId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orders'] }),
  })
}

export function useOrderExport(orderId: string | null) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['order-export', orderId],
    queryFn: () => ordersApi.getExport(token!, orderId!),
    enabled: !!token && !!orderId,
  })
}
```

```typescript
// frontend/src/hooks/useOrderStatus.ts
import { useQuery } from '@tanstack/react-query'
import { ordersApi } from '../api/orders'
import { useAuthStore } from '../store/authStore'

const POLLING_STATUSES = ['submitted', 'pending_approval', 'provisioning']

export function useOrderStatus(orderId: string | null, currentStatus: string | null) {
  const token = useAuthStore((s) => s.token)
  const shouldPoll = !!currentStatus && POLLING_STATUSES.includes(currentStatus)

  return useQuery({
    queryKey: ['order-status', orderId],
    queryFn: () => ordersApi.getStatus(token!, orderId!),
    enabled: !!token && !!orderId && shouldPoll,
    refetchInterval: shouldPoll ? 10_000 : false,
  })
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useOrders.ts frontend/src/hooks/useOrderStatus.ts
git commit -m "feat(frontend): add order hooks with mutations and status polling"
```

---

### Task 4: ParameterForm — Dynamic Form from Template Schema

**Files:**
- Create: `frontend/src/components/ParameterForm/ParameterForm.tsx`
- Create: `frontend/src/components/ParameterForm/IntegerField.tsx`
- Create: `frontend/src/components/ParameterForm/EnumField.tsx`
- Create: `frontend/src/components/ParameterForm/BooleanField.tsx`
- Create: `frontend/src/components/ParameterForm/StringField.tsx`
- Create: `frontend/src/components/ParameterForm/SizeBytesField.tsx`
- Test: `frontend/tests/components/ParameterForm.test.tsx`

- [ ] **Step 1: Write test**

```typescript
// frontend/tests/components/ParameterForm.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ParameterForm from '../../src/components/ParameterForm/ParameterForm'
import type { ParameterDefinition } from '../../src/types/catalog'

const mockParams: ParameterDefinition[] = [
  { key: 'cpu', label: 'CPU-Kerne', type: 'integer', required: true,
    tofu_variable_name: 'cpu', display_order: 1, group: 'Compute',
    constraints: { min: 1, max: 64 }, depends_on: [], affects_options_of: [],
    description: null, default_value: 2 },
  { key: 'os', label: 'Betriebssystem', type: 'enum', required: true,
    tofu_variable_name: 'os', display_order: 2, group: 'System',
    constraints: { options: [
      { value: 'ubuntu', label: 'Ubuntu', enabled: true },
      { value: 'rhel', label: 'RHEL', enabled: true },
    ] }, depends_on: [], affects_options_of: [],
    description: null, default_value: null },
  { key: 'backup', label: 'Backup', type: 'boolean', required: false,
    tofu_variable_name: 'backup', display_order: 3, group: 'Compute',
    constraints: {}, depends_on: [], affects_options_of: [],
    description: 'Backup aktivieren', default_value: false },
]

describe('ParameterForm', () => {
  it('renders all visible parameters', () => {
    render(<ParameterForm parameters={mockParams} values={{}} onChange={vi.fn()} />)
    expect(screen.getByLabelText(/CPU-Kerne/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Betriebssystem/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Backup/)).toBeInTheDocument()
  })

  it('renders group headers', () => {
    render(<ParameterForm parameters={mockParams} values={{}} onChange={vi.fn()} />)
    expect(screen.getByText('Compute')).toBeInTheDocument()
    expect(screen.getByText('System')).toBeInTheDocument()
  })

  it('shows required indicator', () => {
    render(<ParameterForm parameters={mockParams} values={{}} onChange={vi.fn()} />)
    const cpuLabel = screen.getByText('CPU-Kerne')
    expect(cpuLabel.parentElement?.textContent).toContain('*')
  })
})
```

- [ ] **Step 2: Implement field components**

Each field receives: `label`, `value`, `onChange`, `constraints`, `required`, `description`, `errors`.

```tsx
// frontend/src/components/ParameterForm/IntegerField.tsx
interface Props {
  label: string; value: number | undefined; onChange: (v: number) => void
  constraints: { min?: number; max?: number; step?: number; unit?: string }
  required?: boolean; description?: string | null; errors?: string[]
}
export default function IntegerField({ label, value, onChange, constraints, required, description, errors }: Props) {
  return (
    <div className="mb-3">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-1">*</span>}
        {constraints.unit && <span className="text-gray-400 text-xs ml-1">({constraints.unit})</span>}
      </label>
      {description && <p className="text-xs text-gray-400 mb-1">{description}</p>}
      <input type="number" value={value ?? ''} onChange={(e) => onChange(Number(e.target.value))}
        min={constraints.min} max={constraints.max} step={constraints.step ?? 1}
        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
      {constraints.min !== undefined && constraints.max !== undefined && (
        <p className="text-xs text-gray-400 mt-0.5">{constraints.min} – {constraints.max}</p>
      )}
      {errors?.map((e, i) => <p key={i} className="text-xs text-red-500 mt-0.5">{e}</p>)}
    </div>
  )
}
```

```tsx
// frontend/src/components/ParameterForm/EnumField.tsx
import type { EnumOption } from '../../types/catalog'
interface Props {
  label: string; value: string | undefined; onChange: (v: string) => void
  options: EnumOption[]; required?: boolean; description?: string | null; errors?: string[]
}
export default function EnumField({ label, value, onChange, options, required, description, errors }: Props) {
  return (
    <div className="mb-3">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {description && <p className="text-xs text-gray-400 mb-1">{description}</p>}
      <select value={value ?? ''} onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
        <option value="">Bitte wählen...</option>
        {options.filter(o => o.enabled).map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
      {errors?.map((e, i) => <p key={i} className="text-xs text-red-500 mt-0.5">{e}</p>)}
    </div>
  )
}
```

```tsx
// frontend/src/components/ParameterForm/BooleanField.tsx
interface Props {
  label: string; value: boolean | undefined; onChange: (v: boolean) => void
  required?: boolean; description?: string | null
}
export default function BooleanField({ label, value, onChange, description }: Props) {
  return (
    <div className="mb-3 flex items-center gap-3">
      <input type="checkbox" checked={value ?? false} onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-gray-300" />
      <div>
        <label className="text-sm font-medium text-gray-700">{label}</label>
        {description && <p className="text-xs text-gray-400">{description}</p>}
      </div>
    </div>
  )
}
```

```tsx
// frontend/src/components/ParameterForm/StringField.tsx
interface Props {
  label: string; value: string | undefined; onChange: (v: string) => void
  constraints: { min_length?: number; max_length?: number; pattern?: string }
  required?: boolean; description?: string | null; errors?: string[]
}
export default function StringField({ label, value, onChange, constraints, required, description, errors }: Props) {
  return (
    <div className="mb-3">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {description && <p className="text-xs text-gray-400 mb-1">{description}</p>}
      <input type="text" value={value ?? ''} onChange={(e) => onChange(e.target.value)}
        maxLength={constraints.max_length} pattern={constraints.pattern}
        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
      {errors?.map((e, i) => <p key={i} className="text-xs text-red-500 mt-0.5">{e}</p>)}
    </div>
  )
}
```

```tsx
// frontend/src/components/ParameterForm/SizeBytesField.tsx
const UNITS = { MB: 1024 * 1024, GB: 1024 * 1024 * 1024, TB: 1024 * 1024 * 1024 * 1024 }
interface Props {
  label: string; value: number | undefined; onChange: (v: number) => void
  constraints: { min_bytes?: number; max_bytes?: number; display_unit?: string }
  required?: boolean; description?: string | null; errors?: string[]
}
export default function SizeBytesField({ label, value, onChange, constraints, required, description, errors }: Props) {
  const unit = (constraints.display_unit ?? 'GB') as keyof typeof UNITS
  const multiplier = UNITS[unit] ?? UNITS.GB
  const displayValue = value !== undefined ? Math.round(value / multiplier) : ''

  return (
    <div className="mb-3">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {description && <p className="text-xs text-gray-400 mb-1">{description}</p>}
      <div className="flex items-center gap-2">
        <input type="number" value={displayValue}
          onChange={(e) => onChange(Number(e.target.value) * multiplier)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm" />
        <span className="text-sm text-gray-500">{unit}</span>
      </div>
      {errors?.map((e, i) => <p key={i} className="text-xs text-red-500 mt-0.5">{e}</p>)}
    </div>
  )
}
```

```tsx
// frontend/src/components/ParameterForm/ParameterForm.tsx
import type { ParameterDefinition } from '../../types/catalog'
import IntegerField from './IntegerField'
import EnumField from './EnumField'
import BooleanField from './BooleanField'
import StringField from './StringField'
import SizeBytesField from './SizeBytesField'

interface Props {
  parameters: ParameterDefinition[]
  values: Record<string, unknown>
  onChange: (key: string, value: unknown) => void
  errors?: Record<string, string[]>
}

function isVisible(param: ParameterDefinition, values: Record<string, unknown>): boolean {
  const visRules = param.depends_on.filter(r => r.effect === 'visible')
  if (visRules.length === 0) return true
  return visRules.every(r => {
    const actual = values[r.parameter_key]
    switch (r.operator) {
      case 'eq': return actual === r.value
      case 'neq': return actual !== r.value
      case 'in': return Array.isArray(r.value) && r.value.includes(actual)
      case 'gt': return typeof actual === 'number' && actual > (r.value as number)
      default: return true
    }
  })
}

export default function ParameterForm({ parameters, values, onChange, errors }: Props) {
  const visible = parameters.filter(p => isVisible(p, values))
  const grouped = visible.reduce<Record<string, ParameterDefinition[]>>((acc, p) => {
    const g = p.group || 'Allgemein'
    if (!acc[g]) acc[g] = []
    acc[g].push(p)
    return acc
  }, {})

  function renderField(p: ParameterDefinition) {
    const fieldErrors = errors?.[p.key]
    const v = values[p.key]
    const change = (val: unknown) => onChange(p.key, val)

    switch (p.type) {
      case 'integer': case 'range_integer': case 'float': case 'range_float':
        return <IntegerField key={p.key} label={p.label} value={v as number | undefined}
          onChange={change as (v: number) => void} constraints={p.constraints}
          required={p.required} description={p.description} errors={fieldErrors} />
      case 'enum':
        return <EnumField key={p.key} label={p.label} value={v as string | undefined}
          onChange={change as (v: string) => void} options={p.constraints.options ?? []}
          required={p.required} description={p.description} errors={fieldErrors} />
      case 'boolean':
        return <BooleanField key={p.key} label={p.label} value={v as boolean | undefined}
          onChange={change as (v: boolean) => void} description={p.description} />
      case 'size_bytes':
        return <SizeBytesField key={p.key} label={p.label} value={v as number | undefined}
          onChange={change as (v: number) => void} constraints={p.constraints}
          required={p.required} description={p.description} errors={fieldErrors} />
      default:
        return <StringField key={p.key} label={p.label} value={v as string | undefined}
          onChange={change as (v: string) => void} constraints={p.constraints}
          required={p.required} description={p.description} errors={fieldErrors} />
    }
  }

  return (
    <div>
      {Object.entries(grouped).map(([group, params]) => (
        <div key={group} className="mb-6">
          <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3 border-b pb-1">{group}</h4>
          {params.sort((a, b) => a.display_order - b.display_order).map(renderField)}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: Run tests, commit**

```bash
git add frontend/src/components/ParameterForm/ frontend/tests/components/ParameterForm.test.tsx
git commit -m "feat(frontend): add dynamic ParameterForm with field components for all parameter types"
```

---

### Task 5: Order Pages — List + New + Detail Hub + Export

**Files:**
- Create: `frontend/src/components/orders/OrderItemCard.tsx`
- Create: `frontend/src/components/orders/OrderActions.tsx`
- Create: `frontend/src/components/orders/ValidationErrors.tsx`
- Modify: `frontend/src/pages/OrderList.tsx`
- Create: `frontend/src/pages/OrderNew.tsx`
- Create: `frontend/src/pages/OrderDetail.tsx`
- Create: `frontend/src/pages/OrderExport.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/tests/pages/OrderDetail.test.tsx`

- [ ] **Step 1: Write OrderDetail test**

```typescript
// frontend/tests/pages/OrderDetail.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import OrderDetail from '../../src/pages/OrderDetail'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/orders', () => ({
  ordersApi: {
    getOrder: vi.fn().mockResolvedValue({
      id: 'o1', order_number: 'ORD-2026-00001', status: 'draft',
      title: 'Test Order', business_reason: 'Testing', desired_date: null,
      requester_id: 'test', items: [
        { id: 'i1', template_slug: 'vm-linux', template_version: '1.0.0',
          display_name: 'Linux VM', parameters: { cpu_cores: 4 }, position: 1,
          validation_state: 'unchecked', validation_errors: [],
          created_at: '2026-01-01', updated_at: '2026-01-01' }
      ], context: null, submitted_at: null,
      created_at: '2026-01-01', updated_at: '2026-01-01',
    }),
    listOrders: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 }),
  },
}))

vi.mock('../../src/api/catalog', () => ({
  catalogApi: {
    listTemplates: vi.fn().mockResolvedValue({ data: [], total: 0, limit: 20, offset: 0 }),
    getTemplate: vi.fn().mockResolvedValue({ parameters: [] }),
    getCategories: vi.fn().mockResolvedValue({ categories: [] }),
  },
}))

function renderOrderDetail() {
  useAuthStore.getState().setAuth('tok', {
    username: 'test', display_name: 'Test', email: 'test@test.local', roles: ['requester'],
  })
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/orders/o1']}>
        <Routes>
          <Route path="/orders/:orderId" element={<OrderDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('OrderDetail', () => {
  beforeEach(() => { vi.clearAllMocks(); useAuthStore.getState().logout() })

  it('renders order title and number', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('ORD-2026-00001')).toBeInTheDocument()
      expect(screen.getByText('Test Order')).toBeInTheDocument()
    })
  })

  it('renders order items', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('Linux VM')).toBeInTheDocument()
    })
  })

  it('shows draft status', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('draft')).toBeInTheDocument()
    })
  })
})
```

- [ ] **Step 2: Implement all components and pages**

The OrderDetail page is the Hub — it shows the order header (number, title, status), context, items list, and action buttons. Items are displayed as OrderItemCards. "Add Service" opens a Drawer with template selection + ParameterForm. Validate and Submit buttons call the respective API hooks.

OrderList shows a table of orders with status badges and links to detail.
OrderNew creates a draft order and redirects to the detail page.
OrderExport shows the Tofu JSON readonly.

Update App.tsx to wire the new routes.

- [ ] **Step 3: Run tests, commit**

```bash
git add frontend/src/components/orders/ frontend/src/pages/ frontend/src/App.tsx frontend/tests/pages/OrderDetail.test.tsx
git commit -m "feat(frontend): add Order Hub pages (list, new, detail, export) with item management"
```

---

### Task 6: Final Verification

- [ ] **Step 1: Run all frontend tests**
- [ ] **Step 2: Type check** `npx tsc --noEmit`
- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore(frontend): phase F3+F4 complete — Order Hub with validation, submit, and export"
```
