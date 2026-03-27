# Phase 8: Order Groups + Quantity + Per-Instance Parameters — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Order system with item groups for logical clustering, quantity for scaling identical servers, and per-instance parameters that differentiate shared vs. instance-specific configuration. Fully backwards-compatible.

**Architecture:** New OrderItemGroupModel in DB. Extended OrderItemModel with group_id, quantity, instance_parameters. Extended ParameterDefinition with per_instance field. GroupService handles group CRUD. OrderService extended for quantity expansion at submit time. Frontend gets group UI + quantity selector + per-instance form sections.

**Tech Stack:** Flask, SQLAlchemy, PostgreSQL (JSONB), Alembic, React, TypeScript

**Spec:** `docs/specs/order-groups-quantity.md` — Features 11.1-11.3

---

## File Structure (new/modified)

### Backend
```
app/
├── data/db/models/
│   ├── order_group.py              # NEW: OrderItemGroupModel
│   ├── order.py                    # MODIFY: add group_id, quantity, instance_parameters to OrderItemModel
│   └── __init__.py                 # MODIFY: register new model
├── data/repositories/
│   └── order_repository.py         # MODIFY: group CRUD, quantity handling
├── domain/
│   └── catalog.py                  # MODIFY: add per_instance to ParameterDefinition
├── services/
│   ├── order_service.py            # MODIFY: quantity expansion, instance params validation
│   └── catalog_service.py          # MODIFY: per_instance validation
└── api/v1/
    └── orders.py                   # MODIFY: group endpoints, quantity in add-item

tests/
├── unit/
│   └── test_order_groups_service.py
├── integration/
│   ├── test_order_groups_api.py
│   ├── test_order_quantity_api.py
│   └── test_per_instance_api.py
└── e2e/
    └── test_groups_quantity_e2e.py
```

### Frontend
```
frontend/src/
├── types/
│   └── order.ts                    # MODIFY: add group, quantity, instance_parameters types
├── api/
│   └── orders.ts                   # MODIFY: group API calls, quantity in add-item
├── components/
│   └── orders/
│       ├── GroupSection.tsx         # NEW: collapsible group container
│       ├── QuantitySelector.tsx     # NEW: quantity input with instance preview
│       └── OrderItemCard.tsx        # MODIFY: show group badge, quantity badge
└── pages/
    └── OrderDetail.tsx             # MODIFY: group-based layout, add-group button
```

---

### Task 1: DB Model — OrderItemGroup + OrderItem Extensions

**Files:**
- Create: `app/data/db/models/order_group.py`
- Modify: `app/data/db/models/order.py`
- Modify: `app/data/db/models/__init__.py`
- Test: `tests/integration/test_order_group_db.py`

- [ ] **Step 1: Write failing tests**

Tests:
- Create OrderItemGroupModel with name, order_id, position
- Unique constraint on (order_id, lower(name))
- OrderItemModel with group_id FK, quantity default 1, instance_parameters JSONB default []
- Cascade: deleting group sets items' group_id to null (SET NULL)

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement models**

OrderItemGroupModel: id, order_id (FK), name (String 100), description (Text nullable), position (Integer), created_at, updated_at. UniqueConstraint on (order_id, name) with functional index for case-insensitive.

OrderItemModel additions: group_id (String 36, FK to order_item_groups.id, SET NULL, nullable), quantity (Integer, default 1), instance_parameters (JSONB, default []).

- [ ] **Step 4: Alembic migration**
- [ ] **Step 5: Run ALL tests, commit**

```bash
git commit -m "feat: add OrderItemGroup model and extend OrderItem with group_id, quantity, instance_parameters"
```

---

### Task 2: ParameterDefinition — Add per_instance Field

**Files:**
- Modify: `app/domain/catalog.py`
- Modify: `app/data/db/models/service_template.py` (JSONB schema allows new field)
- Modify: `app/services/template_validator.py`
- Test: `tests/unit/test_per_instance_param.py`

- [ ] **Step 1: Write failing tests**

