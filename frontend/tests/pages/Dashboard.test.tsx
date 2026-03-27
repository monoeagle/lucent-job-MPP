import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Dashboard from '../../src/pages/Dashboard'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/dashboard', () => ({
  dashboardApi: {
    getStats: vi.fn().mockResolvedValue({
      orders_by_status: { draft: 3, submitted: 1, done: 7 },
      orders_by_month: [{ month: '2026-01', count: 5 }],
      total_templates: 12,
      active_resources: 7,
      pending_approvals: 2,
      popular_templates: [
        { slug: 'vm-linux', display_name: 'Linux VM', category: 'Compute', order_count: 15 },
      ],
    }),
    search: vi.fn().mockResolvedValue({ query: '', orders: [], templates: [], resources: [] }),
  },
}))

vi.mock('../../src/api/orders', () => ({
  ordersApi: {
    listOrders: vi.fn().mockResolvedValue({
      items: [
        { id: 'o1', order_number: 'ORD-2026-00001', status: 'draft', title: 'Test Order',
          item_count: 1, created_at: '2026-01-01', updated_at: '2026-01-01' },
      ],
      total: 1, limit: 5, offset: 0,
    }),
  },
}))

vi.mock('../../src/api/approvals', () => ({
  approvalsApi: {
    listPendingApprovals: vi.fn().mockResolvedValue({ items: [] }),
  },
}))

function renderDashboard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Dashboard', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'test-user', display_name: 'Test User', email: 'test@test.com', roles: ['requester'] },
    })
  })

  it('renders stat cards', async () => {
    renderDashboard()
    expect(await screen.findByText('Offene Orders')).toBeInTheDocument()
    expect(await screen.findByText('Templates')).toBeInTheDocument()
  })

  it('renders recent orders', async () => {
    renderDashboard()
    expect(await screen.findByText('Letzte Bestellungen')).toBeInTheDocument()
  })

  it('renders popular services', async () => {
    renderDashboard()
    expect(await screen.findByText('Beliebte Services')).toBeInTheDocument()
    expect(await screen.findByText('Linux VM')).toBeInTheDocument()
  })
})
