# Shop-Wizard / Service Request Flow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two switchable views (Wizard + Form) for service configuration with context integration, quantity support, copy-shortcut for clusters, and template-controlled step ordering.

**Architecture:** New `ServiceRequest` page at `/shop/:slug/request` renders either `WizardView` or `FormView` based on user preference / template default. Both views share the same state (context, params, quantity) via props. Parameter groups become wizard steps (ordered by `wizard_config` or fallback). Existing `ParameterForm`, `ContextSelector`, and `QuantitySelector` are reused. No backend changes needed — `preferred_view` and `wizard_config` stored in template `metadata` JSONB.

**Tech Stack:** React 19, TypeScript, TailwindCSS 4, React Router v6, tanstack-query, zustand

**Spec:** `docs/superpowers/specs/2026-03-27-shop-wizard-design.md`

---

## File Structure (new/modified)

```
frontend/src/
├── pages/
│   └── ServiceRequest.tsx           # NEW: Main config page (both views)
├── components/orders/
│   ├── WizardView.tsx               # NEW: Step-by-step wizard container
│   ├── FormView.tsx                 # NEW: Scrollable form view
│   ├── StepIndicator.tsx            # NEW: Step progress bar for wizard
│   ├── RequestSummary.tsx           # NEW: Summary section (both views)
│   ├── OrderItemCard.tsx            # MODIFY: add "Aehnlichen Service" button
│   └── QuantitySelector.tsx         # EXISTS: reused as-is
├── components/ParameterForm/
│   └── ParameterForm.tsx            # EXISTS: reused as-is
├── components/orders/
│   └── ContextSelector.tsx          # EXISTS: reused as-is
├── components/catalog/
│   └── TemplateCard.tsx             # MODIFY: add "Bestellen" button
└── App.tsx                          # MODIFY: add routes

frontend/tests/
├── components/orders/
│   ├── StepIndicator.test.tsx       # NEW
│   ├── RequestSummary.test.tsx      # NEW
│   └── WizardView.test.tsx          # NEW
└── pages/
    └── ServiceRequest.test.tsx      # NEW
```

---

### Task 1: StepIndicator Component

**Files:**
- Create: `frontend/src/components/orders/StepIndicator.tsx`
- Create: `frontend/tests/components/orders/StepIndicator.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/tests/components/orders/StepIndicator.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import StepIndicator from '../../../src/components/orders/StepIndicator'

const steps = [
  { key: 'context', label: 'Kontext' },
  { key: 'network', label: 'Netzwerk' },
  { key: 'sizing', label: 'VM Sizing' },
  { key: 'summary', label: 'Zusammenfassung' },
]

describe('StepIndicator', () => {
  it('renders all step labels', () => {
    render(<StepIndicator steps={steps} currentStep={0} onStepClick={() => {}} />)
    expect(screen.getByText('Kontext')).toBeInTheDocument()
    expect(screen.getByText('Netzwerk')).toBeInTheDocument()
    expect(screen.getByText('VM Sizing')).toBeInTheDocument()
    expect(screen.getByText('Zusammenfassung')).toBeInTheDocument()
  })

  it('marks completed steps', () => {
    render(<StepIndicator steps={steps} currentStep={2} onStepClick={() => {}} />)
    const items = screen.getAllByTestId('step-item')
    expect(items[0]).toHaveAttribute('data-status', 'completed')
    expect(items[1]).toHaveAttribute('data-status', 'completed')
    expect(items[2]).toHaveAttribute('data-status', 'current')
    expect(items[3]).toHaveAttribute('data-status', 'pending')
  })

  it('calls onStepClick for completed steps', () => {
    const onClick = vi.fn()
    render(<StepIndicator steps={steps} currentStep={2} onStepClick={onClick} />)
    fireEvent.click(screen.getByText('Kontext'))
    expect(onClick).toHaveBeenCalledWith(0)
  })

  it('does not call onStepClick for pending steps', () => {
    const onClick = vi.fn()
    render(<StepIndicator steps={steps} currentStep={1} onStepClick={onClick} />)
    fireEvent.click(screen.getByText('Zusammenfassung'))
    expect(onClick).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `cd frontend && npx vitest run tests/components/orders/StepIndicator.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement**

