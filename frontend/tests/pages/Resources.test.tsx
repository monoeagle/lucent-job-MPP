import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Resources from '../../src/pages/Resources'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/resources', () => ({
  resourcesApi: {
    listResources: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'r1',
          order_id: 'o1',
          order_number: 'ORD-2026-00001',
          display_name: 'Linux VM Production',
          template_slug: 'vm-linux',
          parameters: { cpu_cores: 4, memory_gb: 16, disk_gb: 100 },
          status: 'active',
          created_at: '2026-01-15T10:00:00Z',
        },
        {
          id: 'r2',
          order_id: 'o2',
          order_number: 'ORD-2026-00002',
          display_name: 'Database Cluster',
          template_slug: 'db-postgres',
          parameters: { version: '15', replicas: 3 },
          status: 'active',
          created_at: '2026-01-16T10:00:00Z',
        },
      ],
      total: 2,
    }),
  },
}))

function renderResources() {
  useAuthStore.getState().setAuth('tok', {
    username: 'test', display_name: 'Test', email: 'test@test.local', roles: ['requester'],
  })
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Resources />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Resources', () => {
  beforeEach(() => { vi.clearAllMocks(); useAuthStore.getState().logout() })

  it('renders resources list', async () => {
    renderResources()
    await waitFor(() => {
      expect(screen.getByText('Ressourcen')).toBeInTheDocument()
      expect(screen.getByText('Linux VM Production')).toBeInTheDocument()
      expect(screen.getByText('Database Cluster')).toBeInTheDocument()
    })
  })

  it('shows order number links', async () => {
    renderResources()
    await waitFor(() => {
      expect(screen.getByText('ORD-2026-00001')).toBeInTheDocument()
      expect(screen.getByText('ORD-2026-00002')).toBeInTheDocument()
    })
  })
})
