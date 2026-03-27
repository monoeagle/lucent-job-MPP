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
    localStorage.clear()
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'u', display_name: 'U', email: 'u@u', roles: ['requester'] },
    })
  })

  it('defaults to wizard view', async () => {
    renderPage()
    expect(await screen.findByText('Weiter')).toBeInTheDocument()
  })
})