- ParameterDefinition with per_instance=False (default)
- ParameterDefinition with per_instance=True
- ParameterDefinition with per_instance="auto"
- TemplateValidator: per_instance="auto" only for type="string"
- TemplateValidator: max 1 hostname + 1 ip parameter with per_instance="auto"

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement**

Add `per_instance` field to ParameterDefinition dataclass (default False). Update TemplateValidator to validate per_instance rules.

- [ ] **Step 4: Run ALL tests, commit**

```bash
git commit -m "feat: add per_instance field to ParameterDefinition (false/true/auto)"
```

---

### Task 3: Group Repository Methods

**Files:**
- Modify: `app/data/repositories/order_repository.py`
- Test: `tests/integration/test_order_groups_repo.py`

- [ ] **Step 1: Write failing tests**

- create_group(order_id, name, description) → returns group with auto-position
- list_groups(order_id) → returns groups ordered by position
- get_group(group_id) → returns group or None
- update_group(group_id, name=None, description=None)
- delete_group(group_id) → raises if not empty
- reorder_groups(order_id, positions)
- assign_item_to_group(item_id, group_id)
- unassign_item_from_group(item_id)
- Duplicate name (case-insensitive) raises
- Max 20 groups per order

- [ ] **Step 2-5: Standard TDD cycle, commit**

```bash
git commit -m "feat: add group CRUD methods to OrderRepository"
```

---

### Task 4: Order Service — Group + Quantity Logic

**Files:**
- Modify: `app/services/order_service.py`
- Test: `tests/unit/test_order_groups_service.py`

- [ ] **Step 1: Write failing tests** (mocked repos)

Groups:
- create_group: checks order is draft, validates name
- delete_group: checks empty
- assign_item_to_group: checks group belongs to same order

Quantity:
- add_item with quantity=3: stores quantity + instance_parameters
- add_item with quantity>1 but no per_instance param in template → error
- validate_order: validates shared params once, validates instance_parameters per instance
- submit_order with quantity=3: expands to 3 dispatch events
- export_tofu with quantity=3: generates 3 export blocks

Per-Instance:
- validate instance_parameters: each set must have all per_instance=true params
- auto params not in instance_parameters (generated at submit)

- [ ] **Step 2-5: Standard TDD cycle, commit**

```bash
git commit -m "feat: add group management and quantity expansion to OrderService"
```

---

### Task 5: Group API Endpoints

**Files:**
- Modify: `app/api/v1/orders.py`
- Test: `tests/integration/test_order_groups_api.py`

- [ ] **Step 1: Write failing tests**

Endpoints:
- POST /api/v1/orders/{id}/groups → create group (201)
- PATCH /api/v1/orders/{id}/groups/{gid} → update (200)
- DELETE /api/v1/orders/{id}/groups/{gid} → delete empty (204), non-empty (409)
- PUT /api/v1/orders/{id}/groups/reorder → reorder (200)
- PATCH /api/v1/orders/{id}/items/{iid} with group_id → assign to group (200)
- GET /api/v1/orders/{id} → response includes groups[] and ungrouped_items[]
- Only in draft (422 otherwise)
- Max 20 groups (400)
- Duplicate name (409)

- [ ] **Step 2-5: Standard TDD cycle, commit**

```bash
git commit -m "feat: add group CRUD API endpoints for orders"
```

---

### Task 6: Quantity API — Add Item with Quantity + Instance Params

**Files:**
- Modify: `app/api/v1/orders.py`
- Test: `tests/integration/test_order_quantity_api.py`

- [ ] **Step 1: Write failing tests**

- POST /api/v1/orders/{id}/items with quantity=3 + instance_parameters → 201
- POST with quantity=3 but template has no per_instance params → 400
- POST with quantity=1 (default, backwards compatible) → 201
- GET order shows items with quantity and instance_parameters
- Validate order with quantity>1 → validates shared + per-instance
- Submit order with quantity=3 → order has 3 expanded dispatch references
- Export with quantity=3 → 3 tofu blocks

Needs a template with per_instance params seeded in test fixture.

- [ ] **Step 2-5: Standard TDD cycle, commit**

```bash
git commit -m "feat: add quantity and instance_parameters support to order items API"
```

---

