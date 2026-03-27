import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Sidebar from '../../../src/components/Layout/Sidebar'
import { useAuthStore } from '../../../src/store/authStore'

function renderSidebar() {
  return render(
    <MemoryRouter>
      <Sidebar />
    </MemoryRouter>
  )
}

describe('Sidebar', () => {
  beforeEach(() => {
    localStorage.clear()
    useAuthStore.setState({
      isAuthenticated: true,
      user: {
        username: 'test-user',
        display_name: 'Test User',
        email: 'test@example.com',
        roles: ['requester'],
      },
    })
  })

  describe('main navigation', () => {
    it('renders main nav items for regular user', () => {
      renderSidebar()
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
      expect(screen.getByText('Shop')).toBeInTheDocument()
      expect(screen.getByText('My Services')).toBeInTheDocument()
      expect(screen.getByText('Notifications')).toBeInTheDocument()
    })

    it('shows Subscriptions as disabled', () => {
      renderSidebar()
      const sub = screen.getByText('Subscriptions')
      expect(sub.closest('div')).toHaveClass('opacity-50')
    })

    it('hides Review Requests for regular user', () => {
      renderSidebar()
      expect(screen.queryByText('Review Requests')).not.toBeInTheDocument()
    })

    it('hides admin section for regular user', () => {
      renderSidebar()
      expect(screen.queryByText('Admin Dashboard')).not.toBeInTheDocument()
    })
  })

  describe('role-based visibility', () => {
    it('shows Review Requests for approver', () => {
      useAuthStore.setState({
        user: {
          username: 'approver',
          display_name: 'Approver',
          email: 'a@example.com',
          roles: ['approver'],
        },
      })
      renderSidebar()
      expect(screen.getByText('Review Requests')).toBeInTheDocument()
    })

    it('shows admin section for admin', () => {
      useAuthStore.setState({
        user: {
          username: 'admin',
          display_name: 'Admin',
          email: 'admin@example.com',
          roles: ['admin'],
        },
      })
      renderSidebar()
      expect(screen.getByText('Admin Dashboard')).toBeInTheDocument()
      expect(screen.getByText('Rules')).toBeInTheDocument()
      expect(screen.getByText('Audit Log')).toBeInTheDocument()
    })
  })

  describe('collapse behavior', () => {
    it('starts expanded by default', () => {
      renderSidebar()
      expect(screen.getByText('Dashboard')).toBeVisible()
      expect(screen.getByTestId('sidebar')).toHaveClass('w-60')
    })

    it('collapses when toggle clicked', () => {
      renderSidebar()
      fireEvent.click(screen.getByTestId('sidebar-toggle'))
      expect(screen.getByTestId('sidebar')).toHaveClass('w-16')
    })

    it('persists collapsed state in localStorage', () => {
      renderSidebar()
      fireEvent.click(screen.getByTestId('sidebar-toggle'))
      expect(localStorage.getItem('mpp-sidebar-collapsed')).toBe('true')
    })

    it('restores collapsed state from localStorage', () => {
      localStorage.setItem('mpp-sidebar-collapsed', 'true')
      renderSidebar()
      expect(screen.getByTestId('sidebar')).toHaveClass('w-16')
    })
  })

  describe('user footer', () => {
    it('shows username and logout button', () => {
      renderSidebar()
      expect(screen.getByText('Test User')).toBeInTheDocument()
      expect(screen.getByText('Abmelden')).toBeInTheDocument()
    })
  })
})
