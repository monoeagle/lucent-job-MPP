# Subscriptions System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Subscription lifecycle management — every OrderItem becomes a Subscription at submit, with change/cancel flows requiring approval, group subscriptions for clusters, and a full frontend UI.

**Architecture:** New SubscriptionModel + GroupSubscriptionModel in DB. SubscriptionRepository for CRUD. SubscriptionService for lifecycle logic (create at submit, change, cancel). REST API for user + admin. Frontend with Subscriptions list page, detail page, and sidebar activation. Approval integration via existing ApprovalService.

**Tech Stack:** Python/Flask, SQLAlchemy, Alembic, PostgreSQL (backend). React 19, TypeScript, TailwindCSS 4, tanstack-query (frontend).

**Spec:** `docs/superpowers/specs/2026-03-27-subscriptions-design.md`

---

## File Structure

### Backend
```
app/
├── data/db/models/
│   ├── subscription.py           # NEW: SubscriptionModel + GroupSubscriptionModel
│   └── __init__.py               # MODIFY: register new models
├── data/repositories/
│   └── subscription_repository.py # NEW: CRUD + queries
├── services/
│   └── subscription_service.py   # NEW: lifecycle logic
├── api/v1/
│   └── subscriptions.py          # NEW: REST endpoints
└── __init__.py                   # MODIFY: register blueprint

tests/
├── integration/
│   ├── test_subscription_api.py          # NEW: CRUD endpoints
│   └── test_subscription_lifecycle_api.py # NEW: change/cancel flows
└── unit/
    └── test_subscription_service.py      # NEW: service logic
```

### Frontend
```
frontend/src/
├── types/subscription.ts                          # NEW
├── api/subscriptions.ts                           # NEW
├── hooks/useSubscriptions.ts                      # NEW
├── pages/
│   ├── Subscriptions.tsx                          # NEW
│   └── SubscriptionDetail.tsx                     # NEW
├── components/subscriptions/
│   ├── SubscriptionCard.tsx                       # NEW
│   └── SubscriptionGroupSection.tsx               # NEW
├── components/Layout/Sidebar.tsx                  # MODIFY: activate
└── App.tsx                                        # MODIFY: routes

frontend/tests/pages/
├── Subscriptions.test.tsx                         # NEW
└── SubscriptionDetail.test.tsx                    # NEW
```

---

### Task 1: DB Models — Subscription + GroupSubscription

**Files:**
- Create: `app/data/db/models/subscription.py`
- Modify: `app/data/db/models/__init__.py`

- [ ] **Step 1: Write failing test**

```python
# tests/integration/test_subscription_db.py
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.db.models.subscription import SubscriptionModel, GroupSubscriptionModel


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


class TestSubscriptionModel:
    def test_create_subscription(self, db_session):
        import uuid
        sub = SubscriptionModel(
            id=str(uuid.uuid4()),
            order_item_id=str(uuid.uuid4()),
            requester_id="test-requester",
            status="ordered",
            display_name="Linux VM",
            template_slug="vm-linux",
            template_version="1.0.0",
            parameters={"cpu_cores": 4},
        )
        db_session.add(sub)
        db_session.commit()

        found = db_session.query(SubscriptionModel).filter_by(id=sub.id).first()
        assert found is not None
        assert found.status == "ordered"
        assert found.parameters == {"cpu_cores": 4}
        assert found.activated_at is None
        assert found.cancelled_at is None
        assert found.pending_changes is None

    def test_create_group_subscription(self, db_session):
        import uuid
        group = GroupSubscriptionModel(
            id=str(uuid.uuid4()),
            name="Web-Cluster",
            requester_id="test-requester",
        )
        db_session.add(group)
        db_session.commit()

        found = db_session.query(GroupSubscriptionModel).filter_by(id=group.id).first()
        assert found is not None
        assert found.name == "Web-Cluster"
```

- [ ] **Step 2: Run test — verify FAIL**
- [ ] **Step 3: Implement models**

```python
# app/data/db/models/subscription.py
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.data.db.session import Base


class GroupSubscriptionModel(Base):
    __tablename__ = "group_subscriptions"

    id = Column(String(36), primary_key=True)
    order_item_group_id = Column(String(36), ForeignKey("order_item_groups.id"), nullable=True)
    name = Column(String(100), nullable=False)
    requester_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    subscriptions = relationship("SubscriptionModel", back_populates="group_subscription")


class SubscriptionModel(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True)
    order_item_id = Column(String(36), ForeignKey("order_items.id"), nullable=False, unique=True)
    group_subscription_id = Column(String(36), ForeignKey("group_subscriptions.id", ondelete="SET NULL"),
                                    nullable=True, index=True)
    requester_id = Column(String(100), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="ordered", index=True)
    display_name = Column(String(200), nullable=False)
    template_slug = Column(String(64), nullable=False)
    template_version = Column(String(32), nullable=False)
    parameters = Column(JSONB, nullable=False, default=dict)
    pending_changes = Column(JSONB, nullable=True)
    monthly_cost_eur = Column(Numeric(10, 2), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    group_subscription = relationship("GroupSubscriptionModel", back_populates="subscriptions")

    __table_args__ = (
        Index("ix_subscription_requester_status", "requester_id", "status"),
    )
```

Register in `app/data/db/models/__init__.py`:
```python
from app.data.db.models.subscription import SubscriptionModel, GroupSubscriptionModel
```

