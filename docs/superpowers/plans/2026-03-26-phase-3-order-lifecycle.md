# Phase 3: Order Lifecycle + JSON Export — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Order Lifecycle with multi-service CRUD, parameter validation against catalog templates, order submission with status machine, and JSON export for OpenTofu provisioning.

**Architecture:** Order and OrderItem as SQLAlchemy models with JSONB for parameters. OrderService handles business logic (validation, status transitions, export). Endpoints in a new orders blueprint. SSE deferred to a later task (stub endpoint now).

**Tech Stack:** Flask, SQLAlchemy, PostgreSQL (JSONB), Alembic, pytest

**Spec:** `docs/specs/order-lifecycle.md` — REQ-126 to REQ-172, VAL-71 to VAL-97, EC-81 to EC-107, Endpoints 45-59

---

## File Structure (new/modified)

```
app/
├── domain/
│   └── order.py                    # OrderStatus enum, OrderItem validation state
├── data/
│   ├── db/models/
│   │   ├── order.py                # OrderModel + OrderItemModel
│   │   └── __init__.py             # updated imports
│   └── repositories/
│       └── order_repository.py     # Order CRUD + query
├── services/
│   └── order_service.py            # Business logic: create, validate, submit, export
└── api/v1/
    └── orders.py                   # Blueprint: 15 endpoints

tests/
├── unit/
│   ├── test_order_domain.py
│   └── test_order_service.py
└── integration/
    ├── test_order_crud_api.py
    ├── test_order_items_api.py
    ├── test_order_validation_api.py
    ├── test_order_submit_api.py
    └── test_order_export_api.py
```

---

### Task 1: Domain — OrderStatus + Validation State

**Files:**
- Create: `app/domain/order.py`
- Test: `tests/unit/test_order_domain.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_order_domain.py
from app.domain.order import OrderStatus, ItemValidationState


class TestOrderStatus:
    def test_status_values(self):
        assert OrderStatus.DRAFT == "draft"
        assert OrderStatus.VALIDATED == "validated"
        assert OrderStatus.SUBMITTED == "submitted"
        assert OrderStatus.PROVISIONING == "provisioning"
        assert OrderStatus.DONE == "done"
        assert OrderStatus.FAILED == "failed"

    def test_allowed_transitions(self):
        assert OrderStatus.can_transition("draft", "validated") is True
        assert OrderStatus.can_transition("validated", "submitted") is True
        assert OrderStatus.can_transition("validated", "draft") is True
        assert OrderStatus.can_transition("submitted", "provisioning") is True
        assert OrderStatus.can_transition("submitted", "pending_approval") is True
        assert OrderStatus.can_transition("pending_approval", "approved") is True
        assert OrderStatus.can_transition("pending_approval", "rejected") is True
        assert OrderStatus.can_transition("approved", "provisioning") is True
        assert OrderStatus.can_transition("provisioning", "done") is True
        assert OrderStatus.can_transition("provisioning", "failed") is True

    def test_forbidden_transitions(self):
        assert OrderStatus.can_transition("submitted", "draft") is False
        assert OrderStatus.can_transition("done", "draft") is False
        assert OrderStatus.can_transition("failed", "draft") is False
        assert OrderStatus.can_transition("rejected", "draft") is False
        assert OrderStatus.can_transition("done", "failed") is False

    def test_is_terminal(self):
        assert OrderStatus.is_terminal("done") is True
        assert OrderStatus.is_terminal("failed") is True
        assert OrderStatus.is_terminal("rejected") is True
        assert OrderStatus.is_terminal("draft") is False

    def test_is_editable(self):
        assert OrderStatus.is_editable("draft") is True
        assert OrderStatus.is_editable("validated") is False
        assert OrderStatus.is_editable("submitted") is False


class TestItemValidationState:
    def test_states(self):
        assert ItemValidationState.UNCHECKED == "unchecked"
        assert ItemValidationState.VALID == "valid"
        assert ItemValidationState.INVALID == "invalid"
```

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement**

