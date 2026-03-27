# Phase F1: Frontend Scaffold + Layout + Auth — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up the React + TypeScript frontend with Vite, TailwindCSS, routing, sidebar layout, auth store, login page, and a protected route guard — the foundation for all subsequent frontend phases.

**Architecture:** Vite project with React 19. API client module handles auth headers and error parsing. zustand store for auth state. react-router with a ProtectedRoute wrapper. Sidebar layout with role-based navigation items.

**Tech Stack:** React 19, TypeScript, Vite 6, TailwindCSS 4, react-router-dom 7, zustand 5, @tanstack/react-query 5, vitest, @testing-library/react

---

## File Structure

```
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── src/
│   ├── main.tsx                    # Entry point: React root
│   ├── App.tsx                     # Router + QueryProvider + Layout
│   ├── api/
│   │   └── client.ts              # Base fetch wrapper with auth + error handling
│   ├── store/
│   │   └── authStore.ts           # zustand: token, user, login/logout
│   ├── types/
│   │   └── common.ts              # User, ErrorResponse, ApiError types
│   ├── hooks/
│   │   └── useAuth.ts             # Convenience hook over authStore
│   ├── components/
│   │   ├── Layout/
│   │   │   ├── AppLayout.tsx      # Sidebar + Content wrapper
│   │   │   ├── Sidebar.tsx        # Navigation with role-based items
│   │   │   └── Header.tsx         # Top bar with user info + logout
│   │   ├── ProtectedRoute.tsx     # Redirects to /login if not authed
│   │   └── StatusBadge.tsx        # Colored badge for order status
│   └── pages/
│       ├── Login.tsx              # Login form
│       └── Dashboard.tsx          # Placeholder landing page
└── tests/
    ├── setup.ts                   # vitest setup (testing-library)
    ├── api/
    │   └── client.test.ts
    ├── store/
    │   └── authStore.test.ts
    └── components/
        └── ProtectedRoute.test.tsx
```

---

### Task 1: Project Scaffold — Vite + React + TypeScript

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`

- [ ] **Step 1: Create frontend directory and package.json**

```json
{
  "name": "marketplace-portal-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "@tanstack/react-query": "^5.0.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "typescript": "^5.7.0",
    "vite": "^6.0.0",
    "vitest": "^3.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "@testing-library/user-event": "^14.0.0",
    "jsdom": "^25.0.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/vite": "^4.0.0"
  }
}
```

- [ ] **Step 2: Create vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',
  },
})
```

- [ ] **Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src", "tests"]
}
```

- [ ] **Step 4: Create index.html**

```html
<!DOCTYPE html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Marketplace Portal</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create src/main.tsx**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 6: Create src/index.css**

```css
@import "tailwindcss";
```

- [ ] **Step 7: Create src/App.tsx (minimal placeholder)**

```tsx
export default function App() {
  return <div className="p-4">Marketplace Portal</div>
}
```

- [ ] **Step 8: Create tests/setup.ts**

```typescript
import '@testing-library/jest-dom/vitest'
```

- [ ] **Step 9: Install dependencies and verify**

Run: `cd frontend && npm install`
Run: `npx vitest run` (should pass with 0 tests, no errors)
Run: `npx tsc --noEmit` (should compile clean)

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold Vite + React + TypeScript + TailwindCSS project"
```

---

### Task 2: Types — Common API Types

**Files:**
- Create: `frontend/src/types/common.ts`
- Test: `frontend/tests/types/common.test.ts`

- [ ] **Step 1: Write types**

```typescript
// frontend/src/types/common.ts

export interface User {
  username: string
  display_name: string
  email: string
  roles: string[]
}

export interface LoginResponse {
  token: string
  user: User
  expires_at: string
}

