# My Services + My Requests + Review Requests — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Combine Resources+Subscriptions into MyServices, Orders+Approvals into MyRequests, improve Review Requests with inline details and bulk actions.

**Architecture:** Pure frontend changes. Two new tab-based pages (MyServices, MyRequests) reusing existing hooks and API clients. Enhanced Approvals page with expandable details and checkbox-based bulk actions. Route updates and sidebar label changes.

**Tech Stack:** React 19, TypeScript, TailwindCSS 4, tanstack-query

**Spec:** `docs/superpowers/specs/2026-03-27-my-services-requests-reviews-design.md`

---

## File Structure

```
frontend/src/
├── pages/
│   ├── MyServices.tsx            # NEW: Resources + Subscriptions tabs
│   ├── MyRequests.tsx            # NEW: Orders + Approvals tabs
│   └── Approvals.tsx             # REWRITE: details + bulk actions
├── components/Layout/
│   └── Sidebar.tsx               # MODIFY: labels + remove Subscriptions item
└── App.tsx                       # MODIFY: routes + redirects

frontend/tests/pages/
├── MyServices.test.tsx           # NEW
├── MyRequests.test.tsx           # NEW
└── Approvals.test.tsx            # REWRITE
```

---

### Task 1: MyServices Page

**Files:**
- Create: `frontend/src/pages/MyServices.tsx`
- Create: `frontend/tests/pages/MyServices.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/tests/pages/MyServices.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import MyServices from '../../src/pages/MyServices'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/resources', () => ({
  resourcesApi: {
    listResources: vi.fn().mockResolvedValue({
      items: [
        { id: 'r1', order_id: 'o1', order_number: 'ORD-1', display_name: 'Linux VM Production',
          template_slug: 'vm-linux', parameters: { cpu: 4 }, status: 'active', created_at: '2026-01-15' },
      ],
    }),
  },
}))

vi.mock('../../src/api/subscriptions', () => ({
  subscriptionsApi: {
    list: vi.fn().mockResolvedValue({
      items: [
        { id: 's1', order_item_id: 'i1', group_subscription_id: null, requester_id: 'test-requester',
          status: 'active', display_name: 'DB Cluster', template_slug: 'db-postgres',
          template_version: '1.0.0', parameters: { storage: 100 }, pending_changes: null,
          monthly_cost_eur: 45, activated_at: '2026-01-15', cancelled_at: null,
          created_at: '2026-01-15', updated_at: '2026-01-15' },
      ],
      total: 1, limit: 50, offset: 0,
    }),
    listGroups: vi.fn().mockResolvedValue([]),
  },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <MyServices />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('MyServices', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'test-requester', display_name: 'Test', email: 't@t', roles: ['requester'] },
    })
  })

  it('renders heading', async () => {
    renderPage()
    expect(await screen.findByText('My Services')).toBeInTheDocument()
  })

  it('shows tabs', async () => {
    renderPage()
    expect(await screen.findByText('Aktive Services')).toBeInTheDocument()
    expect(screen.getByText('Subscriptions')).toBeInTheDocument()
  })

  it('shows resource in active tab', async () => {
    renderPage()
    expect(await screen.findByText('Linux VM Production')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — verify FAIL**
- [ ] **Step 3: Implement**

MyServices page with tabs using existing hooks `useOrders` pattern for resources and `useSubscriptions` for subscriptions. The "Aktive Services" tab shows resources from `resourcesApi.listResources`, the "Subscriptions" tab shows subscriptions from `subscriptionsApi.list`. Each item rendered as a card with name, template, status badge.

- [ ] **Step 4: Run test — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/MyServices.tsx frontend/tests/pages/MyServices.test.tsx
git commit -m "feat(frontend): add MyServices page combining Resources and Subscriptions"
```

---

### Task 2: MyRequests Page

**Files:**
- Create: `frontend/src/pages/MyRequests.tsx`
- Create: `frontend/tests/pages/MyRequests.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/tests/pages/MyRequests.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import MyRequests from '../../src/pages/MyRequests'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/orders', () => ({
  ordersApi: {
    listOrders: vi.fn().mockResolvedValue({
      items: [
        { id: 'o1', order_number: 'ORD-2026-00001', status: 'draft', title: 'VM Order',
          item_count: 2, created_at: '2026-01-15', updated_at: '2026-01-15' },
      ],
      total: 1, limit: 20, offset: 0,
    }),
  },
}))

vi.mock('../../src/api/approvals', () => ({
  approvalsApi: {
    listPendingApprovals: vi.fn().mockResolvedValue({ items: [] }),
  },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <MyRequests />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('MyRequests', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'test-requester', display_name: 'Test', email: 't@t', roles: ['requester'] },
    })
  })

  it('renders heading', async () => {
    renderPage()
    expect(await screen.findByText('My Requests')).toBeInTheDocument()
  })

  it('shows order tabs', async () => {
    renderPage()
    expect(await screen.findByText('Meine Bestellungen')).toBeInTheDocument()
    expect(screen.getByText('Meine Genehmigungen')).toBeInTheDocument()
  })

  it('shows order in list', async () => {
    renderPage()
    expect(await screen.findByText('ORD-2026-00001')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — verify FAIL**
- [ ] **Step 3: Implement**

MyRequests page with two tabs. "Meine Bestellungen" reuses `useOrders` hook and renders order list with number, title, status badge, link to detail. "Meine Genehmigungen" uses existing approvals API to show decided-by-me approvals.

- [ ] **Step 4: Run test — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/MyRequests.tsx frontend/tests/pages/MyRequests.test.tsx
git commit -m "feat(frontend): add MyRequests page combining Orders and Approvals"
```

