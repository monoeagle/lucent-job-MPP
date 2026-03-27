import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import AdminDashboard from '../../../src/pages/admin/Dashboard'
import { useAuthStore } from '../../../src/store/authStore'

vi.mock('../../../src/api/admin', () => ({
  adminApi: {
    getDashboard: vi.fn().mockResolvedValue({
      order_counts: { draft: 5, submitted: 3, approved: 2, done: 10, rejected: 1 },
      pending_approvals: 3,
      active_resources: 7,
      system_health: { database: 'ok', cmdb: 'ok' },
      recent_orders: [
        { order_id: 'o1', order_number: 'ORD-2026-00001', title: 'VM Order', status: 'draft', created_at: '2026-01-15T10:00:00Z' },
      ],
    }),
  },
}))

vi.mock('../../../src/hooks/useDashboard', () => ({
  useStats: () => ({ data: null }),
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

  it('renders order status cards with german labels', async () => {
    renderAdminDashboard()
    await waitFor(() => {
      expect(screen.getByText('Entwurf')).toBeInTheDocument()
    })
    expect(screen.getByText('Eingereicht')).toBeInTheDocument()
    expect(screen.getByText('Genehmigt')).toBeInTheDocument()
    expect(screen.getByText('Aktiv')).toBeInTheDocument()
    expect(screen.getByText('Abgelehnt')).toBeInTheDocument()
  })

  it('shows system health section', async () => {
    renderAdminDashboard()
    await waitFor(() => {
      expect(screen.getByText('Systemstatus')).toBeInTheDocument()
    })
    expect(screen.getByText(/Datenbank/)).toBeInTheDocument()
    expect(screen.getByText(/CMDB/)).toBeInTheDocument()
  })

  it('shows pending approvals and active resources', async () => {
    renderAdminDashboard()
    await waitFor(() => {
      expect(screen.getByText('Ausstehende Genehmigungen')).toBeInTheDocument()
      expect(screen.getByText('Aktive Ressourcen')).toBeInTheDocument()
      expect(screen.getByText('7')).toBeInTheDocument()
    })
  })

  it('shows recent orders table', async () => {
    renderAdminDashboard()
    await waitFor(() => {
      expect(screen.getByText('ORD-2026-00001')).toBeInTheDocument()
      expect(screen.getByText('VM Order')).toBeInTheDocument()
    })
  })
})