export interface ErrorResponse {
  error_code: string
  message: string
  details: Record<string, unknown> | null
  request_id: string
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public errorCode: string,
    public details: Record<string, unknown> | null,
    public requestId: string,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export function hasRole(user: User | null, role: string): boolean {
  return user?.roles.includes(role) ?? false
}

export function isAdmin(user: User | null): boolean {
  return hasRole(user, 'admin')
}

export function isApprover(user: User | null): boolean {
  return hasRole(user, 'approver')
}
```

- [ ] **Step 2: Write test**

```typescript
// frontend/tests/types/common.test.ts
import { describe, it, expect } from 'vitest'
import { hasRole, isAdmin, isApprover, ApiError } from '../../src/types/common'

describe('hasRole', () => {
  it('returns true when user has role', () => {
    const user = { username: 'test', display_name: 'Test', email: 'test@test.local', roles: ['requester'] }
    expect(hasRole(user, 'requester')).toBe(true)
  })

  it('returns false when user lacks role', () => {
    const user = { username: 'test', display_name: 'Test', email: 'test@test.local', roles: ['requester'] }
    expect(hasRole(user, 'admin')).toBe(false)
  })

  it('returns false for null user', () => {
    expect(hasRole(null, 'admin')).toBe(false)
  })
})

describe('isAdmin', () => {
  it('returns true for admin', () => {
    const user = { username: 'admin', display_name: 'Admin', email: 'a@test.local', roles: ['admin'] }
    expect(isAdmin(user)).toBe(true)
  })
})

describe('isApprover', () => {
  it('returns true for approver', () => {
    const user = { username: 'app', display_name: 'App', email: 'a@test.local', roles: ['approver'] }
    expect(isApprover(user)).toBe(true)
  })
})

describe('ApiError', () => {
  it('creates with all fields', () => {
    const err = new ApiError(400, 'VALIDATION_FAILED', { fields: [] }, 'req-1', 'Bad request')
    expect(err.status).toBe(400)
    expect(err.errorCode).toBe('VALIDATION_FAILED')
    expect(err.name).toBe('ApiError')
  })
})
```

- [ ] **Step 3: Run tests**

Run: `cd frontend && npx vitest run`
Expected: 6 passed

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/ frontend/tests/types/
git commit -m "feat(frontend): add common types (User, ErrorResponse, ApiError)"
```

---

### Task 3: API Client — Fetch Wrapper with Auth

**Files:**
- Create: `frontend/src/api/client.ts`
- Test: `frontend/tests/api/client.test.ts`

- [ ] **Step 1: Write test**

```typescript
// frontend/tests/api/client.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiClient } from '../../src/api/client'

describe('apiClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('adds auth header when token is provided', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ status: 'ok' }),
      headers: new Headers({ 'content-type': 'application/json' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await apiClient.get('/api/v1/health', 'test-token')

    expect(mockFetch).toHaveBeenCalledWith('/api/v1/health', expect.objectContaining({
      headers: expect.objectContaining({
        Authorization: 'Bearer test-token',
      }),
    }))
  })

  it('does not add auth header when no token', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ status: 'ok' }),
      headers: new Headers({ 'content-type': 'application/json' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await apiClient.get('/api/v1/health')

    const calledHeaders = mockFetch.mock.calls[0][1].headers
    expect(calledHeaders.Authorization).toBeUndefined()
  })

  it('throws ApiError on 4xx response', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.resolve({
        error_code: 'NOT_FOUND',
        message: 'Not found',
        details: null,
        request_id: 'req-1',
      }),
      headers: new Headers({ 'content-type': 'application/json' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    const { ApiError } = await import('../../src/types/common')
    await expect(apiClient.get('/api/v1/missing')).rejects.toThrow(ApiError)
  })

  it('posts JSON body', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ success: true }),
      headers: new Headers({ 'content-type': 'application/json' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await apiClient.post('/api/v1/test', { key: 'value' }, 'token')

    expect(mockFetch).toHaveBeenCalledWith('/api/v1/test', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ key: 'value' }),
    }))
  })
})
```

- [ ] **Step 2: Run test — verify FAIL**
- [ ] **Step 3: Implement API client**

```typescript
// frontend/src/api/client.ts
import { ApiError } from '../types/common'

async function handleResponse(response: Response): Promise<unknown> {
  const data = await response.json()

  if (!response.ok) {
    throw new ApiError(
      response.status,
      data.error_code ?? 'UNKNOWN_ERROR',
      data.details ?? null,
      data.request_id ?? '',
      data.message ?? 'An error occurred',
    )
  }

  return data
}

function buildHeaders(token?: string): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  return headers
}

export const apiClient = {
  async get(url: string, token?: string): Promise<unknown> {
    const response = await fetch(url, {
      method: 'GET',
      headers: buildHeaders(token),
    })
    return handleResponse(response)
  },

  async post(url: string, body?: unknown, token?: string): Promise<unknown> {
    const response = await fetch(url, {
      method: 'POST',
      headers: buildHeaders(token),
      body: body ? JSON.stringify(body) : undefined,
    })
    return handleResponse(response)
  },

  async patch(url: string, body: unknown, token?: string): Promise<unknown> {
    const response = await fetch(url, {
      method: 'PATCH',
      headers: buildHeaders(token),
      body: JSON.stringify(body),
    })
    return handleResponse(response)
  },

  async put(url: string, body: unknown, token?: string): Promise<unknown> {
    const response = await fetch(url, {
      method: 'PUT',
      headers: buildHeaders(token),
      body: JSON.stringify(body),
    })
    return handleResponse(response)
  },

  async del(url: string, token?: string): Promise<void> {
    const response = await fetch(url, {
      method: 'DELETE',
      headers: buildHeaders(token),
    })
    if (!response.ok) {
      const data = await response.json()
      throw new ApiError(
        response.status,
        data.error_code ?? 'UNKNOWN_ERROR',
        data.details ?? null,
        data.request_id ?? '',
        data.message ?? 'An error occurred',
      )
    }
  },
}
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/ frontend/tests/api/
git commit -m "feat(frontend): add API client with auth headers and error handling"
```

---

### Task 4: Auth Store — zustand

**Files:**
- Create: `frontend/src/store/authStore.ts`
- Create: `frontend/src/hooks/useAuth.ts`
- Test: `frontend/tests/store/authStore.test.ts`

- [ ] **Step 1: Write test**

```typescript
// frontend/tests/store/authStore.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
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
```

- [ ] **Step 2: Run test — verify FAIL**
- [ ] **Step 3: Implement auth store**

```typescript
// frontend/src/store/authStore.ts
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
```

```typescript
// frontend/src/hooks/useAuth.ts
import { useAuthStore } from '../store/authStore'

export function useAuth() {
  return useAuthStore()
}
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/store/ frontend/src/hooks/ frontend/tests/store/
git commit -m "feat(frontend): add auth store with localStorage persistence"
```

---

### Task 5: Login Page

**Files:**
- Create: `frontend/src/pages/Login.tsx`
- Test: `frontend/tests/pages/Login.test.tsx`

- [ ] **Step 1: Write test**

```typescript
// frontend/tests/pages/Login.test.tsx
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
```

- [ ] **Step 2: Run test — verify FAIL**
- [ ] **Step 3: Implement Login page**

```tsx
// frontend/src/pages/Login.tsx
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../api/client'
import { useAuthStore } from '../store/authStore'
import type { LoginResponse, ApiError } from '../types/common'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const data = (await apiClient.post('/api/v1/auth/login', {
        username,
        password,
      })) as LoginResponse
      setAuth(data.token, data.user)
      navigate('/orders')
    } catch (err) {
      const apiErr = err as ApiError
      setError(apiErr.message || 'Login fehlgeschlagen')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm p-8 bg-white rounded-lg shadow">
        <h1 className="text-2xl font-bold text-center mb-6">Marketplace Portal</h1>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <div className="mb-4">
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="optional im Stub-Modus"
            />
          </div>
          {error && (
            <p className="mb-4 text-sm text-red-600">{error}</p>
          )}
          <button
            type="submit"
            disabled={loading || !username}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Wird angemeldet...' : 'Anmelden'}
          </button>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Login.tsx frontend/tests/pages/
git commit -m "feat(frontend): add Login page with auth store integration"
```

---

### Task 6: Layout — Sidebar + Header + ProtectedRoute

**Files:**
- Create: `frontend/src/components/Layout/AppLayout.tsx`
- Create: `frontend/src/components/Layout/Sidebar.tsx`
- Create: `frontend/src/components/Layout/Header.tsx`
- Create: `frontend/src/components/ProtectedRoute.tsx`
- Create: `frontend/src/components/StatusBadge.tsx`
- Test: `frontend/tests/components/ProtectedRoute.test.tsx`

- [ ] **Step 1: Write ProtectedRoute test**

```typescript
// frontend/tests/components/ProtectedRoute.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
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
```

- [ ] **Step 2: Run test — verify FAIL**
- [ ] **Step 3: Implement components**

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
      return <Navigate to="/orders" replace />
    }
  }

  return <>{children}</>
}
```

```tsx
// frontend/src/components/Layout/Sidebar.tsx
import { NavLink } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { isAdmin, isApprover } from '../../types/common'

