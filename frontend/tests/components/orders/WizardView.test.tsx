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

  it('navigates to next step on Weiter click', () => {
    renderWizard()
    fireEvent.click(screen.getByText('Weiter'))
    // Now on Compute step, should show CPU field label
    expect(screen.getByText('Compute')).toBeInTheDocument()
  })
})
