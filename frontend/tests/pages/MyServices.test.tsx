import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import MyServices from '../../src/pages/MyServices'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/resources', () => ({
  resourcesApi: {
    listResources: vi.fn().mockResolvedValue({
      items: [
        { id: 'r1', order_id: 'o1', order_number: 'ORD-1', display_name: 'Linux VM Production',
          template_slug: 'vm-linux', parameters: { cpu: 4 }, status: 'active', created_at: '2026-01-15' },
      ],
    }),
  },
}))

vi.mock('../../src/api/subscriptions', () => ({
  subscriptionsApi: {
    list: vi.fn().mockResolvedValue({
      items: [
        { id: 's1', order_item_id: 'i1', group_subscription_id: null, requester_id: 'test-requester',
          status: 'active', display_name: 'DB Cluster', template_slug: 'db-postgres',
          template_version: '1.0.0', parameters: { storage: 100 }, pending_changes: null,
          monthly_cost_eur: 45, activated_at: '2026-01-15', cancelled_at: null,
          created_at: '2026-01-15', updated_at: '2026-01-15' },
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
        <MyServices />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('MyServices', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'test-requester', display_name: 'Test', email: 't@t', roles: ['requester'] },
    })
  })

  it('renders heading', async () => {
    renderPage()
    expect(await screen.findByText('My Services')).toBeInTheDocument()
  })

  it('shows tabs', async () => {
    renderPage()
    expect(await screen.findByText('Aktive Services')).toBeInTheDocument()
    expect(screen.getByText('Subscriptions')).toBeInTheDocument()
  })

  it('shows resource in active tab', async () => {
    renderPage()
    expect(await screen.findByText('Linux VM Production')).toBeInTheDocument()
  })
})
