import { describe, it, expect, beforeEach } from 'vitest'
import { useAuthStore } from '../../src/store/authStore'

describe('authStore', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
    localStorage.clear()
  })

  it('starts logged out', () => {
    const state = useAuthStore.getState()
    expect(state.token).toBeNull()
    expect(state.user).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })

  it('login sets token and user', () => {
    const user = { username: 'test', display_name: 'Test', email: 'test@test.local', roles: ['requester'] }
    useAuthStore.getState().setAuth('my-token', user)

    const state = useAuthStore.getState()
    expect(state.token).toBe('my-token')
    expect(state.user).toEqual(user)
    expect(state.isAuthenticated).toBe(true)
  })

  it('logout clears state', () => {
    const user = { username: 'test', display_name: 'Test', email: 'test@test.local', roles: ['requester'] }
    useAuthStore.getState().setAuth('my-token', user)
    useAuthStore.getState().logout()

    const state = useAuthStore.getState()
    expect(state.token).toBeNull()
    expect(state.user).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })

  it('persists token to localStorage', () => {
    const user = { username: 'test', display_name: 'Test', email: 'test@test.local', roles: ['requester'] }
    useAuthStore.getState().setAuth('my-token', user)

    expect(localStorage.getItem('auth-token')).toBe('my-token')
  })

  it('restores token from localStorage', () => {
    localStorage.setItem('auth-token', 'saved-token')
    localStorage.setItem('auth-user', JSON.stringify({ username: 'saved', display_name: 'Saved', email: 's@test.local', roles: ['admin'] }))

    // Re-create store state from localStorage
    useAuthStore.getState().restoreSession()

    const state = useAuthStore.getState()
    expect(state.token).toBe('saved-token')
    expect(state.user?.username).toBe('saved')
  })
})