```python
# app/domain/order.py

class OrderStatus:
    DRAFT = "draft"
    VALIDATED = "validated"
    SUBMITTED = "submitted"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROVISIONING = "provisioning"
    DONE = "done"
    FAILED = "failed"

    _TRANSITIONS = {
        "draft": {"validated"},
        "validated": {"submitted", "draft"},
        "submitted": {"provisioning", "pending_approval"},
        "pending_approval": {"approved", "rejected"},
        "approved": {"provisioning"},
        "provisioning": {"done", "failed"},
        "done": set(),
        "failed": set(),
        "rejected": set(),
    }

    _TERMINAL = {"done", "failed", "rejected"}

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        return to_status in cls._TRANSITIONS.get(from_status, set())

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        return status in cls._TERMINAL

    @classmethod
    def is_editable(cls, status: str) -> bool:
        return status == cls.DRAFT


class ItemValidationState:
    UNCHECKED = "unchecked"
    VALID = "valid"
    INVALID = "invalid"
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/domain/order.py tests/unit/test_order_domain.py
git commit -m "feat: add OrderStatus and ItemValidationState domain models"
```

---

### Task 2: Database Models — Order + OrderItem

**Files:**
- Create: `app/data/db/models/order.py`
- Modify: `app/data/db/models/__init__.py`
- Test: `tests/integration/test_order_db_model.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_order_db_model.py
import uuid
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.db.models.order import OrderModel, OrderItemModel


class TestOrderModel:
    def setup_method(self):
        self.engine = get_engine("postgresql://mpp:mpp@localhost:5432/mpp_test")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.Session = get_session_factory(self.engine)

    def teardown_method(self):
        Base.metadata.drop_all(self.engine)

    def test_create_order_with_items(self):
        session = self.Session()
        order = OrderModel(
            id=str(uuid.uuid4()),
            order_number="ORD-2026-00001",
            requester_id=str(uuid.uuid4()),
            status="draft",
            title="Test Order",
            business_reason="Testing",
        )
        item = OrderItemModel(
            id=str(uuid.uuid4()),
            order_id=order.id,
            template_slug="vm-linux",
            template_version="1.0.0",
            display_name="Linux VM",
            parameters={"cpu_cores": 4},
            position=1,
            validation_state="unchecked",
            validation_errors=[],
        )
        session.add(order)
        session.add(item)
        session.commit()

        loaded = session.query(OrderModel).filter_by(id=order.id).first()
        assert loaded is not None
        assert loaded.title == "Test Order"
        assert len(loaded.items) == 1
        assert loaded.items[0].template_slug == "vm-linux"
        session.close()

    def test_order_number_unique(self):
        session = self.Session()
        o1 = OrderModel(id=str(uuid.uuid4()), order_number="ORD-2026-00001",
                        requester_id=str(uuid.uuid4()), status="draft", title="Order 1")
        o2 = OrderModel(id=str(uuid.uuid4()), order_number="ORD-2026-00001",
                        requester_id=str(uuid.uuid4()), status="draft", title="Order 2")
        session.add(o1)
        session.commit()
        session.add(o2)
        import pytest
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            session.commit()
        session.close()
```

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement**

```python
# app/data/db/models/order.py
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, DateTime, Integer, UniqueConstraint, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.data.db.session import Base


class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True)
    order_number = Column(String(20), nullable=False, unique=True)
    requester_id = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    title = Column(String(100), nullable=False)
    business_reason = Column(Text, nullable=True)
    desired_date = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)

    items = relationship("OrderItemModel", back_populates="order",
                         order_by="OrderItemModel.position",
                         cascade="all, delete-orphan")


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    template_slug = Column(String(64), nullable=False)
    template_version = Column(String(32), nullable=False)
    display_name = Column(String(100), nullable=False)
    parameters = Column(JSONB, nullable=False, default=dict)
    position = Column(Integer, nullable=False, default=1)
    validation_state = Column(String(20), nullable=False, default="unchecked")
    validation_errors = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    order = relationship("OrderModel", back_populates="items")

    __table_args__ = (
        Index("ix_order_item_order_position", "order_id", "position"),
    )
```

