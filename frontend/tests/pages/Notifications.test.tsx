import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Notifications from '../../src/pages/Notifications'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/notifications', () => ({
  notificationsApi: {
    list: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'n1', event_type: 'order_submitted', recipient_email: 'u@t',
          recipient_id: 'user-1', subject: 'Bestellung ORD-1 eingereicht',
          body: 'Ihre Bestellung wurde eingereicht.', status: 'sent',
          attempts: 0, created_at: '2026-01-15T10:00:00Z', sent_at: '2026-01-15T10:00:00Z',
          error_message: null, read_at: null,
        },
        {
          id: 'n2', event_type: 'approval_requested', recipient_email: 'u@t',
          recipient_id: 'user-1', subject: 'Genehmigung erforderlich',
          body: 'Eine Genehmigung wird benoetigt.', status: 'sent',
          attempts: 0, created_at: '2026-01-14T10:00:00Z', sent_at: '2026-01-14T10:00:00Z',
          error_message: null, read_at: '2026-01-14T11:00:00Z',
        },
      ],
      total: 2, limit: 50, offset: 0,
    }),
    unreadCount: vi.fn().mockResolvedValue({ count: 1 }),
    markRead: vi.fn().mockResolvedValue({}),
    markAllRead: vi.fn().mockResolvedValue({ marked_count: 1 }),
  },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Notifications />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Notifications', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'user-1', display_name: 'User', email: 'u@t', roles: ['requester'] },
    })
  })

  it('renders notification subjects', async () => {
    renderPage()
    expect(await screen.findByText('Bestellung ORD-1 eingereicht')).toBeInTheDocument()
    expect(await screen.findByText('Genehmigung erforderlich')).toBeInTheDocument()
  })

  it('shows alle als gelesen button', async () => {
    renderPage()
    expect(await screen.findByText('Alle als gelesen markieren')).toBeInTheDocument()
  })

  it('shows unread indicator on unread notification', async () => {
    renderPage()
    const items = await screen.findAllByTestId('notification-item')
    expect(items[0]).toHaveAttribute('data-unread', 'true')
    expect(items[1]).toHaveAttribute('data-unread', 'false')
  })
})