const navItems = [
  { to: '/catalog', label: 'Service Catalog', roles: null },
  { to: '/orders', label: 'Meine Bestellungen', roles: null },
  { to: '/resources', label: 'Meine Ressourcen', roles: null },
  { to: '/approvals', label: 'Genehmigungen', roles: ['approver', 'admin'] },
  { to: '/admin/dashboard', label: 'Admin Dashboard', roles: ['admin'] },
  { to: '/admin/rules', label: 'Regelverwaltung', roles: ['admin'] },
  { to: '/admin/audit', label: 'Audit Log', roles: ['admin'] },
]

export default function Sidebar() {
  const user = useAuthStore((s) => s.user)

  const visibleItems = navItems.filter((item) => {
    if (!item.roles) return true
    return item.roles.some((role) => user?.roles.includes(role))
  })

  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen p-4">
      <div className="text-lg font-bold mb-8 px-2">Marketplace Portal</div>
      <nav className="space-y-1">
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `block px-3 py-2 rounded-md text-sm ${
                isActive ? 'bg-gray-700 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
```

```tsx
// frontend/src/components/Layout/Header.tsx
import { useAuthStore } from '../../store/authStore'
import { useNavigate } from 'react-router-dom'

export default function Header() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      <div />
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-600">
          {user?.display_name} ({user?.roles.join(', ')})
        </span>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Abmelden
        </button>
      </div>
    </header>
  )
}
```

```tsx
// frontend/src/components/Layout/AppLayout.tsx
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'

export default function AppLayout() {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

```tsx
// frontend/src/components/StatusBadge.tsx
const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-800',
  validated: 'bg-blue-100 text-blue-800',
  submitted: 'bg-yellow-100 text-yellow-800',
  pending_approval: 'bg-orange-100 text-orange-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  provisioning: 'bg-purple-100 text-purple-800',
  done: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
}

