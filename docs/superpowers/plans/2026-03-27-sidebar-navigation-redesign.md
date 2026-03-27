# Sidebar + Navigation Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat sidebar navigation with a collapsible sidebar featuring new menu structure, role-based admin section, user/logout footer, and updated routing.

**Architecture:** Sidebar becomes stateful component with localStorage-persisted collapse state. Navigation items split into main section, admin section (separator), and user footer. Routes renamed (/shop, /my-services, /reviews) with redirects from old paths. New Notifications placeholder page.

**Tech Stack:** React 19, TypeScript, TailwindCSS 4, React Router v6, zustand

**Spec:** `docs/superpowers/specs/2026-03-27-sidebar-navigation-redesign.md`

---

## File Structure (new/modified)

```
frontend/src/
├── components/Layout/
│   ├── Sidebar.tsx           # REWRITE: collapsible, new menu, admin section, user footer
│   ├── AppLayout.tsx         # MODIFY: dynamic sidebar width
│   └── Header.tsx            # MODIFY: remove user/logout (moved to sidebar)
├── pages/
│   └── Notifications.tsx     # NEW: placeholder page
└── App.tsx                   # MODIFY: new routes, redirects, default route

frontend/tests/
├── components/Layout/
│   └── Sidebar.test.tsx      # NEW: sidebar rendering, collapse, role-based visibility
└── pages/
    └── Notifications.test.tsx # NEW: placeholder page test
```

---

### Task 1: Notifications Placeholder Page

**Files:**
- Create: `frontend/src/pages/Notifications.tsx`
- Create: `frontend/tests/pages/Notifications.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/tests/pages/Notifications.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Notifications from '../../src/pages/Notifications'

describe('Notifications', () => {
  it('renders the notifications heading', () => {
    render(<Notifications />)
    expect(screen.getByText('Benachrichtigungen')).toBeInTheDocument()
  })

  it('shows empty state message', () => {
    render(<Notifications />)
    expect(screen.getByText('Keine Benachrichtigungen vorhanden')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `cd frontend && npx vitest run tests/pages/Notifications.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Implement**

```tsx
// frontend/src/pages/Notifications.tsx
export default function Notifications() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Benachrichtigungen</h1>
      <p className="text-gray-500">Keine Benachrichtigungen vorhanden</p>
    </div>
  )
}
```

- [ ] **Step 4: Run test — verify PASS**

Run: `cd frontend && npx vitest run tests/pages/Notifications.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Notifications.tsx frontend/tests/pages/Notifications.test.tsx
git commit -m "feat(frontend): add Notifications placeholder page"
```

---

### Task 2: Collapsible Sidebar

**Files:**
- Rewrite: `frontend/src/components/Layout/Sidebar.tsx`
- Create: `frontend/tests/components/Layout/Sidebar.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
// frontend/tests/components/Layout/Sidebar.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
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
```

- [ ] **Step 2: Run tests — verify FAIL**

Run: `cd frontend && npx vitest run tests/components/Layout/Sidebar.test.tsx`
Expected: FAIL — missing test IDs, missing nav items, wrong class names

- [ ] **Step 3: Implement Sidebar**

```tsx
// frontend/src/components/Layout/Sidebar.tsx
import { useState, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

const STORAGE_KEY = 'mpp-sidebar-collapsed'

interface NavItem {
  to: string
  label: string
  icon: string
  roles: string[] | null
  disabled?: boolean
}

const mainItems: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: '📊', roles: null },
  { to: '/shop', label: 'Shop', icon: '🛒', roles: null },
  { to: '/my-services', label: 'My Services', icon: '📋', roles: null },
  { to: '/notifications', label: 'Notifications', icon: '🔔', roles: null },
  { to: '/reviews', label: 'Review Requests', icon: '✅', roles: ['approver', 'admin'] },
  { to: '#', label: 'Subscriptions', icon: '📦', roles: null, disabled: true },
]

const adminItems: NavItem[] = [
  { to: '/admin', label: 'Admin Dashboard', icon: '⚙', roles: ['admin'] },
  { to: '/admin/rules', label: 'Rules', icon: '📏', roles: ['admin'] },
  { to: '/admin/audit-log', label: 'Audit Log', icon: '📜', roles: ['admin'] },
]

function NavItemLink({ item, collapsed }: { item: NavItem; collapsed: boolean }) {
  if (item.disabled) {
    return (
      <div
        className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-gray-500 opacity-50 cursor-not-allowed"
        title="Kommt bald"
      >
        <span className="text-base w-5 text-center">{item.icon}</span>
        {!collapsed && <span>{item.label}</span>}
      </div>
    )
  }

  return (
    <NavLink
      to={item.to}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 rounded-md text-sm ${
          isActive
            ? 'bg-gray-700 text-white'
            : 'text-gray-300 hover:bg-gray-800 hover:text-white'
        }`
      }
    >
      <span className="text-base w-5 text-center">{item.icon}</span>
      {!collapsed && <span>{item.label}</span>}
    </NavLink>
  )
}