```tsx
// frontend/src/components/orders/StepIndicator.tsx
export interface StepDef {
  key: string
  label: string
}

interface Props {
  steps: StepDef[]
  currentStep: number
  onStepClick: (index: number) => void
}

export default function StepIndicator({ steps, currentStep, onStepClick }: Props) {
  return (
    <div className="flex items-center gap-1 overflow-x-auto pb-2">
      {steps.map((step, i) => {
        const status = i < currentStep ? 'completed' : i === currentStep ? 'current' : 'pending'
        const clickable = status === 'completed'

        return (
          <div key={step.key} className="flex items-center">
            {i > 0 && <div className={`w-6 h-px mx-1 ${status === 'pending' ? 'bg-gray-300' : 'bg-blue-500'}`} />}
            <button
              data-testid="step-item"
              data-status={status}
              disabled={!clickable}
              onClick={() => clickable && onStepClick(i)}
              className={`px-3 py-1.5 rounded-full text-xs whitespace-nowrap transition-colors ${
                status === 'completed'
                  ? 'bg-blue-100 text-blue-700 hover:bg-blue-200 cursor-pointer'
                  : status === 'current'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-400 cursor-default'
              }`}
            >
              {status === 'completed' ? '✓ ' : ''}{step.label}
            </button>
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 4: Run test — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/orders/StepIndicator.tsx frontend/tests/components/orders/StepIndicator.test.tsx
git commit -m "feat(frontend): add StepIndicator component for wizard progress"
```

---

### Task 2: RequestSummary Component

**Files:**
- Create: `frontend/src/components/orders/RequestSummary.tsx`
- Create: `frontend/tests/components/orders/RequestSummary.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/tests/components/orders/RequestSummary.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import RequestSummary from '../../../src/components/orders/RequestSummary'

const template = {
  display_name: 'Linux VM',
  version: '1.0.0',
  estimated_cost_eur_per_month: 85,
}

const params = { cpu_cores: 8, ram_gb: 32, os_type: 'ubuntu-22.04' }

const parameterDefs = [
  { key: 'cpu_cores', label: 'CPU-Kerne', group: 'Compute' },
  { key: 'ram_gb', label: 'RAM', group: 'Compute' },
  { key: 'os_type', label: 'Betriebssystem', group: 'System' },
]

describe('RequestSummary', () => {
  it('renders template name and version', () => {
    render(
      <RequestSummary template={template} parameters={params}
        parameterDefs={parameterDefs} quantity={1} onQuantityChange={() => {}} />
    )
    expect(screen.getByText('Linux VM')).toBeInTheDocument()
    expect(screen.getByText('v1.0.0')).toBeInTheDocument()
  })

  it('renders parameter values', () => {
    render(
      <RequestSummary template={template} parameters={params}
        parameterDefs={parameterDefs} quantity={1} onQuantityChange={() => {}} />
    )
    expect(screen.getByText('CPU-Kerne')).toBeInTheDocument()
    expect(screen.getByText('8')).toBeInTheDocument()
  })

  it('shows cost estimate for quantity', () => {
    render(
      <RequestSummary template={template} parameters={params}
        parameterDefs={parameterDefs} quantity={3} onQuantityChange={() => {}} />
    )
    expect(screen.getByText(/255/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `cd frontend && npx vitest run tests/components/orders/RequestSummary.test.tsx`

- [ ] **Step 3: Implement**

```tsx
// frontend/src/components/orders/RequestSummary.tsx
import QuantitySelector from './QuantitySelector'

interface Props {
  template: { display_name: string; version: string; estimated_cost_eur_per_month?: number | null }
  parameters: Record<string, unknown>
  parameterDefs: Array<{ key: string; label: string; group?: string | null }>
  quantity: number
  onQuantityChange: (q: number) => void
}

