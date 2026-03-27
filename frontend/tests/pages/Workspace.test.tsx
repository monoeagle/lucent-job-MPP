import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Workspace from '../../src/pages/Workspace'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/orders', () => ({
  ordersApi: {
    listOrders: vi.fn().mockResolvedValue({
      items: [
        { id: 'o1', order_number: 'ORD-001', status: 'draft', title: 'Test',
          item_count: 1, created_at: '2026-01-01', updated_at: '2026-01-01' },
      ],
      total: 1, limit: 20, offset: 0,
    }),
  },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/workspace']}>
        <Workspace />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Workspace', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'test', display_name: 'T', email: 't@t', roles: ['requester'] },
    })
  })

  it('renders tab buttons', async () => {
    renderPage()
    expect(await screen.findByText('Alle Bestellungen')).toBeInTheDocument()
    expect(screen.getByText('Meine Bestellungen')).toBeInTheDocument()
  })

  it('shows orders in list', async () => {
    renderPage()
    expect(await screen.findByText('ORD-001')).toBeInTheDocument()
  })
})
