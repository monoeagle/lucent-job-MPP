import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Approvals from '../../src/pages/Approvals'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/approvals', () => ({
  approvalsApi: {
    listPendingApprovals: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'a1',
          order_id: 'o1',
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
    username: 'admin', display_name: 'Admin', email: 'admin@test.local', roles: ['admin', 'approver'],
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
  beforeEach(() => { vi.clearAllMocks(); useAuthStore.getState().logout() })

  it('renders approval requests list', async () => {
    renderApprovals()
    await waitFor(() => {
      expect(screen.getByText('Genehmigungen')).toBeInTheDocument()
      expect(screen.getByText('o1')).toBeInTheDocument()
      expect(screen.getByText('o2')).toBeInTheDocument()
    })
  })

  it('shows approve and reject buttons', async () => {
    renderApprovals()
    await waitFor(() => {
      const approveButtons = screen.getAllByText('Genehmigen')
      expect(approveButtons).toHaveLength(2)
      const rejectButtons = screen.getAllByText('Ablehnen')
      expect(rejectButtons).toHaveLength(2)
    })
  })
})