Update `app/data/db/models/__init__.py`:
```python
from app.data.db.models.service_template import ServiceTemplateModel
from app.data.db.models.order import OrderModel, OrderItemModel
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Create Alembic migration**

Run: `alembic revision --autogenerate -m "add orders and order_items tables"`
Run: `alembic upgrade head`

- [ ] **Step 6: Run ALL tests, commit**

```bash
git add app/data/db/models/ migrations/ tests/integration/test_order_db_model.py
git commit -m "feat: add Order and OrderItem database models with cascade delete"
```

---

### Task 3: Order Repository

**Files:**
- Create: `app/data/repositories/order_repository.py`
- Test: `tests/integration/test_order_repository.py`

- [ ] **Step 1: Write failing tests** covering:
- create_order(requester_id, title, business_reason, desired_date) → returns OrderModel with generated id + order_number
- get_by_id(id) → returns order with items
- list_orders(requester_id, status_filter, limit, offset) → paginated
- list_orders for admin (no requester_id filter)
- update_order(id, fields) → updates title/business_reason/desired_date
- delete_order(id) → deletes order + cascade items
- add_item(order_id, template_slug, template_version, display_name, parameters) → returns item
- update_item_parameters(item_id, parameters) → updates params, resets validation_state
- remove_item(item_id) → deletes item
- update_order_status(id, new_status) → transitions status

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement OrderRepository**

Key design decisions:
- `order_number` is auto-generated as `ORD-{year}-{seq:05d}` using a DB sequence or max+1
- All methods that modify an order also update `updated_at`
- `update_item_parameters` resets `validation_state` to "unchecked"
- Status transitions should be validated before calling (service layer responsibility)

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/data/repositories/order_repository.py tests/integration/test_order_repository.py
git commit -m "feat: add OrderRepository with CRUD, items management, and status transitions"
```

---

### Task 4: Order Service — Business Logic

**Files:**
- Create: `app/services/order_service.py`
- Test: `tests/unit/test_order_service.py`

- [ ] **Step 1: Write failing tests** covering:
- create_order → validates title, creates via repo
- add_item → checks order is draft, validates template exists and is active/deprecated, creates item
- update_item → checks order is draft, resets validation, resets order to draft if validated
- remove_item → checks order is draft
- validate_order → validates all items against catalog, sets validation states, transitions to validated if all valid
- submit_order → checks status is validated, business_reason present, transitions to submitted
- export_order_tofu → generates JSON with tofu_variable_name mapping, skips inactive depends_on params

Unit tests with mocked repositories.

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement OrderService**

Key methods:
- `create_order(requester_id, title, business_reason, desired_date)`
- `add_item(order_id, requester_id, template_slug, template_version, parameters)`
- `update_item(order_id, item_id, requester_id, parameters)`
- `remove_item(order_id, item_id, requester_id)`
- `validate_order(order_id, requester_id)` — uses CatalogService for validation
- `submit_order(order_id, requester_id)`
- `export_tofu(order_id, requester_id)` — generates OpenTofu JSON

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/services/order_service.py tests/unit/test_order_service.py
git commit -m "feat: add OrderService with validation, submission, and Tofu export"
```

---

### Task 5: Orders API — CRUD Endpoints

**Files:**
- Create: `app/api/v1/orders.py`
- Modify: `app/__init__.py` (register blueprint)
- Test: `tests/integration/test_order_crud_api.py`

- [ ] **Step 1: Write failing tests** covering:
- POST /api/v1/orders → create draft (201)
- GET /api/v1/orders/{id} → get order with items (200)
- GET /api/v1/orders → list own orders (200), pagination, status filter
- PATCH /api/v1/orders/{id} → update title (200), 409 if not draft
- DELETE /api/v1/orders/{id} → delete draft (204), 409 if not draft
- 401 without auth, 403 for other user's order

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement orders blueprint + register in app factory**
- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/api/v1/orders.py app/__init__.py tests/integration/test_order_crud_api.py
git commit -m "feat: add Order CRUD API endpoints (create, get, list, update, delete)"
```

---

### Task 6: Orders API — Item Management Endpoints

