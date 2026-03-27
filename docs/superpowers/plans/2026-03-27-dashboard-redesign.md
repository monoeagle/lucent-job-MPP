# Dashboard Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Role-based dashboard with stat cards, recent orders, charts (recharts), popular services, pending approvals, and global search — replacing the current placeholder page.

**Architecture:** Two new backend endpoints (search + stats) using existing repositories with aggregation queries. Frontend dashboard page composed of isolated widget components, each with its own data hook. recharts for Donut and Line charts. Global search with debounced input and grouped dropdown results.

**Tech Stack:** Python/Flask, SQLAlchemy (backend). React 19, TypeScript, TailwindCSS 4, recharts, tanstack-query (frontend).

**Spec:** `docs/superpowers/specs/2026-03-27-dashboard-redesign.md`

---

## File Structure

### Backend
```
app/api/v1/
├── dashboard.py          # NEW: GET /api/v1/dashboard/stats
└── search.py             # NEW: GET /api/v1/search

tests/integration/
├── test_dashboard_api.py # NEW
└── test_search_api.py    # NEW
```

### Frontend
```
frontend/src/
├── api/
│   └── dashboard.ts                    # NEW: API client for stats + search
├── hooks/
│   └── useDashboard.ts                 # NEW: useStats, useSearch hooks
├── components/dashboard/
│   ├── StatCard.tsx                     # NEW: single stat tile
│   ├── RecentOrders.tsx                 # NEW: latest 5 orders list
│   ├── OrderStatusChart.tsx            # NEW: recharts PieChart (donut)
│   ├── OrderTimelineChart.tsx          # NEW: recharts LineChart
│   ├── PopularServices.tsx             # NEW: top 5 templates list
│   ├── PendingApprovals.tsx            # NEW: approver widget
│   └── GlobalSearch.tsx                # NEW: search input + dropdown
└── pages/
    └── Dashboard.tsx                   # REWRITE

frontend/tests/
├── components/dashboard/
│   └── StatCard.test.tsx               # NEW
└── pages/
    └── Dashboard.test.tsx              # REWRITE
```

---

### Task 1: Backend — Dashboard Stats Endpoint

**Files:**
- Create: `app/api/v1/dashboard.py`
- Modify: `app/__init__.py`
- Test: `tests/integration/test_dashboard_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_dashboard_api.py
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.order_repository import OrderRepository
from app.data.repositories.template_repository import TemplateRepository


@pytest.fixture
def db_session(app):
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def seed_data(db_session):
    tmpl_repo = TemplateRepository(db_session)
    tmpl_repo.create({
        "slug": "vm-linux", "version": "1.0.0", "type": "vm",
        "display_name": "Linux VM", "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "cpu", "display_order": 1, "constraints": {"min": 1, "max": 64}},
        ],
    })

    order_repo = OrderRepository(db_session)
    o1 = order_repo.create_order("test-requester", "Order 1", "Reason")
    order_repo.add_item(o1.id, "vm-linux", "1.0.0", "Linux VM", {"cpu": 4})
    o2 = order_repo.create_order("test-requester", "Order 2", "Reason")
    order_repo.add_item(o2.id, "vm-linux", "1.0.0", "Linux VM", {"cpu": 8})
    order_repo.update_order_status(o2.id, "validated")
    order_repo.update_order_status(o2.id, "submitted")
    return {"orders": [o1, o2]}


class TestDashboardStats:
    def test_stats_returns_200(self, client, db_session, seed_data, requester_headers):
        resp = client.get("/api/v1/dashboard/stats", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "orders_by_status" in data
        assert "orders_by_month" in data
        assert "total_templates" in data
        assert "popular_templates" in data
        assert "pending_approvals" in data
        assert "active_resources" in data

    def test_stats_counts_orders_by_status(self, client, db_session, seed_data, requester_headers):
        resp = client.get("/api/v1/dashboard/stats", headers=requester_headers)
        data = resp.get_json()
        assert data["orders_by_status"]["draft"] == 1
        assert data["orders_by_status"]["submitted"] == 1

    def test_stats_counts_templates(self, client, db_session, seed_data, requester_headers):
        resp = client.get("/api/v1/dashboard/stats", headers=requester_headers)
        data = resp.get_json()
        assert data["total_templates"] >= 1

    def test_stats_popular_templates(self, client, db_session, seed_data, requester_headers):
        resp = client.get("/api/v1/dashboard/stats", headers=requester_headers)
        data = resp.get_json()
        assert len(data["popular_templates"]) >= 1
        assert data["popular_templates"][0]["slug"] == "vm-linux"
        assert data["popular_templates"][0]["order_count"] >= 2

    def test_stats_unauthenticated_returns_401(self, client, db_session):
        resp = client.get("/api/v1/dashboard/stats")
        assert resp.status_code == 401
```