- [ ] **Step 4: Run test — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add app/data/db/models/subscription.py app/data/db/models/__init__.py tests/integration/test_subscription_db.py
git commit -m "feat: add SubscriptionModel and GroupSubscriptionModel"
```

---

### Task 2: Subscription Repository

**Files:**
- Create: `app/data/repositories/subscription_repository.py`
- Test: `tests/integration/test_subscription_repo.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_subscription_repo.py
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.subscription_repository import SubscriptionRepository
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
def seed(db_session):
    tmpl_repo = TemplateRepository(db_session)
    tmpl_repo.create({
        "slug": "vm-linux", "version": "1.0.0", "type": "vm",
        "display_name": "Linux VM", "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "estimated_cost_eur_per_month": 85.0,
        "parameters": [
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "cpu", "display_order": 1, "constraints": {"min": 1, "max": 64}},
        ],
    })
    order_repo = OrderRepository(db_session)
    order = order_repo.create_order("test-requester", "Test Order", "Reason")
    item = order_repo.add_item(order.id, "vm-linux", "1.0.0", "Linux VM", {"cpu": 4})
    return {"order": order, "item": item}


class TestCreateSubscription:
    def test_create_from_order_item(self, db_session, seed):
        repo = SubscriptionRepository(db_session)
        sub = repo.create_from_order_item(seed["item"], monthly_cost_eur=85.0)
        assert sub.order_item_id == seed["item"].id
        assert sub.status == "ordered"
        assert sub.display_name == "Linux VM"
        assert sub.template_slug == "vm-linux"
        assert float(sub.monthly_cost_eur) == 85.0


class TestListSubscriptions:
    def test_list_by_requester(self, db_session, seed):
        repo = SubscriptionRepository(db_session)
        repo.create_from_order_item(seed["item"])
        result = repo.list_subscriptions(requester_id="test-requester")
        assert result["total"] == 1

    def test_list_by_status(self, db_session, seed):
        repo = SubscriptionRepository(db_session)
        sub = repo.create_from_order_item(seed["item"])
        result = repo.list_subscriptions(status="ordered")
        assert result["total"] == 1
        result = repo.list_subscriptions(status="active")
        assert result["total"] == 0


class TestUpdateStatus:
    def test_update_status(self, db_session, seed):
        repo = SubscriptionRepository(db_session)
        sub = repo.create_from_order_item(seed["item"])
        updated = repo.update_status(sub.id, "active")
        assert updated.status == "active"
        assert updated.activated_at is not None

    def test_cancel_sets_cancelled_at(self, db_session, seed):
        repo = SubscriptionRepository(db_session)
        sub = repo.create_from_order_item(seed["item"])
        repo.update_status(sub.id, "active")
        cancelled = repo.update_status(sub.id, "cancelled")
        assert cancelled.cancelled_at is not None


class TestPendingChanges:
    def test_set_pending_changes(self, db_session, seed):
        repo = SubscriptionRepository(db_session)
        sub = repo.create_from_order_item(seed["item"])
        repo.update_status(sub.id, "active")
        changes = {"type": "change", "parameters": {"cpu": 8}, "reason": "More power"}
        updated = repo.set_pending_changes(sub.id, changes)
        assert updated.pending_changes == changes

    def test_apply_pending_changes(self, db_session, seed):
        repo = SubscriptionRepository(db_session)
        sub = repo.create_from_order_item(seed["item"])
        repo.update_status(sub.id, "active")
        repo.set_pending_changes(sub.id, {"type": "change", "parameters": {"cpu": 8}})
        updated = repo.apply_pending_changes(sub.id)
        assert updated.parameters["cpu"] == 8
        assert updated.pending_changes is None


class TestGroupSubscription:
    def test_create_group(self, db_session, seed):
        repo = SubscriptionRepository(db_session)
        group = repo.create_group(name="Web-Cluster", requester_id="test-requester")
        assert group.name == "Web-Cluster"

    def test_assign_to_group(self, db_session, seed):
        repo = SubscriptionRepository(db_session)
        group = repo.create_group(name="Web-Cluster", requester_id="test-requester")
        sub = repo.create_from_order_item(seed["item"])
        repo.assign_to_group(sub.id, group.id)
        refreshed = repo.get_by_id(sub.id)
        assert refreshed.group_subscription_id == group.id
```

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement**

```python
# app/data/repositories/subscription_repository.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.data.db.models.subscription import SubscriptionModel, GroupSubscriptionModel


class SubscriptionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_from_order_item(self, item, monthly_cost_eur=None,
                                group_subscription_id=None) -> SubscriptionModel:
        sub = SubscriptionModel(
            id=str(uuid.uuid4()),
            order_item_id=item.id,
            group_subscription_id=group_subscription_id,
            requester_id=item.order.requester_id if hasattr(item, 'order') and item.order else "",
            status="ordered",
            display_name=item.display_name,
            template_slug=item.template_slug,
            template_version=item.template_version,
            parameters=item.parameters,
            monthly_cost_eur=monthly_cost_eur,
        )
        self.session.add(sub)
        self.session.commit()
        return sub

    def get_by_id(self, subscription_id: str) -> SubscriptionModel | None:
        return self.session.query(SubscriptionModel).filter_by(id=subscription_id).first()

    def list_subscriptions(self, requester_id: str | None = None,
                           status: str | None = None,
                           limit: int = 50, offset: int = 0) -> dict:
        q = self.session.query(SubscriptionModel)
        if requester_id:
            q = q.filter(SubscriptionModel.requester_id == requester_id)
        if status:
            q = q.filter(SubscriptionModel.status == status)
        total = q.count()
        items = q.order_by(SubscriptionModel.created_at.desc()).offset(offset).limit(limit).all()
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def update_status(self, subscription_id: str, new_status: str) -> SubscriptionModel:
        sub = self.get_by_id(subscription_id)
        if sub is None:
            raise ValueError(f"Subscription '{subscription_id}' not found.")
        sub.status = new_status
        now = datetime.now(timezone.utc)
        if new_status == "active" and sub.activated_at is None:
            sub.activated_at = now
        if new_status == "cancelled":
            sub.cancelled_at = now
        self.session.commit()
        return sub

    def set_pending_changes(self, subscription_id: str, changes: dict) -> SubscriptionModel:
        sub = self.get_by_id(subscription_id)
        if sub is None:
            raise ValueError(f"Subscription '{subscription_id}' not found.")
        sub.pending_changes = changes
        self.session.commit()
        return sub

    def apply_pending_changes(self, subscription_id: str) -> SubscriptionModel:
        sub = self.get_by_id(subscription_id)
        if sub is None:
            raise ValueError(f"Subscription '{subscription_id}' not found.")
        if sub.pending_changes and "parameters" in sub.pending_changes:
            params = dict(sub.parameters)
            params.update(sub.pending_changes["parameters"])
            sub.parameters = params
        sub.pending_changes = None
        self.session.commit()
        return sub

    def create_group(self, name: str, requester_id: str,
                     order_item_group_id: str | None = None) -> GroupSubscriptionModel:
        group = GroupSubscriptionModel(
            id=str(uuid.uuid4()),
            order_item_group_id=order_item_group_id,
            name=name,
            requester_id=requester_id,
        )
        self.session.add(group)
        self.session.commit()
        return group

    def assign_to_group(self, subscription_id: str, group_id: str) -> None:
        sub = self.get_by_id(subscription_id)
        if sub is None:
            raise ValueError(f"Subscription '{subscription_id}' not found.")
        sub.group_subscription_id = group_id
        self.session.commit()

    def get_group(self, group_id: str) -> GroupSubscriptionModel | None:
        return self.session.query(GroupSubscriptionModel).filter_by(id=group_id).first()

    def list_groups(self, requester_id: str | None = None) -> list[GroupSubscriptionModel]:
        q = self.session.query(GroupSubscriptionModel)
        if requester_id:
            q = q.filter(GroupSubscriptionModel.requester_id == requester_id)
        return q.order_by(GroupSubscriptionModel.created_at.desc()).all()
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add app/data/repositories/subscription_repository.py tests/integration/test_subscription_repo.py
git commit -m "feat: add SubscriptionRepository with CRUD, status, changes, groups"
```

---

### Task 3: Subscription Service

**Files:**
- Create: `app/services/subscription_service.py`
- Test: `tests/unit/test_subscription_service.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_subscription_service.py
import pytest
from unittest.mock import MagicMock
from app.services.subscription_service import SubscriptionService


