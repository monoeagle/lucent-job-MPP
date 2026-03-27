import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Login from '../../src/pages/Login'
import { useAuthStore } from '../../src/store/authStore'

// Mock react-router-dom
const mockNavigate = vi.fn()
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}))

// Mock api client
vi.mock('../../src/api/client', () => ({
  apiClient: {
    post: vi.fn(),
  },
}))

import { apiClient } from '../../src/api/client'

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().logout()
  })

  it('renders login form', () => {
    render(<Login />)
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /anmelden/i })).toBeInTheDocument()
  })

  it('submits login and navigates on success', async () => {
    const mockResponse = {
      token: 'jwt-token',
      user: { username: 'test-requester', display_name: 'Test', email: 'test@test.local', roles: ['requester'] },
      expires_at: '2026-04-01T00:00:00Z',
    }
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

    render(<Login />)
    await userEvent.type(screen.getByLabelText(/username/i), 'test-requester')
    await userEvent.click(screen.getByRole('button', { name: /anmelden/i }))

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/auth/login', {
        username: 'test-requester',
        password: '',
      })
      expect(mockNavigate).toHaveBeenCalledWith('/orders')
    })
  })

  it('shows error on failed login', async () => {
    const { ApiError } = await import('../../src/types/common')
    vi.mocked(apiClient.post).mockRejectedValue(
      new ApiError(401, 'INVALID_CREDENTIALS', null, 'req-1', 'invalid credentials')
    )

    render(<Login />)
    await userEvent.type(screen.getByLabelText(/username/i), 'wrong-user')
    await userEvent.click(screen.getByRole('button', { name: /anmelden/i }))

    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
    })
  })
})
