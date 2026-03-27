// frontend/tests/pages/Subscriptions.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Subscriptions from '../../src/pages/Subscriptions'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/subscriptions', () => ({
  subscriptionsApi: {
    list: vi.fn().mockResolvedValue({
      items: [
        {
          id: 's1', order_item_id: 'i1', group_subscription_id: null,
          requester_id: 'test-requester', status: 'active',
          display_name: 'Linux VM', template_slug: 'vm-linux',
          template_version: '1.0.0', parameters: { cpu: 4 },
          pending_changes: null, monthly_cost_eur: 85,
          activated_at: '2026-01-15T10:00:00Z', cancelled_at: null,
          created_at: '2026-01-15T10:00:00Z', updated_at: '2026-01-15T10:00:00Z',
        },
      ],
      total: 1, limit: 50, offset: 0,
    }),
    listGroups: vi.fn().mockResolvedValue([]),
  },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Subscriptions />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Subscriptions', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'test-requester', display_name: 'Test', email: 't@t', roles: ['requester'] },
    })
  })

  it('renders heading', async () => {
    renderPage()
    expect(await screen.findByText('Subscriptions')).toBeInTheDocument()
  })

  it('renders subscription card', async () => {
    renderPage()
    expect(await screen.findByText('Linux VM')).toBeInTheDocument()
  })

  it('shows status badge', async () => {
    renderPage()
    expect(await screen.findByText('active')).toBeInTheDocument()
  })
})