- [ ] **Step 2: Run tests — verify FAIL**

Run: `source venv/bin/activate && DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_test pytest tests/integration/test_dashboard_api.py -v --tb=short`

- [ ] **Step 3: Implement**

```python
# app/api/v1/dashboard.py
from flask import Blueprint, jsonify, g
from sqlalchemy import func, extract

from app.core.auth import login_required
from app.data.db.models.order import OrderModel, OrderItemModel
from app.data.db.models.service_template import ServiceTemplateModel

bp = Blueprint("dashboard", __name__, url_prefix="/api/v1/dashboard")


@bp.route("/stats", methods=["GET"])
@login_required
def get_stats():
    session = g.db_session
    user = g.current_user

    # Orders by status (user sees own, admin sees all)
    q = session.query(OrderModel.status, func.count(OrderModel.id))
    if not user.is_admin:
        q = q.filter(OrderModel.requester_id == user.username)
    rows = q.group_by(OrderModel.status).all()
    orders_by_status = {status: count for status, count in rows}

    # Orders by month (last 6 months)
    q = session.query(
        func.to_char(OrderModel.created_at, 'YYYY-MM').label('month'),
        func.count(OrderModel.id),
    )
    if not user.is_admin:
        q = q.filter(OrderModel.requester_id == user.username)
    rows = q.group_by('month').order_by('month').limit(6).all()
    orders_by_month = [{"month": m, "count": c} for m, c in rows]

    # Total templates
    total_templates = session.query(func.count(ServiceTemplateModel.id)).scalar() or 0

    # Active resources (count of items in done orders)
    rq = session.query(func.count(OrderItemModel.id)).join(
        OrderModel, OrderItemModel.order_id == OrderModel.id
    ).filter(OrderModel.status == "done")
    if not user.is_admin:
        rq = rq.filter(OrderModel.requester_id == user.username)
    active_resources = rq.scalar() or 0

    # Pending approvals
    from app.data.db.models.approval import ApprovalRequestModel
    pq = session.query(func.count(ApprovalRequestModel.id)).filter(
        ApprovalRequestModel.status == "pending"
    )
    pending_approvals = pq.scalar() or 0

    # Popular templates (top 5 by order count)
    pop = session.query(
        OrderItemModel.template_slug,
        func.count(OrderItemModel.id).label('cnt'),
    ).group_by(OrderItemModel.template_slug).order_by(func.count(OrderItemModel.id).desc()).limit(5).all()

    popular_templates = []
    for slug, cnt in pop:
        tmpl = session.query(ServiceTemplateModel).filter_by(slug=slug).first()
        popular_templates.append({
            "slug": slug,
            "display_name": tmpl.display_name if tmpl else slug,
            "category": tmpl.category if tmpl else "",
            "order_count": cnt,
        })

    return jsonify({
        "orders_by_status": orders_by_status,
        "orders_by_month": orders_by_month,
        "total_templates": total_templates,
        "active_resources": active_resources,
        "pending_approvals": pending_approvals,
        "popular_templates": popular_templates,
    }), 200
```

Register blueprint in `app/__init__.py` — add after the notifications block:
```python
    from app.api.v1 import dashboard
    app.register_blueprint(dashboard.bp)
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add app/api/v1/dashboard.py app/__init__.py tests/integration/test_dashboard_api.py
git commit -m "feat: add dashboard stats API endpoint"
```

