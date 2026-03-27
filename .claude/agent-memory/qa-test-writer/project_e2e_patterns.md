---
name: E2E test patterns for lucent-app-mpp-TDD
description: Key behavioral facts discovered when writing E2E integration tests — response shapes, validator rules, stub data counts
type: project
---

TemplateValidator rejects templates with empty `parameters: []` — every registered template must have at least one `required: True` parameter. Error: "Ein Template muss mindestens einen Pflichtparameter definieren." Validation fires before the duplicate-check in the repository.

**Why:** TemplateValidator.validate_template() calls `has_required = any(p.get("required") for p in parameters)` and appends an error if False. The duplicate IntegrityError in the repo is therefore never reached when the payload has no parameters.

**How to apply:** All test fixtures that register templates must include at least one parameter with `required: True`. The LINUX_VM and POSTGRES_DB fixtures in conftest.py already satisfy this. Any new ad-hoc template registrations in tests need the same.

---

Validation violation structure uses `parameter_key` (not `field` or `parameter`) as the key identifying which parameter failed. Example: `{"parameter_key": "cpu_cores", "message": "...", "rule": "VAL-constraints"}`.

**Why:** The order validation service serialises violations with this shape; the API passes them through unchanged in `item_results[n]["violations"]`.

**How to apply:** When asserting specific parameter violations, use `v.get("parameter_key")`, not `v.get("field")`.

---

`list_orders` API response uses key `"items"` (not `"data"`). Catalog templates use `"data"`. Admin audit-log also uses `"items"`.

**Why:** Inconsistent naming between blueprint authors. Orders blueprint: `{"items": [...], "total": ...}`. Catalog: `{"data": [...], "total": ...}`.

**How to apply:** Check the blueprint source before asserting response keys.

---

CMDB stub data counts (stubs/cmdb/): 3 locations (loc-berlin, loc-munich, loc-hamburg), 7 networks total (3 Berlin, 2 Munich, 2 Hamburg), 3 security zones (sz-low, sz-medium, sz-high), 2 tenants (ten-corp, ten-dev). sz-high only has a network at loc-berlin (net-ber-mgmt) — testing zone-not-at-location uses loc-hamburg + sz-high.

---

E2E fixture scope is `function` (not `session` or `module`) — each test gets a full schema drop_all/create_all for complete isolation. This adds ~0.3s per test but prevents cross-test state leakage.