interface Props {
  status: string
}

export default function StatusBadge({ status }: Props) {
  const colors = statusColors[status] ?? 'bg-gray-100 text-gray-800'
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors}`}>
      {status}
    </span>
  )
}
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ frontend/tests/components/
git commit -m "feat(frontend): add AppLayout with Sidebar, Header, ProtectedRoute, and StatusBadge"
```

---

### Task 7: Router — Wire Everything Together

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Create placeholder Dashboard**

```tsx
// frontend/src/pages/Dashboard.tsx
export default function Dashboard() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Willkommen</h1>
      <p className="text-gray-600">Wählen Sie einen Bereich in der Navigation.</p>
    </div>
  )
}
```

- [ ] **Step 2: Update App.tsx with full routing**

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
        <Route index element={<Navigate to="/orders" replace />} />
        <Route path="/catalog" element={<Dashboard />} />
        <Route path="/orders" element={<Dashboard />} />
        <Route path="/resources" element={<Dashboard />} />
        <Route path="/approvals" element={<Dashboard />} />
        <Route path="/admin/*" element={<Dashboard />} />
      </Route>
      <Route path="*" element={<Navigate to="/orders" replace />} />
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

- [ ] **Step 3: Run all tests**

Run: `cd frontend && npx vitest run`
Expected: All pass

- [ ] **Step 4: Manual smoke test**

Run: `cd frontend && npm run dev`
Open http://localhost:3000 — should redirect to /login.
Login with "test-requester" — should show sidebar + dashboard placeholder.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/pages/Dashboard.tsx
git commit -m "feat(frontend): add router with protected routes and sidebar layout"
```

---

### Task 8: Final Verification

- [ ] **Step 1: Run all frontend tests**

Run: `cd frontend && npx vitest run`

- [ ] **Step 2: Type check**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`

- [ ] **Step 4: Verify structure**

```
frontend/src/
├── api/client.ts
├── store/authStore.ts
├── hooks/useAuth.ts
├── types/common.ts
├── components/
│   ├── Layout/AppLayout.tsx, Sidebar.tsx, Header.tsx
│   ├── ProtectedRoute.tsx
│   └── StatusBadge.tsx
├── pages/Login.tsx, Dashboard.tsx
├── App.tsx
├── main.tsx
└── index.css
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore(frontend): phase F1 complete — scaffold, auth, layout, routing"
```