---

### Task 2: Backend — Search Endpoint

**Files:**
- Create: `app/api/v1/search.py`
- Modify: `app/__init__.py`
- Test: `tests/integration/test_search_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_search_api.py
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.order_repository import OrderRepository
from app.data.repositories.template_repository import TemplateRepository


@pytest.fixture
def db_session(app):
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def seed_data(db_session):
    tmpl_repo = TemplateRepository(db_session)
    tmpl_repo.create({
        "slug": "vm-linux", "version": "1.0.0", "type": "vm",
        "display_name": "Linux VM", "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "cpu", "display_order": 1, "constraints": {"min": 1, "max": 64}},
        ],
    })
    tmpl_repo.create({
        "slug": "db-postgres", "version": "1.0.0", "type": "database",
        "display_name": "PostgreSQL DB", "category": "Database",
        "tofu_module_source": "git::https://gitlab.internal/tofu/db.git",
        "parameters": [
            {"key": "storage", "label": "Storage", "type": "integer", "required": True,
             "tofu_variable_name": "storage", "display_order": 1, "constraints": {"min": 10, "max": 1000}},
        ],
    })
    order_repo = OrderRepository(db_session)
    order_repo.create_order("test-requester", "Linux VM Bestellung", "Need it")
    order_repo.create_order("test-requester", "Database Setup", "DB needed")


class TestSearch:
    def test_search_finds_templates(self, client, db_session, seed_data, requester_headers):
        resp = client.get("/api/v1/search?q=linux", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["templates"]) >= 1
        assert data["templates"][0]["slug"] == "vm-linux"

    def test_search_finds_orders(self, client, db_session, seed_data, requester_headers):
        resp = client.get("/api/v1/search?q=Database", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["orders"]) >= 1
        assert "Database" in data["orders"][0]["title"]

    def test_search_empty_query_returns_empty(self, client, db_session, seed_data, requester_headers):
        resp = client.get("/api/v1/search?q=", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["orders"] == []
        assert data["templates"] == []

    def test_search_no_results(self, client, db_session, seed_data, requester_headers):
        resp = client.get("/api/v1/search?q=zzzzzznotfound", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["orders"] == []
        assert data["templates"] == []

    def test_search_unauthenticated_returns_401(self, client, db_session):
        resp = client.get("/api/v1/search?q=test")
        assert resp.status_code == 401
```

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement**

```python
# app/api/v1/search.py
from flask import Blueprint, jsonify, request, g

from app.core.auth import login_required
from app.data.db.models.order import OrderModel
from app.data.db.models.service_template import ServiceTemplateModel

bp = Blueprint("search", __name__, url_prefix="/api/v1")


@bp.route("/search", methods=["GET"])
@login_required
def global_search():
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", 5, type=int)

    if len(q) < 1:
        return jsonify({"query": q, "orders": [], "templates": [], "resources": []}), 200

    session = g.db_session
    user = g.current_user
    pattern = f"%{q}%"

    # Search orders (title + order_number)
    oq = session.query(OrderModel).filter(
        (OrderModel.title.ilike(pattern)) | (OrderModel.order_number.ilike(pattern))
    )
    if not user.is_admin:
        oq = oq.filter(OrderModel.requester_id == user.username)
    orders = oq.order_by(OrderModel.created_at.desc()).limit(limit).all()

    # Search templates (display_name + slug)
    tq = session.query(ServiceTemplateModel).filter(
        (ServiceTemplateModel.display_name.ilike(pattern)) | (ServiceTemplateModel.slug.ilike(pattern))
    ).filter(ServiceTemplateModel.status.in_(["active", "deprecated"]))
    templates = tq.limit(limit).all()

    return jsonify({
        "query": q,
        "orders": [
            {"id": o.id, "order_number": o.order_number, "title": o.title, "status": o.status}
            for o in orders
        ],
        "templates": [
            {"slug": t.slug, "display_name": t.display_name, "category": t.category, "status": t.status}
            for t in templates
        ],
        "resources": [],
    }), 200
```