### Task 7: Per-Instance Parameters API

**Files:**
- Modify: `app/api/v1/orders.py`
- Modify: `app/api/v1/catalog.py` (template registration accepts per_instance)
- Test: `tests/integration/test_per_instance_api.py`

- [ ] **Step 1: Write failing tests**

- Register template with per_instance params (admin)
- GET template detail shows per_instance field
- POST /api/v1/catalog/templates/{slug}/parameter-layout?quantity=3 → returns resolved layout (shared vs per-instance sections)
- Add item with per_instance=true params: must provide instance_parameters
- Validate: missing instance param → violation per instance
- Auto params (hostname): not in request, generated at submit

- [ ] **Step 2-5: Standard TDD cycle, commit**

```bash
git commit -m "feat: add per-instance parameter support to catalog and order validation"
```

---

### Task 8: E2E Test — Full Groups + Quantity Flow

**Files:**
- Test: `tests/e2e/test_groups_quantity_e2e.py`

- [ ] **Step 1: Write comprehensive E2E test**

End-to-end flow:
1. Register template with per_instance params (hostname=auto, custom_tag=true, cpu=false)
2. Create order
3. Create group "Web-Cluster"
4. Add item to group with quantity=3, instance_parameters for custom_tag per instance
5. Add standalone DB item (no group, quantity=1)
6. Validate → all valid
7. Submit → order submitted
8. Export → 4 tofu blocks (3 VMs + 1 DB), each VM has unique instance params
9. Verify group structure in GET order response

- [ ] **Step 2: Run, fix, commit**

```bash
git commit -m "test: add E2E test for groups + quantity + per-instance parameters"
```

---

### Task 9: Frontend — Types + API Extensions

**Files:**
- Modify: `frontend/src/types/order.ts`
- Modify: `frontend/src/api/orders.ts`
- Modify: `frontend/src/hooks/useOrders.ts`

- [ ] **Step 1: Extend types**

Add to order.ts:
- OrderItemGroup: { id, order_id, name, description, position }
- Extend OrderItem: + group_id, quantity, instance_parameters
- Extend Order: + groups[]

Add to orders API:
- createGroup, updateGroup, deleteGroup, reorderGroups
- addItem now accepts quantity + instance_parameters

Add hooks: useCreateGroup, useDeleteGroup

- [ ] **Step 2: Commit**

```bash
git commit -m "feat(frontend): extend order types and API for groups + quantity"
```

---

### Task 10: Frontend — Group UI + Quantity Selector

**Files:**
- Create: `frontend/src/components/orders/GroupSection.tsx`
- Create: `frontend/src/components/orders/QuantitySelector.tsx`
- Modify: `frontend/src/components/orders/OrderItemCard.tsx`
- Modify: `frontend/src/pages/OrderDetail.tsx`
- Test: `frontend/tests/pages/OrderDetailGroups.test.tsx`

- [ ] **Step 1: Implement GroupSection**

Collapsible container with group name header, item count badge, add-item button. Contains OrderItemCards for items in this group.

- [ ] **Step 2: Implement QuantitySelector**

Number input (1-50) in the add-item drawer. When quantity>1: shows expandable per-instance section below shared params. Auto params show "(wird automatisch vergeben)".

- [ ] **Step 3: Update OrderDetail**

Layout changes:
- "Neue Gruppe" button next to "+ Service hinzufügen"
- Groups rendered as GroupSection components
- Ungrouped items below groups
- Drawer for add-item includes optional group selector + quantity

- [ ] **Step 4: Update OrderItemCard**

Show group badge, quantity badge (×3), instance count.

- [ ] **Step 5: Write test, run, commit**

```bash
git commit -m "feat(frontend): add group sections, quantity selector, and per-instance UI"
```

---

### Task 11: Final Verification

- [ ] **Step 1: Run backend tests**

Run: `pytest tests/ -v --tb=short`

- [ ] **Step 2: Run frontend tests**

Run: `cd frontend && npx vitest run`

- [ ] **Step 3: Type check frontend**

Run: `npx tsc --noEmit`

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: phase 8 complete — order groups, quantity, per-instance parameters"
```