export default function Sidebar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem(STORAGE_KEY) === 'true'
  })

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(collapsed))
  }, [collapsed])

  const isVisible = (item: NavItem) => {
    if (!item.roles) return true
    return item.roles.some((role) => user?.roles.includes(role))
  }

  const visibleMain = mainItems.filter(isVisible)
  const visibleAdmin = adminItems.filter(isVisible)

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <aside
      data-testid="sidebar"
      className={`${collapsed ? 'w-16' : 'w-60'} bg-gray-900 text-white min-h-screen flex flex-col transition-all duration-200`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4">
        {!collapsed && <span className="text-lg font-bold">MPP</span>}
        <button
          data-testid="sidebar-toggle"
          onClick={() => setCollapsed(!collapsed)}
          className="text-gray-400 hover:text-white p-1"
        >
          {collapsed ? '»' : '«'}
        </button>
      </div>

      {/* Main nav */}
      <nav className="flex-1 px-2 space-y-1">
        {visibleMain.map((item) => (
          <NavItemLink key={item.label} item={item} collapsed={collapsed} />
        ))}

        {/* Admin section */}
        {visibleAdmin.length > 0 && (
          <>
            <div className="border-t border-gray-700 my-3" />
            {visibleAdmin.map((item) => (
              <NavItemLink key={item.label} item={item} collapsed={collapsed} />
            ))}
          </>
        )}
      </nav>

      {/* User footer */}
      <div className="border-t border-gray-700 p-3">
        <div className="flex items-center gap-3 px-1">
          <span className="text-base">👤</span>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <div className="text-sm text-gray-300 truncate">{user?.display_name}</div>
              <button
                onClick={handleLogout}
                className="text-xs text-gray-500 hover:text-gray-300"
              >
                Abmelden
              </button>
            </div>
          )}
        </div>
      </div>
    </aside>
  )
}
```

- [ ] **Step 4: Run tests — verify PASS**

Run: `cd frontend && npx vitest run tests/components/Layout/Sidebar.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Layout/Sidebar.tsx frontend/tests/components/Layout/Sidebar.test.tsx
git commit -m "feat(frontend): rewrite Sidebar with collapsible layout, new menu structure, role-based sections"
```

---

### Task 3: Update AppLayout + Header

**Files:**
- Modify: `frontend/src/components/Layout/AppLayout.tsx`
- Modify: `frontend/src/components/Layout/Header.tsx`

- [ ] **Step 1: Update AppLayout**

The layout needs no structural changes — Sidebar handles its own width via `w-60`/`w-16` classes and `transition-all`. The `flex-1` on the content div already adapts. Just verify it works.

```tsx
// frontend/src/components/Layout/AppLayout.tsx
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'