Register in `app/__init__.py` after dashboard:
```python
    from app.api.v1 import search
    app.register_blueprint(search.bp)
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add app/api/v1/search.py app/__init__.py tests/integration/test_search_api.py
git commit -m "feat: add global search API endpoint"
```

---

### Task 3: Frontend — Install recharts + API Client + Hooks

**Files:**
- Create: `frontend/src/api/dashboard.ts`
- Create: `frontend/src/hooks/useDashboard.ts`

- [ ] **Step 1: Install recharts**

Run: `cd frontend && npm install recharts`

- [ ] **Step 2: Create API client**

```typescript
// frontend/src/api/dashboard.ts
import { apiClient } from './client'

export interface DashboardStats {
  orders_by_status: Record<string, number>
  orders_by_month: Array<{ month: string; count: number }>
  total_templates: number
  active_resources: number
  pending_approvals: number
  popular_templates: Array<{
    slug: string
    display_name: string
    category: string
    order_count: number
  }>
}

export interface SearchResult {
  query: string
  orders: Array<{ id: string; order_number: string; title: string; status: string }>
  templates: Array<{ slug: string; display_name: string; category: string; status: string }>
  resources: Array<{ id: string; display_name: string; template_slug: string }>
}

export const dashboardApi = {
  async getStats(token: string): Promise<DashboardStats> {
    return (await apiClient.get('/api/v1/dashboard/stats', token)) as DashboardStats
  },

  async search(token: string, query: string, limit = 5): Promise<SearchResult> {
    return (await apiClient.get(`/api/v1/search?q=${encodeURIComponent(query)}&limit=${limit}`, token)) as SearchResult
  },
}
```

- [ ] **Step 3: Create hooks**

```typescript
// frontend/src/hooks/useDashboard.ts
import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../api/dashboard'
import { useAuthStore } from '../store/authStore'

export function useStats() {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => dashboardApi.getStats(token!),
    enabled: !!token,
    staleTime: 60_000,
  })
}

export function useSearch(query: string) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['search', query],
    queryFn: () => dashboardApi.search(token!, query),
    enabled: !!token && query.length >= 2,
    staleTime: 10_000,
  })
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/dashboard.ts frontend/src/hooks/useDashboard.ts frontend/package.json frontend/package-lock.json
git commit -m "feat(frontend): add recharts, dashboard API client and hooks"
```

---

### Task 4: Frontend — StatCard + GlobalSearch Components

**Files:**
- Create: `frontend/src/components/dashboard/StatCard.tsx`
- Create: `frontend/src/components/dashboard/GlobalSearch.tsx`
- Create: `frontend/tests/components/dashboard/StatCard.test.tsx`

- [ ] **Step 1: Write failing test for StatCard**

```tsx
// frontend/tests/components/dashboard/StatCard.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import StatCard from '../../../src/components/dashboard/StatCard'

describe('StatCard', () => {
  it('renders label and value', () => {
    render(<StatCard label="Offene Orders" value={3} />)
    expect(screen.getByText('Offene Orders')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('renders zero value', () => {
    render(<StatCard label="Pending" value={0} />)
    expect(screen.getByText('0')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — verify FAIL**
- [ ] **Step 3: Implement StatCard**

```tsx
// frontend/src/components/dashboard/StatCard.tsx
interface Props {
  label: string
  value: number
  color?: string
}

export default function StatCard({ label, value, color = 'text-blue-600' }: Props) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
      <p className="text-sm text-gray-500 mt-1">{label}</p>
    </div>
  )
}
```

- [ ] **Step 4: Implement GlobalSearch**

```tsx
// frontend/src/components/dashboard/GlobalSearch.tsx
import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSearch } from '../../hooks/useDashboard'

