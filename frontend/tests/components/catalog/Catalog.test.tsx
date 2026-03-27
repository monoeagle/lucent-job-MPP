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

  it('opens detail drawer on card click', async () => {
    renderCatalog()
    await waitFor(() => screen.getByText('Linux VM'))
    await userEvent.click(screen.getByText('Linux VM'))
    await waitFor(() => {
      expect(screen.getByText('CPU-Kerne')).toBeInTheDocument()
    })
  })
})
