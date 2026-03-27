# Phase F2: Service Catalog UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Service Catalog page showing template cards with filtering, search, pagination, and a detail drawer showing parameters and constraints.

**Architecture:** Catalog API module calls backend endpoints. tanstack-query for server state. Catalog page with filter bar + template card grid. Detail drawer shows full template with parameter definitions grouped by `group` field.

**Tech Stack:** React 19, TypeScript, TailwindCSS, @tanstack/react-query, react-router-dom

---

## File Structure

```
frontend/src/
├── types/
│   └── catalog.ts                  # ServiceTemplate, ParameterDefinition types
├── api/
│   └── catalog.ts                  # Catalog API calls
├── hooks/
│   └── useCatalog.ts               # tanstack-query hooks for catalog
├── components/
│   ├── Drawer.tsx                  # Reusable slide-in drawer (right)
│   └── catalog/
│       ├── TemplateCard.tsx        # Card component for catalog grid
│       ├── TemplateDetail.tsx      # Detail view inside drawer
│       ├── FilterBar.tsx           # Type, category, search filters
│       └── ParameterList.tsx       # Read-only parameter display grouped by group
└── pages/
    └── Catalog.tsx                 # Main catalog page (replaces placeholder)

frontend/tests/
├── api/
│   └── catalog.test.ts
├── hooks/
│   └── useCatalog.test.ts
└── components/
    └── catalog/
        └── Catalog.test.tsx
```

---

### Task 1: Catalog Types

**Files:**
- Create: `frontend/src/types/catalog.ts`

- [ ] **Step 1: Create types matching backend API**

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/catalog.ts
git commit -m "feat(frontend): add catalog TypeScript types"
```

---

### Task 2: Catalog API Module

**Files:**
- Create: `frontend/src/api/catalog.ts`
- Test: `frontend/tests/api/catalog.test.ts`

- [ ] **Step 1: Write test**

```typescript
// frontend/tests/api/catalog.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { catalogApi } from '../../src/api/catalog'
import { apiClient } from '../../src/api/client'

vi.mock('../../src/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('catalogApi', () => {
  beforeEach(() => vi.clearAllMocks())

  it('listTemplates calls correct URL with filters', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [], total: 0, limit: 20, offset: 0 })
    await catalogApi.listTemplates('my-token', { type: 'vm', q: 'linux' })
    expect(apiClient.get).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/catalog/templates?'),
      'my-token'
    )
    const url = vi.mocked(apiClient.get).mock.calls[0][0]
    expect(url).toContain('type=vm')
    expect(url).toContain('q=linux')
  })

  it('getTemplate calls correct URL', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ id: '1', slug: 'vm-linux' })
    await catalogApi.getTemplate('my-token', 'vm-linux')
    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/catalog/templates/vm-linux', 'my-token')
  })

  it('getTemplate with version', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ id: '1', slug: 'vm-linux' })
    await catalogApi.getTemplate('my-token', 'vm-linux', '2.0.0')
    expect(apiClient.get).toHaveBeenCalledWith(
      '/api/v1/catalog/templates/vm-linux?version=2.0.0', 'my-token'
    )
  })

  it('getCategories calls correct URL', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ categories: [] })
    await catalogApi.getCategories('my-token')
    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/catalog/categories', 'my-token')
  })
})
```

- [ ] **Step 2: Implement**

```typescript
// frontend/src/api/catalog.ts
import { apiClient } from './client'
import type { TemplateListResponse, ServiceTemplateDetail, CategoriesResponse, VersionsResponse } from '../types/catalog'

export interface CatalogFilters {
  status?: string
  type?: string
  category?: string
  q?: string
  limit?: number
  offset?: number
}

export const catalogApi = {
  async listTemplates(token: string, filters?: CatalogFilters): Promise<TemplateListResponse> {
    const params = new URLSearchParams()
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== '') params.set(key, String(value))
      })
    }
    const query = params.toString()
    const url = `/api/v1/catalog/templates${query ? `?${query}` : ''}`
    return (await apiClient.get(url, token)) as TemplateListResponse
  },

  async getTemplate(token: string, slug: string, version?: string): Promise<ServiceTemplateDetail> {
    const url = version
      ? `/api/v1/catalog/templates/${slug}?version=${version}`
      : `/api/v1/catalog/templates/${slug}`
    return (await apiClient.get(url, token)) as ServiceTemplateDetail
  },

  async getCategories(token: string): Promise<CategoriesResponse> {
    return (await apiClient.get('/api/v1/catalog/categories', token)) as CategoriesResponse
  },

  async getVersions(token: string, slug: string): Promise<VersionsResponse> {
    return (await apiClient.get(`/api/v1/catalog/templates/${slug}/versions`, token)) as VersionsResponse
  },
}
```

- [ ] **Step 3: Run tests, commit**

```bash
git add frontend/src/api/catalog.ts frontend/tests/api/catalog.test.ts
git commit -m "feat(frontend): add catalog API module"
```

---

### Task 3: Catalog Query Hooks

**Files:**
- Create: `frontend/src/hooks/useCatalog.ts`

- [ ] **Step 1: Implement hooks**

```typescript
// frontend/src/hooks/useCatalog.ts
import { useQuery } from '@tanstack/react-query'
import { catalogApi, type CatalogFilters } from '../api/catalog'
import { useAuthStore } from '../store/authStore'

