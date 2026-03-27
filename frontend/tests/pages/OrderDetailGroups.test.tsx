import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import OrderDetail from '../../src/pages/OrderDetail'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/orders', () => ({
  ordersApi: {
    getOrder: vi.fn().mockResolvedValue({
      id: 'o1',
      order_number: 'ORD-2026-00001',
      requester_id: 'test-requester',
      status: 'draft',
      title: 'Test Order',
      business_reason: null,
      desired_date: null,
      items: [
        {
          id: 'i1', template_slug: 'vm', template_version: '1.0.0',
          display_name: 'VM', parameters: { cpu: 4 }, position: 1,
          validation_state: 'unchecked', validation_errors: [],
          group_id: 'g1', quantity: 3, instance_parameters: [],
        },
        {
          id: 'i2', template_slug: 'db', template_version: '1.0.0',
          display_name: 'DB', parameters: { storage: 100 }, position: 2,
          validation_state: 'unchecked', validation_errors: [],
          group_id: null, quantity: 1, instance_parameters: [],
        },
      ],
      groups: [
        {
          id: 'g1', order_id: 'o1', name: 'Web-Cluster', description: null, position: 1,
          items: [
            {
              id: 'i1', template_slug: 'vm', template_version: '1.0.0',
              display_name: 'VM', parameters: { cpu: 4 }, position: 1,
              validation_state: 'unchecked', validation_errors: [],
              group_id: 'g1', quantity: 3, instance_parameters: [],
            },
          ],
        },
      ],
      ungrouped_items: [
        {
          id: 'i2', template_slug: 'db', template_version: '1.0.0',
          display_name: 'DB', parameters: { storage: 100 }, position: 2,
          validation_state: 'unchecked', validation_errors: [],
          group_id: null, quantity: 1, instance_parameters: [],
        },
      ],
      context: null,
      submitted_at: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    }),
    getStatus: vi.fn().mockResolvedValue({ status: 'draft' }),
    listOrders: vi.fn().mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 }),
  },
}))

vi.mock('../../src/api/catalog', () => ({
  catalogApi: {
    listTemplates: vi.fn().mockResolvedValue({ data: [], total: 0, limit: 20, offset: 0 }),
    getTemplate: vi.fn().mockResolvedValue(null),
  },
}))

function renderPage() {
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

describe('OrderDetail with Groups', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true,
      token: 'test-token',
      user: { username: 'test-requester', display_name: 'Test', email: 'test@test.com', roles: ['requester'] },
    })
  })

  it('renders group section with name', async () => {
    renderPage()
    expect(await screen.findByText('Web-Cluster')).toBeInTheDocument()
  })

  it('renders quantity badge on grouped item', async () => {
    renderPage()
    expect(await screen.findByText('×3')).toBeInTheDocument()
  })

  it('renders ungrouped items section', async () => {
    renderPage()
    expect(await screen.findByText('Ohne Gruppe')).toBeInTheDocument()
    expect(await screen.findByText('DB')).toBeInTheDocument()
  })

  it('shows Neue Gruppe button in draft', async () => {
    renderPage()
    expect(await screen.findByText('Neue Gruppe')).toBeInTheDocument()
  })
})
