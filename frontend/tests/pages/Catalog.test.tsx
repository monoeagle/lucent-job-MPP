import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Catalog from '../../src/pages/Catalog'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/catalog', () => ({
  catalogApi: {
    listTemplates: vi.fn().mockResolvedValue({
      data: [
        {
          id: 't1', slug: 'vm-linux', version: '1.0.0', type: 'vm',
          display_name: 'Linux VM', description: 'Standard Linux Virtual Machine',
          category: 'Compute', icon_identifier: null, status: 'active',
          created_at: '2026-01-01', deprecated_at: null, deprecated_by: null,
          estimated_cost_eur_per_month: 49.99, approval_always_required: false,
        },
        {
          id: 't2', slug: 'postgres-db', version: '2.0.0', type: 'database',
          display_name: 'PostgreSQL DB', description: 'Managed PostgreSQL database',
          category: 'Database', icon_identifier: null, status: 'active',
          created_at: '2026-01-01', deprecated_at: null, deprecated_by: null,
          estimated_cost_eur_per_month: null, approval_always_required: false,
        },
      ],
      total: 2, limit: 20, offset: 0,
    }),
    getTemplate: vi.fn().mockResolvedValue({ parameters: [] }),
    getCategories: vi.fn().mockResolvedValue({
      categories: [
        { name: 'Compute', template_count: 1 },
        { name: 'Database', template_count: 1 },
      ],
    }),
  },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Catalog />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Catalog', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'test', display_name: 'T', email: 't@t', roles: ['requester'] },
    })
  })

  it('renders template cards', async () => {
    renderPage()
    expect(await screen.findByText('Linux VM')).toBeInTheDocument()
    expect(screen.getByText('PostgreSQL DB')).toBeInTheDocument()
  })

  it('shows Bestellen button for active templates', async () => {
    renderPage()
    const buttons = await screen.findAllByText('Bestellen')
    expect(buttons.length).toBeGreaterThanOrEqual(1)
  })

  it('shows template description', async () => {
    renderPage()
    expect(await screen.findByText('Standard Linux Virtual Machine')).toBeInTheDocument()
  })

  it('shows estimated cost when available', async () => {
    renderPage()
    expect(await screen.findByText('~49.99 EUR/Monat')).toBeInTheDocument()
  })
})
