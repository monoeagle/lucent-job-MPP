import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import SubscriptionDetail from '../../src/pages/SubscriptionDetail'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/subscriptions', () => ({
  subscriptionsApi: {
    get: vi.fn().mockResolvedValue({
      id: 's1', order_item_id: 'i1', group_subscription_id: null,
      requester_id: 'test-requester', status: 'active',
      display_name: 'Linux VM', template_slug: 'vm-linux',
      template_version: '1.0.0', parameters: { cpu: 4, ram: 16 },
      pending_changes: null, monthly_cost_eur: 85,
      activated_at: '2026-01-15T10:00:00Z', cancelled_at: null,
      created_at: '2026-01-10T10:00:00Z', updated_at: '2026-01-15T10:00:00Z',
    }),
    requestChange: vi.fn().mockResolvedValue({}),
    requestCancel: vi.fn().mockResolvedValue({}),
  },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/subscriptions/s1']}>
        <Routes>
          <Route path="/subscriptions/:id" element={<SubscriptionDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('SubscriptionDetail', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'test-requester', display_name: 'Test', email: 't@t', roles: ['requester'] },
    })
  })

  it('renders subscription name', async () => {
    renderPage()
    expect(await screen.findByText('Linux VM')).toBeInTheDocument()
  })

  it('renders parameters', async () => {
    renderPage()
    expect(await screen.findByText('cpu')).toBeInTheDocument()
    expect(await screen.findByText('4')).toBeInTheDocument()
  })

  it('shows action buttons for active subscription', async () => {
    renderPage()
    expect(await screen.findByText('Aendern')).toBeInTheDocument()
    expect(await screen.findByText('Kuendigen')).toBeInTheDocument()
  })
})
