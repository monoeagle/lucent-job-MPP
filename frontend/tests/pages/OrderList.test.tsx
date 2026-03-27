import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import OrderList from '../../src/pages/OrderList'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/orders', () => ({
  ordersApi: {
    listOrders: vi.fn().mockResolvedValue({
      items: [
        { id: 'o1', order_number: 'ORD-001', status: 'draft', title: 'Web-Cluster',
          item_count: 2, created_at: '2026-01-15', updated_at: '2026-01-15', requester_id: 'test-user' },
      ],
      total: 1, limit: 20, offset: 0,
    }),
  },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <OrderList />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('OrderList', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'test', display_name: 'T', email: 't@t', roles: ['requester'] },
    })
  })

  it('renders status filter chips', async () => {
    renderPage()
    expect(await screen.findByText('Alle')).toBeInTheDocument()
    expect(screen.getByText('Entwurf')).toBeInTheDocument()
    expect(screen.getByText('Aktiv')).toBeInTheDocument()
  })

  it('renders order in table', async () => {
    renderPage()
    expect(await screen.findByText('ORD-001')).toBeInTheDocument()
    expect(screen.getByText('Web-Cluster')).toBeInTheDocument()
  })

  it('shows Zum Shop link', async () => {
    renderPage()
    expect(await screen.findByText('Zum Shop')).toBeInTheDocument()
  })
})