export default function AppLayout() {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header />
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

Note: Added `min-w-0` to prevent content overflow when sidebar expands.

- [ ] **Step 2: Simplify Header**

Remove user/logout (now in Sidebar footer). Header becomes a minimal top bar.

```tsx
// frontend/src/components/Layout/Header.tsx
export default function Header() {
  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center px-6">
      <div />
    </header>
  )
}
```

- [ ] **Step 3: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All existing tests still pass

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Layout/AppLayout.tsx frontend/src/components/Layout/Header.tsx
git commit -m "feat(frontend): update AppLayout for collapsible sidebar, simplify Header"
```

---

### Task 4: Update Routes in App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/ProtectedRoute.tsx` (update redirect target)

- [ ] **Step 1: Update App.tsx**

Add new routes, redirects from old paths, Notifications page, default to `/dashboard`.

```tsx
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useAuthStore } from './store/authStore'
import ProtectedRoute from './components/ProtectedRoute'
import AppLayout from './components/Layout/AppLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Catalog from './pages/Catalog'
import OrderList from './pages/OrderList'
import OrderNew from './pages/OrderNew'
import OrderDetail from './pages/OrderDetail'
import OrderExport from './pages/OrderExport'
import Approvals from './pages/Approvals'
import Resources from './pages/Resources'
import Notifications from './pages/Notifications'
import AdminDashboard from './pages/admin/Dashboard'
import Rules from './pages/admin/Rules'
import AuditLog from './pages/admin/AuditLog'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
})

function AppRoutes() {
  const restoreSession = useAuthStore((s) => s.restoreSession)

  useEffect(() => {
    restoreSession()
  }, [restoreSession])

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/shop" element={<Catalog />} />
        <Route path="/my-services" element={<Resources />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="/orders" element={<OrderList />} />
        <Route path="/orders/new" element={<OrderNew />} />
        <Route path="/orders/:orderId" element={<OrderDetail />} />
        <Route path="/orders/:orderId/export" element={<OrderExport />} />
        <Route
          path="/reviews"
          element={
            <ProtectedRoute requiredRoles={['approver', 'admin']}>
              <Approvals />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute requiredRoles={['admin']}>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/rules"
          element={
            <ProtectedRoute requiredRoles={['admin']}>
              <Rules />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/audit-log"
          element={
            <ProtectedRoute requiredRoles={['admin']}>
              <AuditLog />
            </ProtectedRoute>
          }
        />
        {/* Redirects from old paths */}
        <Route path="/catalog" element={<Navigate to="/shop" replace />} />
        <Route path="/resources" element={<Navigate to="/my-services" replace />} />
        <Route path="/approvals" element={<Navigate to="/reviews" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
```

- [ ] **Step 2: Update ProtectedRoute redirect target**

Change fallback redirect from `/orders` to `/dashboard`.

```tsx
// frontend/src/components/ProtectedRoute.tsx
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

interface Props {
  children: React.ReactNode
  requiredRoles?: string[]
}

export default function ProtectedRoute({ children, requiredRoles }: Props) {
  const { isAuthenticated, user } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (requiredRoles && user) {
    const hasRequiredRole = requiredRoles.some((role) => user.roles.includes(role))
    if (!hasRequiredRole) {
      return <Navigate to="/dashboard" replace />
    }
  }

  return <>{children}</>
}
```

- [ ] **Step 3: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass. Some existing tests using `/catalog` or `/resources` routes may need path updates in their MemoryRouter initialEntries — fix any failures.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/ProtectedRoute.tsx
git commit -m "feat(frontend): update routes — /shop, /my-services, /reviews, /dashboard default, redirects from old paths"
```

---

### Task 5: Fix Existing Tests for Route Changes

**Files:**
- Modify: `frontend/tests/components/ProtectedRoute.test.tsx` (update redirect expectations from `/orders` to `/dashboard`)
- Modify: any test files that reference old routes

- [ ] **Step 1: Scan tests for old route references**

Search for `/orders`, `/catalog`, `/resources`, `/approvals` in test files and update to new paths where they appear in MemoryRouter initialEntries or redirect assertions.

Key changes:
- ProtectedRoute test: redirect target `/orders` → `/dashboard`
- Any MemoryRouter with `initialEntries={['/catalog']}` → `initialEntries={['/shop']}`
- Any MemoryRouter with `initialEntries={['/resources']}` → `initialEntries={['/my-services']}`
- Any MemoryRouter with `initialEntries={['/approvals']}` → `initialEntries={['/reviews']}`

- [ ] **Step 2: Run all frontend tests**

Run: `cd frontend && npx vitest run`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/
git commit -m "test(frontend): update test routes for sidebar navigation redesign"
```

---

### Task 6: Final Verification

- [ ] **Step 1: Run full frontend test suite**

Run: `cd frontend && npx vitest run`
Expected: All tests pass, no warnings

- [ ] **Step 2: Type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Run backend tests (sanity check)**

Run: `source venv/bin/activate && DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_test pytest tests/ -q`
Expected: All 648 tests pass (backend unaffected)

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: sidebar navigation redesign complete — collapsible sidebar, new routes, role-based menu"
```
