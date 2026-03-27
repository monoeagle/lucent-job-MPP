import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import MyRequests from '../../src/pages/MyRequests'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/orders', () => ({
  ordersApi: {
    listOrders: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'o1',
          order_number: 'ORD-2026-00001',
          status: 'submitted',
          title: 'Mein erster Server',
          item_count: 2,
          created_at: '2026-01-10T08:00:00Z',
          updated_at: '2026-01-10T09:00:00Z',
        },
        {
          id: 'o2',
          order_number: 'ORD-2026-00002',
          status: 'done',
          title: 'Datenbank Prod',
          item_count: 1,
          created_at: '2026-01-12T08:00:00Z',
          updated_at: '2026-01-13T08:00:00Z',
        },
      ],
      total: 2,
      limit: 50,
      offset: 0,
    }),
  },
}))

vi.mock('../../src/api/approvals', () => ({
  approvalsApi: {
    listPendingApprovals: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    listAllApprovals: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'a1',
          order_id: 'o3',
          status: 'approved',
          approval_rule_ids: ['r1'],
          requested_at: '2026-01-14T10:00:00Z',
          deadline_at: '2026-01-21T10:00:00Z',
          decided_by: 'test-approver',
          decided_at: '2026-01-15T12:00:00Z',
          decision_reason: 'Alles in Ordnung',
        },
      ],
      total: 1,
    }),
  },
}))

function renderMyRequests() {
  useAuthStore.getState().setAuth('tok', {
    username: 'test-approver',
    display_name: 'Test Approver',
    email: 'approver@test.local',
    roles: ['approver'],
  })
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <MyRequests />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('MyRequests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().logout()
  })

  it('renders the page heading', () => {
    renderMyRequests()
    expect(screen.getByText('Meine Anfragen')).toBeInTheDocument()
  })

  it('renders both tabs', () => {
    renderMyRequests()
    expect(screen.getByRole('button', { name: 'Meine Bestellungen' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Meine Genehmigungen' })).toBeInTheDocument()
  })

  it('shows orders with order_number in the list', async () => {
    renderMyRequests()
    await waitFor(() => {
      expect(screen.getByText('ORD-2026-00001')).toBeInTheDocument()
      expect(screen.getByText('Mein erster Server')).toBeInTheDocument()
    })
  })

  it('order_number links to the order detail page', async () => {
    renderMyRequests()
    await waitFor(() => {
      const link = screen.getByRole('link', { name: 'ORD-2026-00001' })
      expect(link).toHaveAttribute('href', '/orders/o1')
    })
  })

  it('switches to approvals tab and shows approval history', async () => {
    renderMyRequests()
    const approvalsTab = screen.getByRole('button', { name: 'Meine Genehmigungen' })
    await userEvent.click(approvalsTab)
    await waitFor(() => {
      expect(screen.getByText('o3')).toBeInTheDocument()
    })
  })
})