export default function GlobalSearch() {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const { data: results } = useSearch(debouncedQuery)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300)
    return () => clearTimeout(timer)
  }, [query])

  useEffect(() => {
    setOpen(debouncedQuery.length >= 2 && !!results)
  }, [debouncedQuery, results])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (type: string, id: string) => {
    setOpen(false)
    setQuery('')
    if (type === 'order') navigate(`/orders/${id}`)
    else if (type === 'template') navigate(`/shop/${id}/request`)
    else navigate('/my-services')
  }

  const hasResults = results && (results.orders.length > 0 || results.templates.length > 0)

  return (
    <div ref={ref} className="relative w-80">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
        placeholder="Suche..."
        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
        data-testid="global-search"
      />
      {open && results && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-80 overflow-auto">
          {!hasResults && (
            <p className="p-3 text-sm text-gray-400">Keine Ergebnisse</p>
          )}
          {results.orders.length > 0 && (
            <div>
              <p className="px-3 pt-2 text-xs font-semibold text-gray-400 uppercase">Orders</p>
              {results.orders.map((o) => (
                <button key={o.id} onClick={() => handleSelect('order', o.id)}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50">
                  {o.order_number} — {o.title}
                </button>
              ))}
            </div>
          )}
          {results.templates.length > 0 && (
            <div>
              <p className="px-3 pt-2 text-xs font-semibold text-gray-400 uppercase">Services</p>
              {results.templates.map((t) => (
                <button key={t.slug} onClick={() => handleSelect('template', t.slug)}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50">
                  {t.display_name} <span className="text-gray-400">({t.category})</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Run tests — verify PASS**
- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/dashboard/StatCard.tsx frontend/src/components/dashboard/GlobalSearch.tsx frontend/tests/components/dashboard/StatCard.test.tsx
git commit -m "feat(frontend): add StatCard and GlobalSearch components"
```

---

### Task 5: Frontend — Chart Components

**Files:**
- Create: `frontend/src/components/dashboard/OrderStatusChart.tsx`
- Create: `frontend/src/components/dashboard/OrderTimelineChart.tsx`

- [ ] **Step 1: Implement OrderStatusChart**

```tsx
// frontend/src/components/dashboard/OrderStatusChart.tsx
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

const STATUS_COLORS: Record<string, string> = {
  draft: '#9CA3AF',
  submitted: '#3B82F6',
  pending_approval: '#F59E0B',
  provisioning: '#8B5CF6',
  done: '#10B981',
  failed: '#EF4444',
}

interface Props {
  data: Record<string, number>
}

export default function OrderStatusChart({ data }: Props) {
  const chartData = Object.entries(data)
    .filter(([, count]) => count > 0)
    .map(([status, count]) => ({ name: status, value: count }))

  if (chartData.length === 0) {
    return <p className="text-sm text-gray-400">Keine Orders vorhanden</p>
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Orders nach Status</h3>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie data={chartData} dataKey="value" nameKey="name" cx="50%" cy="50%"
            innerRadius={50} outerRadius={80} paddingAngle={2}>
            {chartData.map((entry) => (
              <Cell key={entry.name} fill={STATUS_COLORS[entry.name] ?? '#6B7280'} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Step 2: Implement OrderTimelineChart**

```tsx
// frontend/src/components/dashboard/OrderTimelineChart.tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

interface Props {
  data: Array<{ month: string; count: number }>
}

export default function OrderTimelineChart({ data }: Props) {
  if (data.length === 0) {
    return <p className="text-sm text-gray-400">Keine Daten vorhanden</p>
  }

  const formatted = data.map((d) => ({
    ...d,
    label: d.month.slice(5),
  }))

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Orders ueber Zeit</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={formatted}>
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Line type="monotone" dataKey="count" stroke="#3B82F6" strokeWidth={2} dot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/OrderStatusChart.tsx frontend/src/components/dashboard/OrderTimelineChart.tsx
git commit -m "feat(frontend): add OrderStatusChart (donut) and OrderTimelineChart (line) with recharts"
```

---

### Task 6: Frontend — List Widgets

**Files:**
- Create: `frontend/src/components/dashboard/RecentOrders.tsx`
- Create: `frontend/src/components/dashboard/PopularServices.tsx`
- Create: `frontend/src/components/dashboard/PendingApprovals.tsx`

- [ ] **Step 1: Implement RecentOrders**

```tsx
// frontend/src/components/dashboard/RecentOrders.tsx
import { Link } from 'react-router-dom'
import { useOrders } from '../../hooks/useOrders'
import StatusBadge from '../StatusBadge'

export default function RecentOrders() {
  const { data } = useOrders({ limit: 5 })
  const orders = data?.items ?? []

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Letzte Bestellungen</h3>
      {orders.length === 0 ? (
        <p className="text-sm text-gray-400">Keine Bestellungen</p>
      ) : (
        <div className="space-y-2">
          {orders.map((o) => (
            <Link key={o.id} to={`/orders/${o.id}`}
              className="flex items-center justify-between text-sm hover:bg-gray-50 rounded px-2 py-1 -mx-2">
              <div>
                <span className="font-medium">{o.order_number}</span>
                <span className="text-gray-400 ml-2">{o.title}</span>
              </div>
              <StatusBadge status={o.status} />
            </Link>
          ))}
          <Link to="/orders" className="text-xs text-blue-600 hover:text-blue-800">
            Alle anzeigen →
          </Link>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Implement PopularServices**

```tsx
// frontend/src/components/dashboard/PopularServices.tsx
import { Link } from 'react-router-dom'
import type { DashboardStats } from '../../api/dashboard'

interface Props {
  templates: DashboardStats['popular_templates']
}

export default function PopularServices({ templates }: Props) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Beliebte Services</h3>
      {templates.length === 0 ? (
        <p className="text-sm text-gray-400">Keine Services bestellt</p>
      ) : (
        <div className="space-y-2">
          {templates.map((t) => (
            <div key={t.slug} className="flex items-center justify-between text-sm">
              <div>
                <span className="font-medium">{t.display_name}</span>
                <span className="text-xs text-gray-400 ml-2">{t.category}</span>
              </div>
              <Link to={`/shop/${t.slug}/request`}
                className="text-xs text-blue-600 hover:text-blue-800">
                Bestellen
              </Link>
            </div>
          ))}
          <Link to="/shop" className="text-xs text-blue-600 hover:text-blue-800">
            Zum Shop →
          </Link>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Implement PendingApprovals**

```tsx
// frontend/src/components/dashboard/PendingApprovals.tsx
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../../store/authStore'
import { approvalsApi } from '../../api/approvals'

export default function PendingApprovals() {
  const token = useAuthStore((s) => s.token)
  const { data } = useQuery({
    queryKey: ['pending-approvals-dashboard'],
    queryFn: () => approvalsApi.listPendingApprovals(token!),
    enabled: !!token,
  })
  const items = data?.items ?? []

  if (items.length === 0) return null

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Ausstehende Genehmigungen</h3>
      <div className="space-y-2">
        {items.slice(0, 5).map((a) => (
          <Link key={a.id} to="/reviews"
            className="flex items-center justify-between text-sm hover:bg-gray-50 rounded px-2 py-1 -mx-2">
            <span>Order {a.order_id.slice(0, 8)}...</span>
            <span className="text-xs text-yellow-600">Ausstehend</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dashboard/RecentOrders.tsx frontend/src/components/dashboard/PopularServices.tsx frontend/src/components/dashboard/PendingApprovals.tsx
git commit -m "feat(frontend): add RecentOrders, PopularServices, PendingApprovals widgets"
```

---

### Task 7: Frontend — Dashboard Page Rewrite

**Files:**
- Rewrite: `frontend/src/pages/Dashboard.tsx`
- Rewrite: `frontend/tests/pages/Dashboard.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/tests/pages/Dashboard.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Dashboard from '../../src/pages/Dashboard'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/dashboard', () => ({
  dashboardApi: {
    getStats: vi.fn().mockResolvedValue({
      orders_by_status: { draft: 3, submitted: 1, done: 7 },
      orders_by_month: [{ month: '2026-01', count: 5 }],
      total_templates: 12,
      active_resources: 7,
      pending_approvals: 2,
      popular_templates: [
        { slug: 'vm-linux', display_name: 'Linux VM', category: 'Compute', order_count: 15 },
      ],
    }),
    search: vi.fn().mockResolvedValue({ query: '', orders: [], templates: [], resources: [] }),
  },
}))

vi.mock('../../src/api/orders', () => ({
  ordersApi: {
    listOrders: vi.fn().mockResolvedValue({
      items: [
        { id: 'o1', order_number: 'ORD-2026-00001', status: 'draft', title: 'Test Order',
          item_count: 1, created_at: '2026-01-01', updated_at: '2026-01-01' },
      ],
      total: 1, limit: 5, offset: 0,
    }),
  },
}))

vi.mock('../../src/api/approvals', () => ({
  approvalsApi: {
    listPendingApprovals: vi.fn().mockResolvedValue({ items: [] }),
  },
}))

function renderDashboard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Dashboard', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'test-user', display_name: 'Test User', email: 'test@test.com', roles: ['requester'] },
    })
  })

  it('renders dashboard title', async () => {
    renderDashboard()
    expect(await screen.findByText('Dashboard')).toBeInTheDocument()
  })

  it('renders stat cards', async () => {
    renderDashboard()
    expect(await screen.findByText('Offene Orders')).toBeInTheDocument()
    expect(await screen.findByText('Templates')).toBeInTheDocument()
  })

  it('renders search field', async () => {
    renderDashboard()
    expect(await screen.findByTestId('global-search')).toBeInTheDocument()
  })

  it('renders recent orders', async () => {
    renderDashboard()
    expect(await screen.findByText('Letzte Bestellungen')).toBeInTheDocument()
  })

  it('renders popular services', async () => {
    renderDashboard()
    expect(await screen.findByText('Beliebte Services')).toBeInTheDocument()
    expect(await screen.findByText('Linux VM')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — verify FAIL**
- [ ] **Step 3: Implement Dashboard**

```tsx
// frontend/src/pages/Dashboard.tsx
import { useAuthStore } from '../store/authStore'
import { useStats } from '../hooks/useDashboard'
import StatCard from '../components/dashboard/StatCard'
import GlobalSearch from '../components/dashboard/GlobalSearch'
import RecentOrders from '../components/dashboard/RecentOrders'
import OrderStatusChart from '../components/dashboard/OrderStatusChart'
import OrderTimelineChart from '../components/dashboard/OrderTimelineChart'
import PopularServices from '../components/dashboard/PopularServices'
import PendingApprovals from '../components/dashboard/PendingApprovals'

export default function Dashboard() {
  const user = useAuthStore((s) => s.user)
  const { data: stats, isLoading } = useStats()

  const isApprover = user?.roles.includes('approver') || user?.roles.includes('admin')
  const openOrders = (stats?.orders_by_status?.draft ?? 0) + (stats?.orders_by_status?.submitted ?? 0)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <GlobalSearch />
      </div>

      {isLoading ? (
        <p className="text-gray-500">Lade Dashboard...</p>
      ) : stats ? (
        <div className="space-y-6">
          {/* Stat Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard label="Offene Orders" value={openOrders} />
            <StatCard label="Ausstehende Genehmigungen" value={stats.pending_approvals} color="text-yellow-600" />
            <StatCard label="Aktive Services" value={stats.active_resources} color="text-green-600" />
            <StatCard label="Templates" value={stats.total_templates} color="text-gray-600" />
          </div>

          {/* Charts + Lists */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <RecentOrders />
            <OrderStatusChart data={stats.orders_by_status} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <PopularServices templates={stats.popular_templates} />
            <OrderTimelineChart data={stats.orders_by_month} />
          </div>

          {/* Role-specific */}
          {isApprover && <PendingApprovals />}
        </div>
      ) : null}
    </div>
  )
}
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/tests/pages/Dashboard.test.tsx
git commit -m "feat(frontend): rewrite Dashboard with stat cards, charts, search, role-based widgets"
```

---

### Task 8: Final Verification

- [ ] **Step 1: Run full frontend test suite**

Run: `cd frontend && npx vitest run`

- [ ] **Step 2: Type check**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Run backend tests**

Run: `source venv/bin/activate && DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_test pytest tests/ -q`

- [ ] **Step 4: Final commit**

```bash
git commit -m "chore: dashboard redesign complete — stats, search, charts, role-based widgets"
```