def _make_sub(sub_id="sub-1", status="active", requester_id="user-1",
              parameters=None, pending_changes=None):
    sub = MagicMock()
    sub.id = sub_id
    sub.status = status
    sub.requester_id = requester_id
    sub.parameters = parameters or {"cpu": 4}
    sub.pending_changes = pending_changes
    return sub


class TestRequestChange:
    def setup_method(self):
        self.repo = MagicMock()
        self.service = SubscriptionService(self.repo)

    def test_request_change_active_subscription(self):
        self.repo.get_by_id.return_value = _make_sub(status="active")
        self.repo.set_pending_changes.return_value = _make_sub(status="change_pending")
        self.repo.update_status.return_value = _make_sub(status="change_pending")

        result = self.service.request_change("sub-1", "user-1", {"cpu": 8}, "More power")
        self.repo.set_pending_changes.assert_called_once()
        self.repo.update_status.assert_called_with("sub-1", "change_pending")

    def test_request_change_not_active_raises(self):
        self.repo.get_by_id.return_value = _make_sub(status="ordered")
        with pytest.raises(ValueError, match="active"):
            self.service.request_change("sub-1", "user-1", {"cpu": 8}, "reason")

    def test_request_change_wrong_user_raises(self):
        self.repo.get_by_id.return_value = _make_sub(status="active", requester_id="other")
        with pytest.raises(PermissionError):
            self.service.request_change("sub-1", "user-1", {"cpu": 8}, "reason")


class TestRequestCancel:
    def setup_method(self):
        self.repo = MagicMock()
        self.service = SubscriptionService(self.repo)

    def test_request_cancel_active_subscription(self):
        self.repo.get_by_id.return_value = _make_sub(status="active")
        self.repo.update_status.return_value = _make_sub(status="cancel_pending")

        result = self.service.request_cancel("sub-1", "user-1", "No longer needed")
        self.repo.update_status.assert_called_with("sub-1", "cancel_pending")

    def test_request_cancel_not_active_raises(self):
        self.repo.get_by_id.return_value = _make_sub(status="cancelled")
        with pytest.raises(ValueError, match="active"):
            self.service.request_cancel("sub-1", "user-1", "reason")


class TestCreateFromOrder:
    def setup_method(self):
        self.repo = MagicMock()
        self.service = SubscriptionService(self.repo)

    def test_creates_subscription_per_item(self):
        item1 = MagicMock()
        item1.id = "i1"
        item1.group_id = None
        item2 = MagicMock()
        item2.id = "i2"
        item2.group_id = None

        order = MagicMock()
        order.items = [item1, item2]
        order.groups = []
        order.requester_id = "user-1"

        self.repo.create_from_order_item.return_value = MagicMock()
        self.service.create_from_order(order)
        assert self.repo.create_from_order_item.call_count == 2
```

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement**

```python
# app/services/subscription_service.py
from datetime import datetime, timezone