export default function RequestSummary({ template, parameters, parameterDefs, quantity, onQuantityChange }: Props) {
  const totalCost = template.estimated_cost_eur_per_month
    ? template.estimated_cost_eur_per_month * quantity
    : null

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h3 className="text-lg font-semibold">{template.display_name}</h3>
        <span className="text-sm text-gray-400">v{template.version}</span>
      </div>

      <div className="bg-gray-50 rounded-lg p-4 space-y-2">
        {parameterDefs
          .filter((p) => parameters[p.key] !== undefined && parameters[p.key] !== '')
          .map((p) => (
            <div key={p.key} className="flex justify-between text-sm">
              <span className="text-gray-600">{p.label}</span>
              <span className="font-medium">{String(parameters[p.key])}</span>
            </div>
          ))}
      </div>

      <QuantitySelector value={quantity} onChange={onQuantityChange} />

      {totalCost !== null && (
        <p className="text-sm text-gray-500">
          Geschaetzte Kosten: <span className="font-semibold">{totalCost} EUR/Monat</span>
          {quantity > 1 && ` (${quantity} × ${template.estimated_cost_eur_per_month} EUR)`}
        </p>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run test — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/orders/RequestSummary.tsx frontend/tests/components/orders/RequestSummary.test.tsx
git commit -m "feat(frontend): add RequestSummary component with quantity and cost"
```

---

### Task 3: WizardView Component

**Files:**
- Create: `frontend/src/components/orders/WizardView.tsx`
- Create: `frontend/tests/components/orders/WizardView.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/tests/components/orders/WizardView.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import WizardView from '../../../src/components/orders/WizardView'
import { useAuthStore } from '../../../src/store/authStore'
import type { ServiceTemplateDetail } from '../../../src/types/catalog'

vi.mock('../../../src/api/context', () => ({
  contextApi: {
    getLocations: vi.fn().mockResolvedValue([]),
    getTenants: vi.fn().mockResolvedValue([]),
    getSecurityZones: vi.fn().mockResolvedValue([]),
    getNetworks: vi.fn().mockResolvedValue([]),
  },
}))

const template: ServiceTemplateDetail = {
  id: 't1', slug: 'vm-linux', version: '1.0.0', type: 'vm',
  display_name: 'Linux VM', description: null, category: 'Compute',
  icon_identifier: null, status: 'active', created_at: '', deprecated_at: null,
  deprecated_by: null, estimated_cost_eur_per_month: 85,
  approval_always_required: false, tofu_module_source: 'git::test',
  cross_parameter_rules: [],
  metadata: {},
  parameters: [
    { key: 'cpu', label: 'CPU', description: null, type: 'integer', required: true,
      default_value: null, tofu_variable_name: 'cpu', display_order: 1,
      group: 'Compute', constraints: { min: 1, max: 64 }, depends_on: [], affects_options_of: [] },
    { key: 'os', label: 'OS', description: null, type: 'enum', required: true,
      default_value: null, tofu_variable_name: 'os', display_order: 1,
      group: 'System', constraints: { options: [{ value: 'ubuntu', label: 'Ubuntu', enabled: true }] },
      depends_on: [], affects_options_of: [] },
  ],
}

function renderWizard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <WizardView
          template={template}
          values={{}}
          context={null}
          quantity={1}
          onValuesChange={() => {}}
          onContextChange={() => {}}
          onQuantityChange={() => {}}
          onSubmit={() => {}}
        />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('WizardView', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test',
      user: { username: 'u', display_name: 'U', email: 'u@u', roles: ['requester'] },
    })
  })

  it('starts on Context step', () => {
    renderWizard()
    expect(screen.getByText('Kontext')).toBeInTheDocument()
  })

  it('shows step indicator with all steps', () => {
    renderWizard()
    expect(screen.getByText('Compute')).toBeInTheDocument()
    expect(screen.getByText('System')).toBeInTheDocument()
    expect(screen.getByText('Zusammenfassung')).toBeInTheDocument()
  })

  it('has Weiter button', () => {
    renderWizard()
    expect(screen.getByText('Weiter')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `cd frontend && npx vitest run tests/components/orders/WizardView.test.tsx`

- [ ] **Step 3: Implement**

```tsx
// frontend/src/components/orders/WizardView.tsx
import { useState } from 'react'
import type { ServiceTemplateDetail, ParameterDefinition } from '../../types/catalog'
import type { OrderContext } from '../../types/context'
import StepIndicator, { type StepDef } from './StepIndicator'
import ContextSelector from './ContextSelector'
import ParameterForm from '../ParameterForm/ParameterForm'
import RequestSummary from './RequestSummary'

interface WizardStep extends StepDef {
  type: 'context' | 'params' | 'summary'
  params?: ParameterDefinition[]
}

interface Props {
  template: ServiceTemplateDetail
  values: Record<string, unknown>
  context: OrderContext | null
  quantity: number
  onValuesChange: (key: string, value: unknown) => void
  onContextChange: (ctx: OrderContext) => void
  onQuantityChange: (q: number) => void
  onSubmit: () => void
  isSubmitting?: boolean
}

function buildSteps(template: ServiceTemplateDetail): WizardStep[] {
  const steps: WizardStep[] = [
    { key: 'context', label: 'Kontext', type: 'context' },
  ]

  // Check for wizard_config in metadata
  const wizardConfig = template.metadata?.wizard_config as
    { steps?: Array<{ group: string; label: string }> } | undefined

  if (wizardConfig?.steps) {
    for (const stepDef of wizardConfig.steps) {
      const params = template.parameters.filter((p) => p.group === stepDef.group)
      if (params.length > 0) {
        steps.push({ key: stepDef.group, label: stepDef.label, type: 'params', params })
      }
    }
    // Add any params not covered by wizard_config
    const coveredGroups = new Set(wizardConfig.steps.map((s) => s.group))
    const uncovered = template.parameters.filter((p) => !coveredGroups.has(p.group ?? ''))
    if (uncovered.length > 0) {
      const groups = [...new Set(uncovered.map((p) => p.group ?? 'Allgemein'))]
      for (const g of groups) {
        steps.push({ key: g, label: g, type: 'params', params: uncovered.filter((p) => (p.group ?? 'Allgemein') === g) })
      }
    }
  } else {
    // Fallback: group by parameter group, sorted by min display_order
    const groups = new Map<string, ParameterDefinition[]>()
    for (const p of template.parameters) {
      const g = p.group ?? 'Allgemein'
      if (!groups.has(g)) groups.set(g, [])
      groups.get(g)!.push(p)
    }
    const sorted = [...groups.entries()].sort(
      (a, b) => Math.min(...a[1].map((p) => p.display_order)) - Math.min(...b[1].map((p) => p.display_order))
    )
    for (const [g, params] of sorted) {
      steps.push({ key: g, label: g, type: 'params', params })
    }
  }

  steps.push({ key: 'summary', label: 'Zusammenfassung', type: 'summary' })
  return steps
}

export default function WizardView({
  template, values, context, quantity,
  onValuesChange, onContextChange, onQuantityChange, onSubmit, isSubmitting,
}: Props) {
  const [currentStep, setCurrentStep] = useState(0)
  const steps = buildSteps(template)
  const step = steps[currentStep]

  const canNext = currentStep < steps.length - 1
  const canBack = currentStep > 0

  return (
    <div>
      <StepIndicator
        steps={steps}
        currentStep={currentStep}
        onStepClick={(i) => setCurrentStep(i)}
      />

      <div className="mt-6 min-h-[300px]">
        {step.type === 'context' && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Kontext</h3>
            <ContextSelector value={context} onChange={onContextChange} />
          </div>
        )}

        {step.type === 'params' && step.params && (
          <div>
            <h3 className="text-lg font-semibold mb-4">{step.label}</h3>
            <ParameterForm
              parameters={step.params}
              values={values}
              onChange={onValuesChange}
            />
          </div>
        )}

        {step.type === 'summary' && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Zusammenfassung</h3>
            <RequestSummary
              template={template}
              parameters={values}
              parameterDefs={template.parameters}
              quantity={quantity}
              onQuantityChange={onQuantityChange}
            />
          </div>
        )}
      </div>

      <div className="flex justify-between mt-6 pt-4 border-t">
        {canBack ? (
          <button onClick={() => setCurrentStep(currentStep - 1)}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
            ← Zurück
          </button>
        ) : <div />}

        {canNext ? (
          <button onClick={() => setCurrentStep(currentStep + 1)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700">
            Weiter
          </button>
        ) : (
          <button onClick={onSubmit} disabled={isSubmitting}
            className="px-4 py-2 bg-green-600 text-white rounded-md text-sm hover:bg-green-700 disabled:opacity-50">
            {isSubmitting ? 'Wird erstellt...' : 'Zur Bestellung hinzufügen'}
          </button>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run test — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/orders/WizardView.tsx frontend/tests/components/orders/WizardView.test.tsx
git commit -m "feat(frontend): add WizardView with step navigation and wizard_config support"
```

---

### Task 4: FormView Component

**Files:**
- Create: `frontend/src/components/orders/FormView.tsx`

- [ ] **Step 1: Implement FormView**

```tsx
// frontend/src/components/orders/FormView.tsx
import type { ServiceTemplateDetail, ParameterDefinition } from '../../types/catalog'
import type { OrderContext } from '../../types/context'
import ContextSelector from './ContextSelector'
import ParameterForm from '../ParameterForm/ParameterForm'
import RequestSummary from './RequestSummary'

interface Props {
  template: ServiceTemplateDetail
  values: Record<string, unknown>
  context: OrderContext | null
  quantity: number
  onValuesChange: (key: string, value: unknown) => void
  onContextChange: (ctx: OrderContext) => void
  onQuantityChange: (q: number) => void
  onSubmit: () => void
  isSubmitting?: boolean
}

function getSectionOrder(template: ServiceTemplateDetail): Array<{ label: string; params: ParameterDefinition[] }> {
  const wizardConfig = template.metadata?.wizard_config as
    { steps?: Array<{ group: string; label: string }> } | undefined

  if (wizardConfig?.steps) {
    const sections: Array<{ label: string; params: ParameterDefinition[] }> = []
    const coveredGroups = new Set<string>()
    for (const stepDef of wizardConfig.steps) {
      const params = template.parameters.filter((p) => p.group === stepDef.group)
      if (params.length > 0) {
        sections.push({ label: stepDef.label, params })
        coveredGroups.add(stepDef.group)
      }
    }
    const uncovered = template.parameters.filter((p) => !coveredGroups.has(p.group ?? ''))
    if (uncovered.length > 0) {
      sections.push({ label: 'Weitere Parameter', params: uncovered })
    }
    return sections
  }

  // Fallback: group by param group
  const groups = new Map<string, ParameterDefinition[]>()
  for (const p of template.parameters) {
    const g = p.group ?? 'Allgemein'
    if (!groups.has(g)) groups.set(g, [])
    groups.get(g)!.push(p)
  }
  return [...groups.entries()]
    .sort((a, b) => Math.min(...a[1].map((p) => p.display_order)) - Math.min(...b[1].map((p) => p.display_order)))
    .map(([label, params]) => ({ label, params }))
}

export default function FormView({
  template, values, context, quantity,
  onValuesChange, onContextChange, onQuantityChange, onSubmit, isSubmitting,
}: Props) {
  const sections = getSectionOrder(template)

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-semibold mb-4 border-b pb-2">Kontext</h3>
        <ContextSelector value={context} onChange={onContextChange} />
      </div>

      {sections.map((section) => (
        <div key={section.label}>
          <h3 className="text-lg font-semibold mb-4 border-b pb-2">{section.label}</h3>
          <ParameterForm
            parameters={section.params}
            values={values}
            onChange={onValuesChange}
          />
        </div>
      ))}

      <div>
        <h3 className="text-lg font-semibold mb-4 border-b pb-2">Zusammenfassung</h3>
        <RequestSummary
          template={template}
          parameters={values}
          parameterDefs={template.parameters}
          quantity={quantity}
          onQuantityChange={onQuantityChange}
        />
        <button onClick={onSubmit} disabled={isSubmitting}
          className="mt-4 w-full px-4 py-2 bg-green-600 text-white rounded-md text-sm hover:bg-green-700 disabled:opacity-50">
          {isSubmitting ? 'Wird erstellt...' : 'Zur Bestellung hinzufügen'}
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/orders/FormView.tsx
git commit -m "feat(frontend): add FormView with scrollable sections and wizard_config ordering"
```

---

### Task 5: ServiceRequest Page

**Files:**
- Create: `frontend/src/pages/ServiceRequest.tsx`
- Create: `frontend/tests/pages/ServiceRequest.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/tests/pages/ServiceRequest.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import ServiceRequest from '../../src/pages/ServiceRequest'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/catalog', () => ({
  catalogApi: {
    getTemplate: vi.fn().mockResolvedValue({
      id: 't1', slug: 'vm-linux', version: '1.0.0', type: 'vm',
      display_name: 'Linux VM', description: null, category: 'Compute',
      icon_identifier: null, status: 'active', created_at: '',
      deprecated_at: null, deprecated_by: null,
      estimated_cost_eur_per_month: 85, approval_always_required: false,
      tofu_module_source: 'git::test', cross_parameter_rules: [],
      metadata: {},
      parameters: [
        { key: 'cpu', label: 'CPU', description: null, type: 'integer',
          required: true, default_value: null, tofu_variable_name: 'cpu',
          display_order: 1, group: 'Compute',
          constraints: { min: 1, max: 64 }, depends_on: [], affects_options_of: [] },
      ],
    }),
    listTemplates: vi.fn().mockResolvedValue({ data: [], total: 0, limit: 20, offset: 0 }),
  },
}))

vi.mock('../../src/api/context', () => ({
  contextApi: {
    getLocations: vi.fn().mockResolvedValue([]),
    getTenants: vi.fn().mockResolvedValue([]),
    getSecurityZones: vi.fn().mockResolvedValue([]),
    getNetworks: vi.fn().mockResolvedValue([]),
  },
}))

vi.mock('../../src/api/orders', () => ({
  ordersApi: {
    createOrder: vi.fn().mockResolvedValue({ id: 'o1', order_number: 'ORD-1', status: 'draft', title: 'T', items: [], groups: [], ungrouped_items: [] }),
    addItem: vi.fn().mockResolvedValue({ item: { id: 'i1' } }),
    listOrders: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 }),
  },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/shop/vm-linux/request']}>
        <Routes>
          <Route path="/shop/:slug/request" element={<ServiceRequest />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ServiceRequest', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'u', display_name: 'U', email: 'u@u', roles: ['requester'] },
    })
  })

  it('renders template name', async () => {
    renderPage()
    expect(await screen.findByText('Linux VM bestellen')).toBeInTheDocument()
  })

  it('shows view toggle button', async () => {
    renderPage()
    expect(await screen.findByTestId('view-toggle')).toBeInTheDocument()
  })

  it('defaults to wizard view', async () => {
    renderPage()
    expect(await screen.findByText('Kontext')).toBeInTheDocument()
    expect(await screen.findByText('Weiter')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `cd frontend && npx vitest run tests/pages/ServiceRequest.test.tsx`

- [ ] **Step 3: Implement**

```tsx
// frontend/src/pages/ServiceRequest.tsx
import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useTemplate } from '../hooks/useCatalog'
import { useCreateOrder, useAddItem } from '../hooks/useOrders'
import { useAuthStore } from '../store/authStore'
import type { OrderContext } from '../types/context'
import WizardView from '../components/orders/WizardView'
import FormView from '../components/orders/FormView'

type ViewMode = 'wizard' | 'form'

function getStoredView(slug: string): ViewMode | null {
  const stored = localStorage.getItem(`mpp-view-${slug}`)
  if (stored === 'wizard' || stored === 'form') return stored
  return null
}

function getDefaultView(metadata: Record<string, unknown> | undefined): ViewMode {
  const wc = metadata?.wizard_config as { preferred_view?: string } | undefined
  if (wc?.preferred_view === 'form') return 'form'
  const pv = metadata?.preferred_view
  if (pv === 'form') return 'form'
  return 'wizard'
}

export default function ServiceRequest() {
  const { slug } = useParams<{ slug: string }>()
  const [searchParams] = useSearchParams()
  const orderId = searchParams.get('orderId')
  const navigate = useNavigate()
  const { data: template, isLoading } = useTemplate(slug ?? null)

  const createOrder = useCreateOrder()
  const token = useAuthStore((s) => s.token)

  const [view, setView] = useState<ViewMode>('wizard')
  const [values, setValues] = useState<Record<string, unknown>>({})
  const [context, setContext] = useState<OrderContext | null>(null)
  const [quantity, setQuantity] = useState(1)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (template) {
      const stored = getStoredView(template.slug)
      setView(stored ?? getDefaultView(template.metadata))
    }
  }, [template])

  const toggleView = () => {
    const next = view === 'wizard' ? 'form' : 'wizard'
    setView(next)
    if (slug) localStorage.setItem(`mpp-view-${slug}`, next)
  }

  const handleSubmit = async () => {
    if (!template || !context || !token) return
    setSubmitting(true)
    try {
      let targetOrderId = orderId
      if (!targetOrderId) {
        const order = await createOrder.mutateAsync({
          title: `${template.display_name} Bestellung`,
          context,
        })
        targetOrderId = order.id
      }

      const { ordersApi } = await import('../api/orders')
      await ordersApi.addItem(token, targetOrderId, {
        template_slug: template.slug,
        template_version: template.version,
        parameters: values,
        quantity: quantity > 1 ? quantity : undefined,
      })

      navigate(`/orders/${targetOrderId}`)
    } finally {
      setSubmitting(false)
    }
  }

  if (isLoading) return <p className="text-gray-500">Lade Template...</p>
  if (!template) return <p className="text-red-500">Template nicht gefunden.</p>

  const viewProps = {
    template,
    values,
    context,
    quantity,
    onValuesChange: (key: string, val: unknown) => setValues((prev) => ({ ...prev, [key]: val })),
    onContextChange: setContext,
    onQuantityChange: setQuantity,
    onSubmit: handleSubmit,
    isSubmitting: submitting,
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{template.display_name} bestellen</h1>
        <button
          data-testid="view-toggle"
          onClick={toggleView}
          className="px-3 py-1.5 border border-gray-300 rounded-md text-sm text-gray-600 hover:bg-gray-50"
        >
          {view === 'wizard' ? '≡ Formular-Ansicht' : '☰ Wizard-Ansicht'}
        </button>
      </div>

      {view === 'wizard' ? <WizardView {...viewProps} /> : <FormView {...viewProps} />}
    </div>
  )
}
```

- [ ] **Step 4: Run test — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ServiceRequest.tsx frontend/tests/pages/ServiceRequest.test.tsx
git commit -m "feat(frontend): add ServiceRequest page with wizard/form toggle and template-first flow"
```