export function useTemplates(filters?: CatalogFilters) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['templates', filters],
    queryFn: () => catalogApi.listTemplates(token!, filters),
    enabled: !!token,
  })
}

export function useTemplate(slug: string | null, version?: string) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['template', slug, version],
    queryFn: () => catalogApi.getTemplate(token!, slug!, version),
    enabled: !!token && !!slug,
  })
}

export function useCategories() {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['categories'],
    queryFn: () => catalogApi.getCategories(token!),
    enabled: !!token,
  })
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useCatalog.ts
git commit -m "feat(frontend): add catalog tanstack-query hooks"
```

---

### Task 4: Reusable Drawer Component

**Files:**
- Create: `frontend/src/components/Drawer.tsx`

- [ ] **Step 1: Implement**

```tsx
// frontend/src/components/Drawer.tsx
interface DrawerProps {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  width?: string
}

export default function Drawer({ open, onClose, title, children, width = 'w-[480px]' }: DrawerProps) {
  if (!open) return null

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />
      <div className={`fixed top-0 right-0 h-full ${width} bg-white shadow-xl z-50 flex flex-col`}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>
      </div>
    </>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Drawer.tsx
git commit -m "feat(frontend): add reusable Drawer slide-in component"
```

---

### Task 5: Catalog UI Components + Page

**Files:**
- Create: `frontend/src/components/catalog/FilterBar.tsx`
- Create: `frontend/src/components/catalog/TemplateCard.tsx`
- Create: `frontend/src/components/catalog/TemplateDetail.tsx`
- Create: `frontend/src/components/catalog/ParameterList.tsx`
- Modify: `frontend/src/pages/Catalog.tsx`
- Test: `frontend/tests/components/catalog/Catalog.test.tsx`

- [ ] **Step 1: Write integration test**

```typescript
// frontend/tests/components/catalog/Catalog.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Catalog from '../../../src/pages/Catalog'
import { useAuthStore } from '../../../src/store/authStore'

vi.mock('../../../src/api/catalog', () => ({
  catalogApi: {
    listTemplates: vi.fn().mockResolvedValue({
      data: [
        { id: '1', slug: 'vm-linux', version: '1.0.0', type: 'vm', display_name: 'Linux VM',
          description: 'A Linux VM', category: 'Compute', status: 'active', created_at: '2026-01-01',
          icon_identifier: null, deprecated_at: null, deprecated_by: null,
          estimated_cost_eur_per_month: 50, approval_always_required: false },
        { id: '2', slug: 'db-postgres', version: '1.0.0', type: 'database', display_name: 'PostgreSQL',
          description: 'PostgreSQL DB', category: 'Database', status: 'active', created_at: '2026-01-01',
          icon_identifier: null, deprecated_at: null, deprecated_by: null,
          estimated_cost_eur_per_month: 30, approval_always_required: false },
      ],
      total: 2, limit: 20, offset: 0,
    }),
    getCategories: vi.fn().mockResolvedValue({
      categories: [
        { name: 'Compute', template_count: 1 },
        { name: 'Database', template_count: 1 },
      ],
    }),
    getTemplate: vi.fn().mockResolvedValue({
      id: '1', slug: 'vm-linux', version: '1.0.0', type: 'vm', display_name: 'Linux VM',
      description: 'A Linux VM', category: 'Compute', status: 'active',
      tofu_module_source: 'git::https://gitlab.internal/tofu/vm.git',
      parameters: [
        { key: 'cpu_cores', label: 'CPU-Kerne', type: 'integer', required: true,
          tofu_variable_name: 'cpu_cores', display_order: 1, group: 'Compute',
          constraints: { min: 1, max: 64 }, depends_on: [], affects_options_of: [],
          description: null, default_value: 2 },
      ],
      cross_parameter_rules: [], metadata: {},
      created_at: '2026-01-01', deprecated_at: null, deprecated_by: null,
      icon_identifier: null, estimated_cost_eur_per_month: 50, approval_always_required: false,
    }),
  },
}))

function renderCatalog() {
  useAuthStore.getState().setAuth('test-token', {
    username: 'test', display_name: 'Test', email: 'test@test.local', roles: ['requester'],
  })
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Catalog />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Catalog page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().logout()
  })

  it('renders template cards', async () => {
    renderCatalog()
    await waitFor(() => {
      expect(screen.getByText('Linux VM')).toBeInTheDocument()
      expect(screen.getByText('PostgreSQL')).toBeInTheDocument()
    })
  })

  it('shows template count', async () => {
    renderCatalog()
    await waitFor(() => {
      expect(screen.getByText(/2 Services/i)).toBeInTheDocument()
    })
  })

  it('opens detail drawer on card click', async () => {
    renderCatalog()
    await waitFor(() => screen.getByText('Linux VM'))
    await userEvent.click(screen.getByText('Linux VM'))
    await waitFor(() => {
      expect(screen.getByText('CPU-Kerne')).toBeInTheDocument()
    })
  })
})
```

- [ ] **Step 2: Run test — verify FAIL**
- [ ] **Step 3: Implement components**

```tsx
// frontend/src/components/catalog/FilterBar.tsx
import { useState } from 'react'
import type { CategoryItem } from '../../types/catalog'

