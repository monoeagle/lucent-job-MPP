import { create } from 'zustand'
import type { User } from '../types/common'

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  setAuth: (token: string, user: User) => void
  logout: () => void
  restoreSession: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isAuthenticated: false,

  setAuth: (token: string, user: User) => {
    localStorage.setItem('auth-token', token)
    localStorage.setItem('auth-user', JSON.stringify(user))
    set({ token, user, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem('auth-token')
    localStorage.removeItem('auth-user')
    set({ token: null, user: null, isAuthenticated: false })
  },

  restoreSession: () => {
    const token = localStorage.getItem('auth-token')
    const userStr = localStorage.getItem('auth-user')
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr) as User
        set({ token, user, isAuthenticated: true })
      } catch {
        localStorage.removeItem('auth-token')
        localStorage.removeItem('auth-user')
      }
    }
  },
}))