---

### Task 3: Improve Review Requests (Approvals Page)

**Files:**
- Rewrite: `frontend/src/pages/Approvals.tsx`
- Rewrite: `frontend/tests/pages/Approvals.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/tests/pages/Approvals.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Approvals from '../../src/pages/Approvals'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/approvals', () => ({
  approvalsApi: {
    listPendingApprovals: vi.fn().mockResolvedValue({
      items: [
        { id: 'a1', order_id: 'o1', status: 'pending', approval_rule_ids: ['r1'],
          requested_at: '2026-01-15T10:00:00Z', deadline_at: '2026-01-22T10:00:00Z',
          decided_by: null, decided_at: null, decision_reason: null,
          order_title: 'Linux VM Bestellung', requester_name: 'test-requester',
          estimated_cost: 85 },
        { id: 'a2', order_id: 'o2', status: 'pending', approval_rule_ids: ['r2'],
          requested_at: '2026-01-16T10:00:00Z', deadline_at: '2026-01-23T10:00:00Z',
          decided_by: null, decided_at: null, decision_reason: null,
          order_title: 'DB Setup', requester_name: 'test-requester',
          estimated_cost: 45 },
      ],
    }),
    approve: vi.fn().mockResolvedValue({}),
    reject: vi.fn().mockResolvedValue({}),
  },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Approvals />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Approvals (Review Requests)', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'test-approver', display_name: 'Approver', email: 'a@t', roles: ['approver'] },
    })
  })

  it('renders heading', async () => {
    renderPage()
    expect(await screen.findByText('Review Requests')).toBeInTheDocument()
  })

  it('shows approval entries with order titles', async () => {
    renderPage()
    expect(await screen.findByText('Linux VM Bestellung')).toBeInTheDocument()
    expect(screen.getByText('DB Setup')).toBeInTheDocument()
  })

  it('shows bulk action buttons', async () => {
    renderPage()
    expect(await screen.findByText('Ausgewählte genehmigen')).toBeInTheDocument()
    expect(screen.getByText('Ausgewählte ablehnen')).toBeInTheDocument()
  })

  it('shows select-all checkbox', async () => {
    renderPage()
    expect(await screen.findByTestId('select-all')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — verify FAIL**
- [ ] **Step 3: Implement**

Rewrite Approvals page with:
- Status filter tabs (Pending/Approved/Rejected/Alle)
- Each approval shows: order title, requester, estimated cost, deadline with color indicator
- Expandable detail section per approval
- Checkbox per pending approval + "Alle auswählen" checkbox
- "Ausgewählte genehmigen" / "Ausgewählte ablehnen" bulk buttons
- Bulk approve calls individual approve endpoints in sequence
- Bulk reject opens reason dialog, then calls reject endpoints

- [ ] **Step 4: Run test — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Approvals.tsx frontend/tests/pages/Approvals.test.tsx
git commit -m "feat(frontend): improve Review Requests with details, filters, and bulk actions"
```

---

### Task 4: Routes + Sidebar Updates

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout/Sidebar.tsx`

- [ ] **Step 1: Update App.tsx**

Add imports for MyServices and MyRequests. Add routes:
```tsx
<Route path="/my-services" element={<MyServices />} />
<Route path="/my-requests" element={<MyRequests />} />
```

Add redirects:
```tsx
<Route path="/subscriptions" element={<Navigate to="/my-services?tab=subscriptions" replace />} />
<Route path="/orders" element={<Navigate to="/my-requests?tab=orders" replace />} />
```

Remove old direct routes for Resources and OrderList (replaced by MyServices and MyRequests).

Keep order detail routes: `/orders/new`, `/orders/:orderId`, `/orders/:orderId/export` unchanged.

- [ ] **Step 2: Update Sidebar**

Change nav items:
- "My Services" stays at `/my-services`
- Remove "Subscriptions" item entirely
- Change "Meine Bestellungen" → label "My Requests", route `/my-requests`

- [ ] **Step 3: Run all frontend tests**
- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Layout/Sidebar.tsx
git commit -m "feat(frontend): update routes and sidebar for MyServices, MyRequests, remove Subscriptions menu"
```

---

### Task 5: Final Verification

- [ ] **Step 1: Run frontend tests**

Run: `cd frontend && npx vitest run`

- [ ] **Step 2: Type check**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Commit if needed**

```bash
git commit -m "chore: My Services, My Requests, Review Requests improvements complete"
```
