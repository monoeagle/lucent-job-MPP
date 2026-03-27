import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { useAuthStore } from '../../src/store/authStore'
import ProtectedRoute from '../../src/components/ProtectedRoute'

describe('ProtectedRoute', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
  })

  it('redirects to /login when not authenticated', () => {
    render(
      <MemoryRouter initialEntries={['/orders']}>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>
    )
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('renders children when authenticated', () => {
    useAuthStore.getState().setAuth('token', {
      username: 'test', display_name: 'Test', email: 'test@test.local', roles: ['requester'],
    })

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>
    )
    expect(screen.getByText('Protected Content')).toBeInTheDocument()
  })
})