class SubscriptionService:
    def __init__(self, subscription_repo):
        self.repo = subscription_repo

    def _get_for_user(self, subscription_id: str, user_id: str, allow_admin: bool = False):
        sub = self.repo.get_by_id(subscription_id)
        if sub is None:
            raise ValueError(f"Subscription '{subscription_id}' not found.")
        if sub.requester_id != user_id and not allow_admin:
            raise PermissionError("No permission to access this subscription.")
        return sub

    def create_from_order(self, order, template_costs: dict | None = None):
        """Create subscriptions for all items in a submitted order."""
        costs = template_costs or {}
        group_map = {}

        # Create group subscriptions
        for group in (order.groups or []):
            gsub = self.repo.create_group(
                name=group.name,
                requester_id=order.requester_id,
                order_item_group_id=group.id,
            )
            group_map[group.id] = gsub.id

        # Create subscriptions per item
        for item in order.items:
            group_sub_id = group_map.get(item.group_id) if item.group_id else None
            cost = costs.get(item.template_slug)
            self.repo.create_from_order_item(
                item,
                monthly_cost_eur=cost,
                group_subscription_id=group_sub_id,
            )

    def request_change(self, subscription_id: str, user_id: str,
                       new_parameters: dict, reason: str):
        sub = self._get_for_user(subscription_id, user_id)
        if sub.status != "active":
            raise ValueError("Subscription must be active to request a change.")
        changes = {
            "type": "change",
            "parameters": new_parameters,
            "reason": reason,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }
        self.repo.set_pending_changes(subscription_id, changes)
        return self.repo.update_status(subscription_id, "change_pending")

    def request_cancel(self, subscription_id: str, user_id: str, reason: str):
        sub = self._get_for_user(subscription_id, user_id)
        if sub.status != "active":
            raise ValueError("Subscription must be active to request cancellation.")
        changes = {
            "type": "cancel",
            "reason": reason,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }
        self.repo.set_pending_changes(subscription_id, changes)
        return self.repo.update_status(subscription_id, "cancel_pending")

    def approve_change(self, subscription_id: str):
        sub = self.repo.get_by_id(subscription_id)
        if sub.status == "change_pending":
            self.repo.apply_pending_changes(subscription_id)
            return self.repo.update_status(subscription_id, "active")
        elif sub.status == "cancel_pending":
            return self.repo.update_status(subscription_id, "cancelled")
        raise ValueError(f"Cannot approve subscription in status '{sub.status}'.")

    def reject_change(self, subscription_id: str):
        sub = self.repo.get_by_id(subscription_id)
        if sub.status in ("change_pending", "cancel_pending"):
            self.repo.set_pending_changes(subscription_id, None)
            return self.repo.update_status(subscription_id, "active")
        raise ValueError(f"Cannot reject subscription in status '{sub.status}'.")
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add app/services/subscription_service.py tests/unit/test_subscription_service.py
git commit -m "feat: add SubscriptionService with change/cancel/create lifecycle"
```

---

### Task 4: Subscription API Endpoints

**Files:**
- Create: `app/api/v1/subscriptions.py`
- Modify: `app/__init__.py`
- Test: `tests/integration/test_subscription_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_subscription_api.py
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.order_repository import OrderRepository
from app.data.repositories.template_repository import TemplateRepository
from app.data.repositories.subscription_repository import SubscriptionRepository


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
def seed(db_session):
    tmpl_repo = TemplateRepository(db_session)
    tmpl_repo.create({
        "slug": "vm-linux", "version": "1.0.0", "type": "vm",
        "display_name": "Linux VM", "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "estimated_cost_eur_per_month": 85.0,
        "parameters": [
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "cpu", "display_order": 1, "constraints": {"min": 1, "max": 64}},
        ],
    })
    order_repo = OrderRepository(db_session)
    order = order_repo.create_order("test-requester", "Test", "Reason")
    item = order_repo.add_item(order.id, "vm-linux", "1.0.0", "Linux VM", {"cpu": 4})

    sub_repo = SubscriptionRepository(db_session)
    sub = sub_repo.create_from_order_item(item, monthly_cost_eur=85.0)
    sub_repo.update_status(sub.id, "active")
    return {"order": order, "item": item, "subscription": sub}