interface Props {
  categories: CategoryItem[]
  onFilterChange: (filters: { type?: string; category?: string; q?: string }) => void
}

export default function FilterBar({ categories, onFilterChange }: Props) {
  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [selectedType, setSelectedType] = useState('')

  function handleSearchChange(value: string) {
    setSearch(value)
    onFilterChange({ q: value, category: selectedCategory, type: selectedType })
  }

  function handleCategoryChange(value: string) {
    setSelectedCategory(value)
    onFilterChange({ q: search, category: value, type: selectedType })
  }

  function handleTypeChange(value: string) {
    setSelectedType(value)
    onFilterChange({ q: search, category: selectedCategory, type: value })
  }

  return (
    <div className="flex gap-4 mb-6 flex-wrap items-end">
      <div>
        <label className="block text-xs text-gray-500 mb-1">Suche</label>
        <input
          type="text"
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder="Service suchen..."
          className="px-3 py-2 border border-gray-300 rounded-md text-sm w-64"
        />
      </div>
      <div>
        <label className="block text-xs text-gray-500 mb-1">Kategorie</label>
        <select value={selectedCategory} onChange={(e) => handleCategoryChange(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm">
          <option value="">Alle</option>
          {categories.map((c) => (
            <option key={c.name} value={c.name}>{c.name} ({c.template_count})</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-xs text-gray-500 mb-1">Typ</label>
        <select value={selectedType} onChange={(e) => handleTypeChange(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm">
          <option value="">Alle</option>
          <option value="vm">VM</option>
          <option value="database">Database</option>
          <option value="container">Container</option>
          <option value="storage">Storage</option>
          <option value="network">Network</option>
        </select>
      </div>
    </div>
  )
}
```

```tsx
// frontend/src/components/catalog/TemplateCard.tsx
import type { ServiceTemplate } from '../../types/catalog'
import StatusBadge from '../StatusBadge'

interface Props {
  template: ServiceTemplate
  onClick: () => void
}

export default function TemplateCard({ template, onClick }: Props) {
  return (
    <div onClick={onClick}
         className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md hover:border-blue-300 cursor-pointer transition-all">
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-semibold text-gray-900">{template.display_name}</h3>
        <StatusBadge status={template.status} />
      </div>
      <p className="text-sm text-gray-500 mb-3 line-clamp-2">{template.description}</p>
      <div className="flex gap-2 text-xs text-gray-400">
        <span className="bg-gray-100 px-2 py-0.5 rounded">{template.type}</span>
        <span className="bg-gray-100 px-2 py-0.5 rounded">{template.category}</span>
        <span className="bg-gray-100 px-2 py-0.5 rounded">v{template.version}</span>
      </div>
      {template.estimated_cost_eur_per_month && (
        <p className="text-xs text-gray-400 mt-2">~{template.estimated_cost_eur_per_month} EUR/Monat</p>
      )}
    </div>
  )
}
```

```tsx
// frontend/src/components/catalog/ParameterList.tsx
import type { ParameterDefinition } from '../../types/catalog'

interface Props {
  parameters: ParameterDefinition[]
}

export default function ParameterList({ parameters }: Props) {
  const grouped = parameters.reduce<Record<string, ParameterDefinition[]>>((acc, p) => {
    const group = p.group || 'Allgemein'
    if (!acc[group]) acc[group] = []
    acc[group].push(p)
    return acc
  }, {})

  return (
    <div className="space-y-4">
      {Object.entries(grouped).map(([group, params]) => (
        <div key={group}>
          <h4 className="text-sm font-medium text-gray-500 mb-2">{group}</h4>
          <div className="space-y-2">
            {params.sort((a, b) => a.display_order - b.display_order).map((p) => (
              <div key={p.key} className="flex justify-between items-center py-1 px-3 bg-gray-50 rounded text-sm">
                <div>
                  <span className="font-medium">{p.label}</span>
                  {p.required && <span className="text-red-500 ml-1">*</span>}
                  {p.description && <p className="text-xs text-gray-400">{p.description}</p>}
                </div>
                <div className="text-gray-500 text-xs">
                  {p.type}
                  {p.constraints.min !== undefined && p.constraints.max !== undefined && (
                    <span> ({p.constraints.min}–{p.constraints.max}{p.constraints.unit ? ` ${p.constraints.unit}` : ''})</span>
                  )}
                  {p.constraints.options && (
                    <span> ({p.constraints.options.filter(o => o.enabled).length} Optionen)</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
```

```tsx
// frontend/src/components/catalog/TemplateDetail.tsx
import type { ServiceTemplateDetail } from '../../types/catalog'
import StatusBadge from '../StatusBadge'
import ParameterList from './ParameterList'

interface Props {
  template: ServiceTemplateDetail
}

export default function TemplateDetail({ template }: Props) {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <StatusBadge status={template.status} />
          <span className="text-xs text-gray-400">v{template.version}</span>
        </div>
        <p className="text-sm text-gray-600">{template.description}</p>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div><span className="text-gray-500">Typ:</span> {template.type}</div>
        <div><span className="text-gray-500">Kategorie:</span> {template.category}</div>
        <div><span className="text-gray-500">Slug:</span> <code className="text-xs bg-gray-100 px-1 rounded">{template.slug}</code></div>
        {template.estimated_cost_eur_per_month && (
          <div><span className="text-gray-500">Kosten:</span> ~{template.estimated_cost_eur_per_month} EUR/Monat</div>
        )}
      </div>

      {template.deprecated_by && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm">
          Dieses Template ist veraltet. Neuere Version: <strong>{template.deprecated_by.slug} v{template.deprecated_by.version}</strong>
        </div>
      )}

      <div>
        <h3 className="font-semibold mb-3">Parameter ({template.parameters.length})</h3>
        <ParameterList parameters={template.parameters} />
      </div>

      {template.cross_parameter_rules.length > 0 && (
        <div>
          <h3 className="font-semibold mb-2">Kombinationsregeln</h3>
          {template.cross_parameter_rules.map((r) => (
            <div key={r.rule_id} className="text-sm text-gray-600 bg-gray-50 rounded p-2 mb-1">
              {r.description}
            </div>
          ))}
        </div>
      )}

      <div className="text-xs text-gray-400">
        Tofu-Modul: <code>{template.tofu_module_source}</code>
      </div>
    </div>
  )
}
```

```tsx
// frontend/src/pages/Catalog.tsx
import { useState } from 'react'
import { useTemplates, useTemplate, useCategories } from '../hooks/useCatalog'
import type { CatalogFilters } from '../api/catalog'
import FilterBar from '../components/catalog/FilterBar'
import TemplateCard from '../components/catalog/TemplateCard'
import TemplateDetail from '../components/catalog/TemplateDetail'
import Drawer from '../components/Drawer'

export default function Catalog() {
  const [filters, setFilters] = useState<CatalogFilters>({})
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)

  const { data: templates, isLoading } = useTemplates(filters)
  const { data: categories } = useCategories()
  const { data: detail } = useTemplate(selectedSlug)

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Service Catalog</h1>
        {templates && (
          <span className="text-sm text-gray-500">{templates.total} Services</span>
        )}
      </div>

      <FilterBar
        categories={categories?.categories ?? []}
        onFilterChange={(f) => setFilters({ ...filters, ...f })}
      />

      {isLoading && <p className="text-gray-500">Laden...</p>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {templates?.data.map((t) => (
          <TemplateCard key={t.id} template={t} onClick={() => setSelectedSlug(t.slug)} />
        ))}
      </div>

      {templates?.data.length === 0 && !isLoading && (
        <p className="text-gray-500 text-center py-8">Keine Services gefunden.</p>
      )}

      <Drawer open={!!selectedSlug} onClose={() => setSelectedSlug(null)}
              title={detail?.display_name ?? 'Laden...'}>
        {detail && <TemplateDetail template={detail} />}
      </Drawer>
    </div>
  )
}
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL frontend tests**
- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/catalog/ frontend/src/components/Drawer.tsx frontend/src/pages/Catalog.tsx frontend/tests/
git commit -m "feat(frontend): add Service Catalog page with template cards, filters, and detail drawer"
```

---

### Task 6: Final Verification

- [ ] **Step 1: Run all frontend tests**

Run: `cd frontend && npx vitest run`

- [ ] **Step 2: Type check**

Run: `npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore(frontend): phase F2 complete — Service Catalog UI"
```