**Files:**
- Modify: `app/api/v1/orders.py`
- Test: `tests/integration/test_order_items_api.py`

- [ ] **Step 1: Write failing tests** covering:
- POST /api/v1/orders/{id}/items → add item (201), warning for deprecated template
- PATCH /api/v1/orders/{id}/items/{item_id} → update parameters (200)
- DELETE /api/v1/orders/{id}/items/{item_id} → remove item (204)
- PUT /api/v1/orders/{id}/items/positions → reorder (200)
- 409 if order not draft, 404 if item not found

Must seed ServiceTemplates in test DB for template validation.

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement item endpoints**
- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/api/v1/orders.py tests/integration/test_order_items_api.py
git commit -m "feat: add Order item management endpoints (add, update, remove, reorder)"
```

---

### Task 7: Orders API — Validation Endpoint

**Files:**
- Modify: `app/api/v1/orders.py`
- Test: `tests/integration/test_order_validation_api.py`

- [ ] **Step 1: Write failing tests** covering:
- POST /api/v1/orders/{id}/validate → all valid (200, status → validated)
- POST /api/v1/orders/{id}/validate → has violations (200, status stays draft)
- 409 if order not draft/validated
- 409 if order has no items

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement validation endpoint**
- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/api/v1/orders.py tests/integration/test_order_validation_api.py
git commit -m "feat: add Order validation endpoint with catalog-based parameter checking"
```

---

### Task 8: Orders API — Submit Endpoint

**Files:**
- Modify: `app/api/v1/orders.py`
- Test: `tests/integration/test_order_submit_api.py`

- [ ] **Step 1: Write failing tests** covering:
- POST /api/v1/orders/{id}/submit → success (200, status → submitted)
- 409 if not validated
- 409 if already submitted
- 409 if no items
- Status polling: GET /api/v1/orders/{id}/status

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement submit + status endpoints**
- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/api/v1/orders.py tests/integration/test_order_submit_api.py
git commit -m "feat: add Order submit endpoint with status machine and idempotency protection"
```

---

### Task 9: Orders API — JSON Export Endpoint

**Files:**
- Modify: `app/api/v1/orders.py`
- Test: `tests/integration/test_order_export_api.py`

- [ ] **Step 1: Write failing tests** covering:
- GET /api/v1/orders/{id}/export/tofu → full export (200) with correct variable mapping
- GET /api/v1/orders/{id}/items/{item_id}/export/tofu → single item export (200)
- 409 if order is draft
- Correct type mapping (integers as numbers, booleans as booleans)
- depends_on inactive params excluded from export
- readonly_notice set for provisioning/done/failed orders

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement export endpoints**
- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git add app/api/v1/orders.py tests/integration/test_order_export_api.py
git commit -m "feat: add OpenTofu JSON export endpoint with variable mapping and dependency filtering"
```

---

### Task 10: Final Verification

- [ ] **Step 1: Run complete test suite**

Run: `pytest tests/ -v --tb=short`

- [ ] **Step 2: Verify endpoint count**

Expected new endpoints (15):
1. `POST /api/v1/orders` (create)
2. `GET /api/v1/orders/{id}` (detail)
3. `GET /api/v1/orders` (list)
4. `PATCH /api/v1/orders/{id}` (update metadata)
5. `DELETE /api/v1/orders/{id}` (delete draft)
6. `POST /api/v1/orders/{id}/items` (add item)
7. `PATCH /api/v1/orders/{id}/items/{item_id}` (update item)
8. `DELETE /api/v1/orders/{id}/items/{item_id}` (remove item)
9. `PUT /api/v1/orders/{id}/items/positions` (reorder)
10. `POST /api/v1/orders/{id}/validate` (validate)
11. `POST /api/v1/orders/{id}/submit` (submit)
12. `GET /api/v1/orders/{id}/status` (status polling)
13. `GET /api/v1/orders/{id}/events` (SSE stub)
14. `GET /api/v1/orders/{id}/export/tofu` (full export)
15. `GET /api/v1/orders/{id}/items/{item_id}/export/tofu` (item export)

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: phase 3 complete — Order Lifecycle with 15 endpoints"
```
