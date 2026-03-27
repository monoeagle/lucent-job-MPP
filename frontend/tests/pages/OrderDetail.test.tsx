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
