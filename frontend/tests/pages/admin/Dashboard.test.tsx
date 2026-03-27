import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import AdminDashboard from '../../../src/pages/admin/Dashboard'
import { useAuthStore } from '../../../src/store/authStore'

vi.mock('../../../src/api/admin', () => ({
  adminApi: {
    getDashboard: vi.fn().mockResolvedValue({
      order_counts: { draft: 5, submitted: 3, approved: 2, done: 10 },
      pending_approvals: 3,
      active_resources: 7,
      system_health: { status: 'healthy', uptime: '14d 3h', version: '1.0.0' },
      recent_orders: [
        { id: 'o1', order_number: 'ORD-2026-00001', title: 'VM Order', status: 'draft', created_at: '2026-01-15T10:00:00Z' },
      ],
    }),
  },
}))

function renderAdminDashboard() {
  useAuthStore.getState().setAuth('tok', {
    username: 'admin', display_name: 'Admin', email: 'admin@test.local', roles: ['admin'],
  })
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AdminDashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Admin Dashboard', () => {
  beforeEach(() => { vi.clearAllMocks(); useAuthStore.getState().logout() })

  it('renders order counts', async () => {
    renderAdminDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('count-draft')).toHaveTextContent('5')
      expect(screen.getByTestId('count-submitted')).toHaveTextContent('3')
      expect(screen.getByTestId('count-done')).toHaveTextContent('10')
    })
  })

  it('shows system health', async () => {
    renderAdminDashboard()
    await waitFor(() => {
      expect(screen.getByText('healthy')).toBeInTheDocument()
      expect(screen.getByText(/14d 3h/)).toBeInTheDocument()
      expect(screen.getByText(/1.0.0/)).toBeInTheDocument()
    })
  })

  it('shows pending approvals and active resources counts', async () => {
    renderAdminDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('pending-approvals')).toHaveTextContent('3')
      expect(screen.getByTestId('active-resources')).toHaveTextContent('7')
    })
  })
})
