import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Approvals from '../../src/pages/Approvals'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/approvals', () => ({
  approvalsApi: {
    listAllApprovals: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'a1',
          order_id: 'o1',
          order_title: 'Linux VM für Team A',
          requester_name: 'Alice Muster',
          estimated_cost: 120.5,
          status: 'pending',
          approval_rule_ids: ['r1'],
          requested_at: '2026-01-15T10:00:00Z',
          deadline_at: '2026-01-22T10:00:00Z',
          decided_by: null,
          decided_at: null,
          decision_reason: null,
        },
        {
          id: 'a2',
          order_id: 'o2',
          order_title: 'PostgreSQL Datenbank',
          requester_name: 'Bob Beispiel',
          estimated_cost: 45.0,
          status: 'pending',
          approval_rule_ids: ['r2'],
          requested_at: '2026-01-16T10:00:00Z',
          deadline_at: '2026-01-23T10:00:00Z',
          decided_by: null,
          decided_at: null,
          decision_reason: null,
        },
      ],
      total: 2,
    }),
    approve: vi.fn().mockResolvedValue({}),
    reject: vi.fn().mockResolvedValue({}),
  },
}))

function renderApprovals() {
  useAuthStore.getState().setAuth('tok', {
    username: 'admin',
    display_name: 'Admin',
    email: 'admin@test.local',
    roles: ['admin', 'approver'],
  })
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Approvals />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Approvals', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().logout()
  })

  it('renders heading "Review Requests"', async () => {
    renderApprovals()
    await waitFor(() => {
      expect(screen.getByText('Review Requests')).toBeInTheDocument()
    })
  })

  it('shows approval entries with order titles', async () => {
    renderApprovals()
    await waitFor(() => {
      expect(screen.getByText('Linux VM für Team A')).toBeInTheDocument()
      expect(screen.getByText('PostgreSQL Datenbank')).toBeInTheDocument()
      expect(screen.getByText('Alice Muster')).toBeInTheDocument()
      expect(screen.getByText('Bob Beispiel')).toBeInTheDocument()
    })
  })

  it('shows bulk action buttons', async () => {
    renderApprovals()
    await waitFor(() => {
      expect(screen.getByText('Ausgewählte genehmigen')).toBeInTheDocument()
      expect(screen.getByText('Ausgewählte ablehnen')).toBeInTheDocument()
    })
  })

  it('shows select-all checkbox', async () => {
    renderApprovals()
    await waitFor(() => {
      expect(screen.getByTestId('select-all')).toBeInTheDocument()
    })
  })
})