class TestListSubscriptions:
    def test_list_returns_200(self, client, db_session, seed, requester_headers):
        resp = client.get("/api/v1/subscriptions", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 1
        assert data["items"][0]["template_slug"] == "vm-linux"

    def test_list_unauthenticated_returns_401(self, client, db_session):
        resp = client.get("/api/v1/subscriptions")
        assert resp.status_code == 401


class TestGetSubscription:
    def test_get_returns_200(self, client, db_session, seed, requester_headers):
        sid = seed["subscription"].id
        resp = client.get(f"/api/v1/subscriptions/{sid}", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == sid
        assert data["status"] == "active"

    def test_get_not_found_returns_404(self, client, db_session, requester_headers):
        resp = client.get("/api/v1/subscriptions/nonexistent", headers=requester_headers)
        assert resp.status_code == 404


class TestChangeRequest:
    def test_change_returns_200(self, client, db_session, seed, requester_headers):
        sid = seed["subscription"].id
        resp = client.post(f"/api/v1/subscriptions/{sid}/change", headers=requester_headers,
                           json={"parameters": {"cpu": 8}, "reason": "More power"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "change_pending"

    def test_change_not_active_returns_409(self, client, db_session, seed, requester_headers):
        sid = seed["subscription"].id
        # First change puts it in change_pending
        client.post(f"/api/v1/subscriptions/{sid}/change", headers=requester_headers,
                    json={"parameters": {"cpu": 8}, "reason": "reason"})
        # Second change should fail
        resp = client.post(f"/api/v1/subscriptions/{sid}/change", headers=requester_headers,
                           json={"parameters": {"cpu": 16}, "reason": "more"})
        assert resp.status_code == 409


class TestCancelRequest:
    def test_cancel_returns_200(self, client, db_session, seed, requester_headers):
        sid = seed["subscription"].id
        resp = client.post(f"/api/v1/subscriptions/{sid}/cancel", headers=requester_headers,
                           json={"reason": "No longer needed"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "cancel_pending"
```

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement**

```python
# app/api/v1/subscriptions.py
from flask import Blueprint, jsonify, request, g

from app.core.auth import login_required, role_required
from app.core.errors import NotFoundError, ForbiddenError, ConflictError
from app.data.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import SubscriptionService

bp = Blueprint("subscriptions", __name__, url_prefix="/api/v1")
admin_bp = Blueprint("admin_subscriptions", __name__, url_prefix="/api/v1/admin")


def _get_service() -> SubscriptionService:
    repo = SubscriptionRepository(g.db_session)
    return SubscriptionService(repo)


def _serialize(sub) -> dict:
    return {
        "id": sub.id,
        "order_item_id": sub.order_item_id,
        "group_subscription_id": sub.group_subscription_id,
        "requester_id": sub.requester_id,
        "status": sub.status,
        "display_name": sub.display_name,
        "template_slug": sub.template_slug,
        "template_version": sub.template_version,
        "parameters": sub.parameters,
        "pending_changes": sub.pending_changes,
        "monthly_cost_eur": float(sub.monthly_cost_eur) if sub.monthly_cost_eur else None,
        "activated_at": sub.activated_at.isoformat() if sub.activated_at else None,
        "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
        "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
    }


def _serialize_group(group) -> dict:
    return {
        "id": group.id,
        "name": group.name,
        "requester_id": group.requester_id,
        "subscriptions": [_serialize(s) for s in group.subscriptions],
        "created_at": group.created_at.isoformat() if group.created_at else None,
    }


@bp.route("/subscriptions", methods=["GET"])
@login_required
def list_subscriptions():
    repo = SubscriptionRepository(g.db_session)
    user = g.current_user
    status = request.args.get("status")
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    requester_id = None if user.is_admin else user.username
    result = repo.list_subscriptions(requester_id=requester_id, status=status,
                                      limit=limit, offset=offset)
    return jsonify({
        "items": [_serialize(s) for s in result["items"]],
        "total": result["total"],
        "limit": result["limit"],
        "offset": result["offset"],
    }), 200


@bp.route("/subscriptions/<subscription_id>", methods=["GET"])
@login_required
def get_subscription(subscription_id):
    repo = SubscriptionRepository(g.db_session)
    sub = repo.get_by_id(subscription_id)
    if sub is None:
        raise NotFoundError("Subscription not found.")
    user = g.current_user
    if sub.requester_id != user.username and not user.is_admin:
        raise ForbiddenError("Keine Berechtigung.")
    return jsonify(_serialize(sub)), 200


@bp.route("/subscriptions/<subscription_id>/change", methods=["POST"])
@login_required
def request_change(subscription_id):
    data = request.get_json() or {}
    service = _get_service()
    try:
        sub = service.request_change(
            subscription_id, g.current_user.username,
            data.get("parameters", {}), data.get("reason", ""),
        )
    except ValueError as e:
        raise ConflictError(str(e))
    except PermissionError:
        raise ForbiddenError("Keine Berechtigung.")
    return jsonify(_serialize(sub)), 200


@bp.route("/subscriptions/<subscription_id>/cancel", methods=["POST"])
@login_required
def request_cancel(subscription_id):
    data = request.get_json() or {}
    service = _get_service()
    try:
        sub = service.request_cancel(
            subscription_id, g.current_user.username,
            data.get("reason", ""),
        )
    except ValueError as e:
        raise ConflictError(str(e))
    except PermissionError:
        raise ForbiddenError("Keine Berechtigung.")
    return jsonify(_serialize(sub)), 200


@bp.route("/subscriptions/groups", methods=["GET"])
@login_required
def list_groups():
    repo = SubscriptionRepository(g.db_session)
    user = g.current_user
    requester_id = None if user.is_admin else user.username
    groups = repo.list_groups(requester_id=requester_id)
    return jsonify([_serialize_group(g_) for g_ in groups]), 200


@bp.route("/subscriptions/groups/<group_id>", methods=["GET"])
@login_required
def get_group(group_id):
    repo = SubscriptionRepository(g.db_session)
    group = repo.get_group(group_id)
    if group is None:
        raise NotFoundError("Group not found.")
    user = g.current_user
    if group.requester_id != user.username and not user.is_admin:
        raise ForbiddenError("Keine Berechtigung.")
    return jsonify(_serialize_group(group)), 200


@admin_bp.route("/subscriptions", methods=["GET"])
@role_required("admin")
def admin_list_subscriptions():
    repo = SubscriptionRepository(g.db_session)
    status = request.args.get("status")
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    result = repo.list_subscriptions(status=status, limit=limit, offset=offset)
    return jsonify({
        "items": [_serialize(s) for s in result["items"]],
        "total": result["total"],
        "limit": result["limit"],
        "offset": result["offset"],
    }), 200
```

Register in `app/__init__.py`:
```python
    from app.api.v1 import subscriptions
    app.register_blueprint(subscriptions.bp)
    app.register_blueprint(subscriptions.admin_bp)
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run full backend tests**
- [ ] **Step 6: Commit**

```bash
git add app/api/v1/subscriptions.py app/__init__.py tests/integration/test_subscription_api.py
git commit -m "feat: add subscription REST API endpoints"
```

---

### Task 5: Wire Subscription Creation at Order Submit

**Files:**
- Modify: `app/api/v1/orders.py`

- [ ] **Step 1: Add subscription creation after successful submit**

In `app/api/v1/orders.py`, in the `submit_order` function, add subscription creation after the notification block and before the final return:

```python
    # Create subscriptions
    from app.data.repositories.subscription_repository import SubscriptionRepository
    from app.services.subscription_service import SubscriptionService
    try:
        sub_repo = SubscriptionRepository(g.db_session)
        sub_service = SubscriptionService(sub_repo)
        sub_service.create_from_order(submitted)
    except Exception:
        pass  # Subscription creation failure should not block submit
```

- [ ] **Step 2: Run submit tests to verify no regression**

Run: `pytest tests/integration/test_order_submit_api.py -v --tb=short`

- [ ] **Step 3: Commit**

```bash
git add app/api/v1/orders.py
git commit -m "feat: create subscriptions automatically on order submit"
```

---

### Task 6: Frontend — Types + API + Hooks

**Files:**
- Create: `frontend/src/types/subscription.ts`
- Create: `frontend/src/api/subscriptions.ts`
- Create: `frontend/src/hooks/useSubscriptions.ts`

- [ ] **Step 1: Create types**

```typescript
// frontend/src/types/subscription.ts
export interface Subscription {
  id: string
  order_item_id: string
  group_subscription_id: string | null
  requester_id: string
  status: string
  display_name: string
  template_slug: string
  template_version: string
  parameters: Record<string, unknown>
  pending_changes: {
    type: string
    parameters?: Record<string, unknown>
    reason?: string
    requested_at?: string
  } | null
  monthly_cost_eur: number | null
  activated_at: string | null
  cancelled_at: string | null
  created_at: string
  updated_at: string
}

export interface SubscriptionGroup {
  id: string
  name: string
  requester_id: string
  subscriptions: Subscription[]
  created_at: string
}

export interface SubscriptionListResponse {
  items: Subscription[]
  total: number
  limit: number
  offset: number
}
```

- [ ] **Step 2: Create API client**

```typescript
// frontend/src/api/subscriptions.ts
import { apiClient } from './client'
import type { Subscription, SubscriptionGroup, SubscriptionListResponse } from '../types/subscription'

export const subscriptionsApi = {
  async list(token: string, params?: { status?: string; limit?: number; offset?: number }): Promise<SubscriptionListResponse> {
    const qs = new URLSearchParams()
    if (params) Object.entries(params).forEach(([k, v]) => { if (v !== undefined) qs.set(k, String(v)) })
    const query = qs.toString()
    return (await apiClient.get(`/api/v1/subscriptions${query ? `?${query}` : ''}`, token)) as SubscriptionListResponse
  },

  async get(token: string, id: string): Promise<Subscription> {
    return (await apiClient.get(`/api/v1/subscriptions/${id}`, token)) as Subscription
  },

  async requestChange(token: string, id: string, parameters: Record<string, unknown>, reason: string): Promise<Subscription> {
    return (await apiClient.post(`/api/v1/subscriptions/${id}/change`, { parameters, reason }, token)) as Subscription
  },

  async requestCancel(token: string, id: string, reason: string): Promise<Subscription> {
    return (await apiClient.post(`/api/v1/subscriptions/${id}/cancel`, { reason }, token)) as Subscription
  },

  async listGroups(token: string): Promise<SubscriptionGroup[]> {
    return (await apiClient.get('/api/v1/subscriptions/groups', token)) as SubscriptionGroup[]
  },

  async getGroup(token: string, groupId: string): Promise<SubscriptionGroup> {
    return (await apiClient.get(`/api/v1/subscriptions/groups/${groupId}`, token)) as SubscriptionGroup
  },
}
```

- [ ] **Step 3: Create hooks**

```typescript
// frontend/src/hooks/useSubscriptions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { subscriptionsApi } from '../api/subscriptions'
import { useAuthStore } from '../store/authStore'

export function useSubscriptions(params?: { status?: string; limit?: number; offset?: number }) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['subscriptions', params],
    queryFn: () => subscriptionsApi.list(token!, params),
    enabled: !!token,
  })
}

export function useSubscription(id: string | null) {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['subscription', id],
    queryFn: () => subscriptionsApi.get(token!, id!),
    enabled: !!token && !!id,
  })
}

export function useRequestChange(id: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ parameters, reason }: { parameters: Record<string, unknown>; reason: string }) =>
      subscriptionsApi.requestChange(token!, id, parameters, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['subscription', id] })
      qc.invalidateQueries({ queryKey: ['subscriptions'] })
    },
  })
}

export function useRequestCancel(id: string) {
  const token = useAuthStore((s) => s.token)
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (reason: string) => subscriptionsApi.requestCancel(token!, id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['subscription', id] })
      qc.invalidateQueries({ queryKey: ['subscriptions'] })
    },
  })
}

export function useSubscriptionGroups() {
  const token = useAuthStore((s) => s.token)
  return useQuery({
    queryKey: ['subscription-groups'],
    queryFn: () => subscriptionsApi.listGroups(token!),
    enabled: !!token,
  })
}
```

- [ ] **Step 4: Run TS check + tests**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/subscription.ts frontend/src/api/subscriptions.ts frontend/src/hooks/useSubscriptions.ts
git commit -m "feat(frontend): add subscription types, API client, and hooks"
```

---

### Task 7: Frontend — Subscriptions Page + Components

**Files:**
- Create: `frontend/src/components/subscriptions/SubscriptionCard.tsx`
- Create: `frontend/src/components/subscriptions/SubscriptionGroupSection.tsx`
- Create: `frontend/src/pages/Subscriptions.tsx`
- Create: `frontend/tests/pages/Subscriptions.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/tests/pages/Subscriptions.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Subscriptions from '../../src/pages/Subscriptions'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/subscriptions', () => ({
  subscriptionsApi: {
    list: vi.fn().mockResolvedValue({
      items: [
        {
          id: 's1', order_item_id: 'i1', group_subscription_id: null,
          requester_id: 'test-requester', status: 'active',
          display_name: 'Linux VM', template_slug: 'vm-linux',
          template_version: '1.0.0', parameters: { cpu: 4 },
          pending_changes: null, monthly_cost_eur: 85,
          activated_at: '2026-01-15T10:00:00Z', cancelled_at: null,
          created_at: '2026-01-15T10:00:00Z', updated_at: '2026-01-15T10:00:00Z',
        },
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
        <Subscriptions />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Subscriptions', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'test-requester', display_name: 'Test', email: 't@t', roles: ['requester'] },
    })
  })

  it('renders heading', async () => {
    renderPage()
    expect(await screen.findByText('Subscriptions')).toBeInTheDocument()
  })

  it('renders subscription card', async () => {
    renderPage()
    expect(await screen.findByText('Linux VM')).toBeInTheDocument()
  })

  it('shows status badge', async () => {
    renderPage()
    expect(await screen.findByText('active')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — verify FAIL**
- [ ] **Step 3: Implement SubscriptionCard**

```tsx
// frontend/src/components/subscriptions/SubscriptionCard.tsx
import { Link } from 'react-router-dom'
import type { Subscription } from '../../types/subscription'
import StatusBadge from '../StatusBadge'

interface Props {
  subscription: Subscription
}

export default function SubscriptionCard({ subscription: sub }: Props) {
  const paramSummary = Object.entries(sub.parameters)
    .slice(0, 4)
    .map(([k, v]) => `${k}: ${String(v)}`)
    .join(', ')

  return (
    <Link to={`/subscriptions/${sub.id}`}
      className="block border border-gray-200 rounded-lg p-4 bg-white hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{sub.display_name}</span>
          <span className="text-xs text-gray-400">v{sub.template_version}</span>
          <StatusBadge status={sub.status} />
        </div>
        {sub.monthly_cost_eur && (
          <span className="text-xs text-gray-400">{sub.monthly_cost_eur} EUR/Monat</span>
        )}
      </div>
      {paramSummary && <p className="text-xs text-gray-500 truncate">{paramSummary}</p>}
      {sub.pending_changes && (
        <p className="text-xs text-yellow-600 mt-1">Aenderung ausstehend: {sub.pending_changes.type}</p>
      )}
    </Link>
  )
}
```

- [ ] **Step 4: Implement SubscriptionGroupSection**

```tsx
// frontend/src/components/subscriptions/SubscriptionGroupSection.tsx
import { useState } from 'react'
import type { SubscriptionGroup } from '../../types/subscription'
import SubscriptionCard from './SubscriptionCard'

interface Props {
  group: SubscriptionGroup
}

export default function SubscriptionGroupSection({ group }: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const activeCount = group.subscriptions.filter((s) => s.status === 'active').length

  return (
    <div className="border border-gray-300 rounded-lg bg-gray-50">
      <div className="flex items-center justify-between p-3 cursor-pointer"
           onClick={() => setCollapsed(!collapsed)}>
        <div className="flex items-center gap-2">
          <span className="text-sm">{collapsed ? '▶' : '▼'}</span>
          <span className="font-medium">{group.name}</span>
          <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">
            {activeCount}/{group.subscriptions.length} aktiv
          </span>
        </div>
      </div>
      {!collapsed && (
        <div className="px-3 pb-3 space-y-2">
          {group.subscriptions.map((sub) => (
            <SubscriptionCard key={sub.id} subscription={sub} />
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Implement Subscriptions page**

```tsx
// frontend/src/pages/Subscriptions.tsx
import { useState } from 'react'
import { useSubscriptions, useSubscriptionGroups } from '../hooks/useSubscriptions'
import SubscriptionCard from '../components/subscriptions/SubscriptionCard'
import SubscriptionGroupSection from '../components/subscriptions/SubscriptionGroupSection'

export default function Subscriptions() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const { data, isLoading } = useSubscriptions({ status: statusFilter })
  const { data: groups } = useSubscriptionGroups()

  const subscriptions = data?.items ?? []
  const groupList = groups ?? []
  const groupedIds = new Set(groupList.flatMap((g) => g.subscriptions.map((s) => s.id)))
  const ungrouped = subscriptions.filter((s) => !groupedIds.has(s.id))

  const statuses = ['active', 'ordered', 'pending_approval', 'change_pending', 'cancel_pending', 'cancelled']

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Subscriptions</h1>

      <div className="flex gap-2 mb-4 flex-wrap">
        <button onClick={() => setStatusFilter(undefined)}
          className={`px-3 py-1 rounded-full text-sm ${!statusFilter ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
          Alle
        </button>
        {statuses.map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded-full text-sm ${statusFilter === s ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
            {s}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-gray-500">Lade Subscriptions...</p>
      ) : (
        <div className="space-y-4">
          {groupList.length > 0 && (
            <div className="space-y-3">
              {groupList.map((group) => (
                <SubscriptionGroupSection key={group.id} group={group} />
              ))}
            </div>
          )}

          {ungrouped.length > 0 && (
            <div className="space-y-2">
              {groupList.length > 0 && <h3 className="text-sm font-medium text-gray-500">Einzeln</h3>}
              {ungrouped.map((sub) => (
                <SubscriptionCard key={sub.id} subscription={sub} />
              ))}
            </div>
          )}

          {subscriptions.length === 0 && groupList.length === 0 && (
            <p className="text-gray-400">Keine Subscriptions vorhanden.</p>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 6: Run tests — verify PASS**
- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/subscriptions/SubscriptionCard.tsx frontend/src/components/subscriptions/SubscriptionGroupSection.tsx frontend/src/pages/Subscriptions.tsx frontend/tests/pages/Subscriptions.test.tsx
git commit -m "feat(frontend): add Subscriptions page with card, group section, and status filter"
```

---

### Task 8: Frontend — SubscriptionDetail Page

**Files:**
- Create: `frontend/src/pages/SubscriptionDetail.tsx`
- Create: `frontend/tests/pages/SubscriptionDetail.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// frontend/tests/pages/SubscriptionDetail.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import SubscriptionDetail from '../../src/pages/SubscriptionDetail'
import { useAuthStore } from '../../src/store/authStore'

vi.mock('../../src/api/subscriptions', () => ({
  subscriptionsApi: {
    get: vi.fn().mockResolvedValue({
      id: 's1', order_item_id: 'i1', group_subscription_id: null,
      requester_id: 'test-requester', status: 'active',
      display_name: 'Linux VM', template_slug: 'vm-linux',
      template_version: '1.0.0', parameters: { cpu: 4, ram: 16 },
      pending_changes: null, monthly_cost_eur: 85,
      activated_at: '2026-01-15T10:00:00Z', cancelled_at: null,
      created_at: '2026-01-10T10:00:00Z', updated_at: '2026-01-15T10:00:00Z',
    }),
    requestChange: vi.fn().mockResolvedValue({}),
    requestCancel: vi.fn().mockResolvedValue({}),
  },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/subscriptions/s1']}>
        <Routes>
          <Route path="/subscriptions/:id" element={<SubscriptionDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('SubscriptionDetail', () => {
  beforeEach(() => {
    useAuthStore.setState({
      isAuthenticated: true, token: 'test-token',
      user: { username: 'test-requester', display_name: 'Test', email: 't@t', roles: ['requester'] },
    })
  })

  it('renders subscription name', async () => {
    renderPage()
    expect(await screen.findByText('Linux VM')).toBeInTheDocument()
  })

  it('renders parameters', async () => {
    renderPage()
    expect(await screen.findByText('cpu')).toBeInTheDocument()
    expect(await screen.findByText('4')).toBeInTheDocument()
  })

  it('shows action buttons for active subscription', async () => {
    renderPage()
    expect(await screen.findByText('Aendern')).toBeInTheDocument()
    expect(await screen.findByText('Kuendigen')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — verify FAIL**
- [ ] **Step 3: Implement**

```tsx
// frontend/src/pages/SubscriptionDetail.tsx
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useSubscription, useRequestChange, useRequestCancel } from '../hooks/useSubscriptions'
import StatusBadge from '../components/StatusBadge'

export default function SubscriptionDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: sub, isLoading } = useSubscription(id ?? null)
  const requestChange = useRequestChange(id ?? '')
  const requestCancel = useRequestCancel(id ?? '')

  const [cancelDialogOpen, setCancelDialogOpen] = useState(false)
  const [cancelReason, setCancelReason] = useState('')

  const handleCancel = () => {
    if (!cancelReason.trim()) return
    requestCancel.mutate(cancelReason, {
      onSuccess: () => { setCancelDialogOpen(false); setCancelReason('') },
    })
  }

  if (isLoading) return <p className="text-gray-500">Lade Subscription...</p>
  if (!sub) return <p className="text-red-500">Subscription nicht gefunden.</p>

  const isActive = sub.status === 'active'

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold">{sub.display_name}</h1>
          <p className="text-sm text-gray-400">{sub.template_slug} v{sub.template_version}</p>
        </div>
        <StatusBadge status={sub.status} />
      </div>

      {sub.monthly_cost_eur && (
        <p className="text-sm text-gray-600 mb-4">{sub.monthly_cost_eur} EUR/Monat</p>
      )}

      {/* Parameters */}
      <div className="bg-gray-50 rounded-lg p-4 mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Konfiguration</h3>
        <div className="space-y-2">
          {Object.entries(sub.parameters).map(([key, val]) => (
            <div key={key} className="flex justify-between text-sm">
              <span className="text-gray-600">{key}</span>
              <span className="font-medium">{String(val)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Pending changes */}
      {sub.pending_changes && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-semibold text-yellow-700 mb-2">Ausstehende Aenderung</h3>
          <p className="text-sm text-yellow-600">Typ: {sub.pending_changes.type}</p>
          {sub.pending_changes.reason && (
            <p className="text-sm text-yellow-600">Grund: {sub.pending_changes.reason}</p>
          )}
        </div>
      )}

      {/* Timeline */}
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Timeline</h3>
        <div className="text-sm space-y-1 text-gray-600">
          <p>Erstellt: {new Date(sub.created_at).toLocaleString('de-DE')}</p>
          {sub.activated_at && <p>Aktiviert: {new Date(sub.activated_at).toLocaleString('de-DE')}</p>}
          {sub.cancelled_at && <p>Gekuendigt: {new Date(sub.cancelled_at).toLocaleString('de-DE')}</p>}
        </div>
      </div>

      {/* Actions */}
      {isActive && (
        <div className="flex gap-3">
          <button className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700">
            Aendern
          </button>
          <button onClick={() => setCancelDialogOpen(true)}
            className="px-4 py-2 bg-red-600 text-white rounded-md text-sm hover:bg-red-700">
            Kuendigen
          </button>
        </div>
      )}

      {/* Cancel dialog */}
      {cancelDialogOpen && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96 shadow-xl">
            <h3 className="text-lg font-semibold mb-4">Subscription kuendigen</h3>
            <textarea
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="Grund fuer die Kuendigung"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm mb-4"
              rows={3}
            />
            <div className="flex gap-2 justify-end">
              <button onClick={() => { setCancelDialogOpen(false); setCancelReason('') }}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
                Abbrechen
              </button>
              <button onClick={handleCancel}
                disabled={!cancelReason.trim() || requestCancel.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded-md text-sm hover:bg-red-700 disabled:opacity-50">
                Kuendigen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SubscriptionDetail.tsx frontend/tests/pages/SubscriptionDetail.test.tsx
git commit -m "feat(frontend): add SubscriptionDetail page with parameters, timeline, change/cancel actions"
```

---

### Task 9: Frontend — Routes + Sidebar Activation

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout/Sidebar.tsx`

- [ ] **Step 1: Add routes in App.tsx**

Add imports:
```tsx
import Subscriptions from './pages/Subscriptions'
import SubscriptionDetail from './pages/SubscriptionDetail'
```

Add routes inside protected block:
```tsx
<Route path="/subscriptions" element={<Subscriptions />} />
<Route path="/subscriptions/:id" element={<SubscriptionDetail />} />
```

- [ ] **Step 2: Activate Subscriptions in Sidebar**

In `frontend/src/components/Layout/Sidebar.tsx`, find the Subscriptions nav item:
```tsx
  { to: '#', label: 'Subscriptions', icon: '📦', roles: null, disabled: true },
```

Change to:
```tsx
  { to: '/subscriptions', label: 'Subscriptions', icon: '📦', roles: null },
```

- [ ] **Step 3: Run all frontend tests**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Layout/Sidebar.tsx
git commit -m "feat(frontend): activate Subscriptions in sidebar and add routes"
```

---

### Task 10: Final Verification

- [ ] **Step 1: Run full frontend test suite**

Run: `cd frontend && npx vitest run`

- [ ] **Step 2: Type check**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Run full backend test suite**

Run: `source venv/bin/activate && DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_test pytest tests/ -q`

- [ ] **Step 4: Final commit**

```bash
git commit -m "chore: subscriptions system complete — lifecycle, change/cancel, groups, frontend"
```