---

### Task 6: Routes + Catalog "Bestellen" Button

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/catalog/TemplateCard.tsx`
- Modify: `frontend/src/pages/Catalog.tsx`

- [ ] **Step 1: Add route in App.tsx**

Add import and route:
```tsx
import ServiceRequest from './pages/ServiceRequest'
```

Add inside the protected route block, after the `/orders/:orderId/export` route:
```tsx
<Route path="/shop/:slug/request" element={<ServiceRequest />} />
```

- [ ] **Step 2: Add "Bestellen" button to TemplateCard**

In `frontend/src/components/catalog/TemplateCard.tsx`, add a `useNavigate` import and an `onOrder` prop:

```tsx
import { useNavigate } from 'react-router-dom'
import type { ServiceTemplate } from '../../types/catalog'
import StatusBadge from '../StatusBadge'

interface Props {
  template: ServiceTemplate
  onClick: () => void
}

export default function TemplateCard({ template, onClick }: Props) {
  const navigate = useNavigate()

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md hover:border-blue-300 transition-all">
      <div onClick={onClick} className="cursor-pointer">
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
      {template.status === 'active' && (
        <button
          onClick={(e) => { e.stopPropagation(); navigate(`/shop/${template.slug}/request`) }}
          className="mt-3 w-full px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
        >
          Bestellen
        </button>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/catalog/TemplateCard.tsx
git commit -m "feat(frontend): add /shop/:slug/request route and Bestellen button on TemplateCard"
```

---

### Task 7: Copy-Shortcut on OrderItemCard

**Files:**
- Modify: `frontend/src/components/orders/OrderItemCard.tsx`
- Modify: `frontend/src/pages/OrderDetail.tsx`

- [ ] **Step 1: Add "Aehnlichen Service" button to OrderItemCard**

Add `onCopy` prop to OrderItemCard:

```tsx
import type { OrderItem } from '../../types/order'
import StatusBadge from '../StatusBadge'
import ValidationErrors from './ValidationErrors'

interface Props {
  item: OrderItem
  onEdit?: () => void
  onRemove?: () => void
  onCopy?: () => void
  readonly?: boolean
}

export default function OrderItemCard({ item, onEdit, onRemove, onCopy, readonly }: Props) {
  const paramSummary = Object.entries(item.parameters)
    .slice(0, 4)
    .map(([k, v]) => `${k}: ${String(v)}`)
    .join(', ')

  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-white">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{item.display_name}</span>
          <span className="text-xs text-gray-400">v{item.template_version}</span>
          <StatusBadge status={item.validation_state} />
          {item.quantity > 1 && (
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
              ×{item.quantity}
            </span>
          )}
        </div>
        {!readonly && (
          <div className="flex gap-2">
            {onCopy && (
              <button onClick={onCopy} className="text-xs text-blue-600 hover:text-blue-800">
                Ähnlichen hinzufügen
              </button>
            )}
            {onEdit && (
              <button onClick={onEdit} className="text-xs text-blue-600 hover:text-blue-800">
                Bearbeiten
              </button>
            )}
            {onRemove && (
              <button onClick={onRemove} className="text-xs text-red-600 hover:text-red-800">
                Entfernen
              </button>
            )}
          </div>
        )}
      </div>
      {paramSummary && (
        <p className="text-xs text-gray-500 truncate">{paramSummary}</p>
      )}
      {item.validation_state === 'invalid' && (
        <ValidationErrors errors={item.validation_errors} />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Wire copy in OrderDetail**

In `frontend/src/pages/OrderDetail.tsx`, add a `handleCopyItem` function that navigates to the ServiceRequest page with pre-filled params via URL:

Add this function inside OrderDetail component:
```tsx
  const handleCopyItem = (item: OrderItem) => {
    // Navigate to request page with orderId to add to same order
    // Pre-fill will be handled via query params or state
    navigate(`/shop/${item.template_slug}/request?orderId=${orderId}`)
  }
```

Import `OrderItem` type at the top:
```tsx
import type { OrderItem } from '../types/order'
```

Pass `onCopy` to all `OrderItemCard` instances in draft mode:
```tsx
onCopy={isDraft ? () => handleCopyItem(item) : undefined}
```

This applies to both grouped items (in GroupSection) and ungrouped items.

For GroupSection, pass the callback through. Update the GroupSection call:
```tsx
<GroupSection
  key={group.id}
  group={group}
  isDraft={isDraft}
  onDeleteGroup={() => deleteGroup.mutate(group.id)}
  onRemoveItem={(itemId) => removeItem.mutate(itemId)}
  onCopyItem={(item) => handleCopyItem(item)}
/>
```

Update `frontend/src/components/orders/GroupSection.tsx` to accept and pass through `onCopyItem`:

Add to Props interface:
```tsx
  onCopyItem?: (item: OrderItem) => void
```

Pass to OrderItemCard:
```tsx
onCopy={isDraft && onCopyItem ? () => onCopyItem(item) : undefined}
```

- [ ] **Step 3: Run all frontend tests**

Run: `cd frontend && npx vitest run`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/orders/OrderItemCard.tsx frontend/src/components/orders/GroupSection.tsx frontend/src/pages/OrderDetail.tsx
git commit -m "feat(frontend): add copy-shortcut — 'Aehnlichen Service hinzufuegen' on OrderItemCard"
```

---

### Task 8: Final Verification

- [ ] **Step 1: Run full frontend test suite**

Run: `cd frontend && npx vitest run`

- [ ] **Step 2: Type check**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Run backend tests (sanity check)**

Run: `source venv/bin/activate && DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_test pytest tests/ -q`

- [ ] **Step 4: Final commit**

```bash
git commit -m "chore: phase 9 complete — shop wizard with wizard/form toggle, template-first flow, copy shortcut"
```
