# Phase 2: Service Catalog — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Service Catalog with ServiceTemplate CRUD, parameter validation, dynamic option resolution, version diffing, and category listing — the foundation for order creation in Phase 3.

**Architecture:** Domain models in `app/domain/catalog.py`, SQLAlchemy models in `app/data/db/models/`, repository pattern for persistence, service layer for business logic, Flask blueprints for API. Templates are stored as JSON blobs for parameters/constraints (flexible schema) with indexed columns for filtering.

**Tech Stack:** Flask, SQLAlchemy, PostgreSQL (JSONB for parameters), Alembic migrations, pytest

**Spec:** `docs/specs/service-catalog.md` — REQ-100 to REQ-125, VAL-47 to VAL-71, EC-66 to EC-80, Endpoints 37-44

---

## File Structure (new/modified files)

```
app/
├── domain/
│   └── catalog.py                  # Domain models: ServiceTemplate, ParameterDefinition, enums
├── data/
│   ├── db/
│   │   └── models/
│   │       ├── __init__.py
│   │       └── service_template.py # SQLAlchemy model
│   └── repositories/
│       ├── __init__.py
│       └── template_repository.py  # CRUD + query operations
├── services/
│   ├── catalog_service.py          # Business logic: register, validate, resolve options
│   └── template_validator.py       # Template registration validation (VAL-47..71)
└── api/
    └── v1/
        └── catalog.py              # Blueprint: 8 endpoints

tests/
├── unit/
│   ├── test_catalog_domain.py
│   ├── test_template_validator.py
│   └── test_catalog_service.py
└── integration/
    ├── test_catalog_api.py
    ├── test_catalog_admin_api.py
    └── test_catalog_validation_api.py
```

---

### Task 1: Domain Models — ServiceTemplate, Enums, ParameterDefinition

**Files:**
- Create: `app/domain/catalog.py`
- Test: `tests/unit/test_catalog_domain.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_catalog_domain.py
import pytest
from app.domain.catalog import (
    ServiceType, TemplateStatus, ParameterType,
    ParameterDefinition, DependencyRule, CrossParameterRule,
    ServiceTemplate,
)


class TestServiceTypeEnum:
    def test_valid_types(self):
        assert ServiceType.VM == "vm"
        assert ServiceType.DATABASE == "database"
        assert ServiceType.CONTAINER == "container"
        assert ServiceType.STORAGE == "storage"
        assert ServiceType.NETWORK == "network"
        assert ServiceType.CUSTOM == "custom"

    def test_is_valid(self):
        assert ServiceType.is_valid("vm") is True
        assert ServiceType.is_valid("unknown") is False


class TestTemplateStatusEnum:
    def test_valid_statuses(self):
        assert TemplateStatus.ACTIVE == "active"
        assert TemplateStatus.DEPRECATED == "deprecated"
        assert TemplateStatus.DISABLED == "disabled"

    def test_allowed_transitions(self):
        assert TemplateStatus.can_transition("active", "deprecated") is True
        assert TemplateStatus.can_transition("active", "disabled") is True
        assert TemplateStatus.can_transition("deprecated", "disabled") is True
        assert TemplateStatus.can_transition("disabled", "active") is False
        assert TemplateStatus.can_transition("deprecated", "active") is False


class TestParameterType:
    def test_all_types(self):
        expected = {"string", "integer", "float", "boolean", "enum",
                    "range_integer", "range_float", "size_bytes"}
        assert set(ParameterType.all()) == expected


class TestDependencyRule:
    def test_evaluate_eq(self):
        rule = DependencyRule(parameter_key="os_type", operator="eq",
                              value="windows", effect="visible")
        assert rule.evaluate({"os_type": "windows"}) is True
        assert rule.evaluate({"os_type": "linux"}) is False

    def test_evaluate_neq(self):
        rule = DependencyRule(parameter_key="os_type", operator="neq",
                              value=None, effect="visible")
        assert rule.evaluate({"os_type": "linux"}) is True
        assert rule.evaluate({"os_type": None}) is False

    def test_evaluate_in(self):
        rule = DependencyRule(parameter_key="tier", operator="in",
                              value=["medium", "large"], effect="visible")
        assert rule.evaluate({"tier": "medium"}) is True
        assert rule.evaluate({"tier": "small"}) is False

    def test_evaluate_gt(self):
        rule = DependencyRule(parameter_key="cpu", operator="gt",
                              value=4, effect="required")
        assert rule.evaluate({"cpu": 8}) is True
        assert rule.evaluate({"cpu": 4}) is False

    def test_evaluate_missing_key(self):
        rule = DependencyRule(parameter_key="missing", operator="eq",
                              value="x", effect="visible")
        assert rule.evaluate({}) is False


class TestParameterDefinition:
    def test_is_visible_no_depends(self):
        param = ParameterDefinition(
            key="cpu", label="CPU", type="integer", required=True,
            tofu_variable_name="cpu_cores", display_order=1,
            constraints={"min": 1, "max": 64},
        )
        assert param.is_visible({}) is True

    def test_is_visible_with_depends(self):
        param = ParameterDefinition(
            key="disk_type", label="Disk", type="enum", required=True,
            tofu_variable_name="disk_type", display_order=2,
            constraints={"options": []},
            depends_on=[DependencyRule(parameter_key="os_type",
                                       operator="neq", value=None,
                                       effect="visible")],
        )
        assert param.is_visible({"os_type": "linux"}) is True
        assert param.is_visible({"os_type": None}) is False
        assert param.is_visible({}) is False
```

- [ ] **Step 2: Run tests — verify FAIL**

Run: `source venv/bin/activate && pytest tests/unit/test_catalog_domain.py -v`

- [ ] **Step 3: Implement domain models**

```python
# app/domain/catalog.py
from dataclasses import dataclass, field
from typing import Any


class ServiceType:
    VM = "vm"
    DATABASE = "database"
    CONTAINER = "container"
    STORAGE = "storage"
    NETWORK = "network"
    CUSTOM = "custom"

    _ALL = {VM, DATABASE, CONTAINER, STORAGE, NETWORK, CUSTOM}

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls._ALL

    @classmethod
    def all(cls) -> set[str]:
        return cls._ALL.copy()


class TemplateStatus:
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"

    _TRANSITIONS = {
        "active": {"deprecated", "disabled"},
        "deprecated": {"disabled"},
        "disabled": set(),
    }

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        return to_status in cls._TRANSITIONS.get(from_status, set())


class ParameterType:
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ENUM = "enum"
    RANGE_INTEGER = "range_integer"
    RANGE_FLOAT = "range_float"
    SIZE_BYTES = "size_bytes"

    _ALL = {STRING, INTEGER, FLOAT, BOOLEAN, ENUM, RANGE_INTEGER, RANGE_FLOAT, SIZE_BYTES}

    @classmethod
    def all(cls) -> set[str]:
        return cls._ALL.copy()

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls._ALL


@dataclass
class DependencyRule:
    parameter_key: str
    operator: str
    value: Any
    effect: str  # "visible" | "required" | "disabled"

    VALID_OPERATORS = {"eq", "neq", "in", "not_in", "gt", "lt", "gte", "lte"}
    VALID_EFFECTS = {"visible", "required", "disabled"}

    def evaluate(self, current_values: dict) -> bool:
        if self.parameter_key not in current_values:
            return False
        actual = current_values[self.parameter_key]
        op = self.operator
        if op == "eq":
            return actual == self.value
        elif op == "neq":
            return actual != self.value
        elif op == "in":
            return actual in self.value
        elif op == "not_in":
            return actual not in self.value
        elif op == "gt":
            return actual > self.value
        elif op == "lt":
            return actual < self.value
        elif op == "gte":
            return actual >= self.value
        elif op == "lte":
            return actual <= self.value
        return False


@dataclass
class CrossParameterRule:
    rule_id: str
    description: str
    parameter_keys: list[str]
    expression: str
    error_message: str


@dataclass
class ParameterDefinition:
    key: str
    label: str
    type: str
    required: bool
    tofu_variable_name: str
    display_order: int
    constraints: dict = field(default_factory=dict)
    description: str | None = None
    default_value: Any = None
    group: str | None = None
    depends_on: list[DependencyRule] = field(default_factory=list)
    affects_options_of: list[str] = field(default_factory=list)

    def is_visible(self, current_values: dict) -> bool:
        visibility_rules = [r for r in self.depends_on if r.effect == "visible"]
        if not visibility_rules:
            return True
        return all(r.evaluate(current_values) for r in visibility_rules)

    def is_required(self, current_values: dict) -> bool:
        if self.required:
            return True
        required_rules = [r for r in self.depends_on if r.effect == "required"]
        if not required_rules:
            return False
        return any(r.evaluate(current_values) for r in required_rules)


@dataclass
class ServiceTemplate:
    id: str
    slug: str
    version: str
    type: str
    display_name: str
    description: str
    category: str
    tofu_module_source: str
    parameters: list[ParameterDefinition] = field(default_factory=list)
    cross_parameter_rules: list[CrossParameterRule] = field(default_factory=list)
    status: str = TemplateStatus.ACTIVE
    icon_identifier: str | None = None
    created_at: str | None = None
    deprecated_at: str | None = None
    deprecated_by: str | None = None
    estimated_cost_eur_per_month: float | None = None
    approval_always_required: bool = False
    metadata: dict = field(default_factory=dict)
```

- [ ] **Step 4: Run tests — verify PASS**

Run: `pytest tests/unit/test_catalog_domain.py -v`

- [ ] **Step 5: Run ALL tests**

Run: `pytest tests/ -v`

- [ ] **Step 6: Commit**

```bash
git add app/domain/catalog.py tests/unit/test_catalog_domain.py
git commit -m "feat: add Service Catalog domain models (ServiceTemplate, ParameterDefinition, DependencyRule)"
```

---

### Task 2: Template Validator — Registration Validation (VAL-47..71)

**Files:**
- Create: `app/services/template_validator.py`
- Test: `tests/unit/test_template_validator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_template_validator.py
import pytest
from app.services.template_validator import TemplateValidator


class TestSlugValidation:
    def test_valid_slug(self):
        v = TemplateValidator()
        assert v.validate_slug("vm-linux") == []

    def test_slug_too_short(self):
        v = TemplateValidator()
        errors = v.validate_slug("ab")
        assert len(errors) == 1
        assert "3" in errors[0] or "alphanumerisch" in errors[0].lower() or "Slug" in errors[0]

    def test_slug_with_uppercase(self):
        v = TemplateValidator()
        errors = v.validate_slug("VM-Linux")
        assert len(errors) >= 1

    def test_slug_starting_with_dash(self):
        v = TemplateValidator()
        errors = v.validate_slug("-vm-linux")
        assert len(errors) >= 1


class TestVersionValidation:
    def test_valid_semver(self):
        v = TemplateValidator()
        assert v.validate_version("1.0.0") == []
        assert v.validate_version("2.1.3") == []

    def test_invalid_semver(self):
        v = TemplateValidator()
        errors = v.validate_version("1.0")
        assert len(errors) >= 1

    def test_semver_with_prerelease(self):
        v = TemplateValidator()
        assert v.validate_version("1.0.0-alpha") == []


class TestServiceTypeValidation:
    def test_valid_type(self):
        v = TemplateValidator()
        assert v.validate_service_type("vm") == []

    def test_invalid_type(self):
        v = TemplateValidator()
        errors = v.validate_service_type("invalid")
        assert len(errors) >= 1


class TestParameterValidation:
    def test_valid_parameter(self):
        v = TemplateValidator()
        param = {
            "key": "cpu_cores",
            "label": "CPU Cores",
            "type": "integer",
            "required": True,
            "tofu_variable_name": "cpu_cores",
            "display_order": 1,
            "constraints": {"min": 1, "max": 64},
        }
        assert v.validate_parameter(param, existing_keys=set(), existing_tofu_names=set()) == []

    def test_duplicate_key(self):
        v = TemplateValidator()
        param = {
            "key": "cpu_cores",
            "label": "CPU",
            "type": "integer",
            "required": True,
            "tofu_variable_name": "cpu",
            "display_order": 1,
            "constraints": {},
        }
        errors = v.validate_parameter(param, existing_keys={"cpu_cores"}, existing_tofu_names=set())
        assert any("eindeutig" in e.lower() or "unique" in e.lower() or "key" in e.lower() for e in errors)

    def test_invalid_parameter_type(self):
        v = TemplateValidator()
        param = {
            "key": "test",
            "label": "Test",
            "type": "invalid_type",
            "required": True,
            "tofu_variable_name": "test",
            "display_order": 1,
            "constraints": {},
        }
        errors = v.validate_parameter(param, existing_keys=set(), existing_tofu_names=set())
        assert len(errors) >= 1


class TestFullTemplateValidation:
    def test_valid_template(self):
        v = TemplateValidator()
        template_data = {
            "slug": "vm-linux",
            "version": "1.0.0",
            "type": "vm",
            "display_name": "Linux VM",
            "description": "A Linux VM.",
            "category": "Compute",
            "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
            "parameters": [
                {
                    "key": "cpu",
                    "label": "CPU",
                    "type": "integer",
                    "required": True,
                    "tofu_variable_name": "cpu_cores",
                    "display_order": 1,
                    "constraints": {"min": 1, "max": 64},
                }
            ],
        }
        errors = v.validate_template(template_data)
        assert errors == []

    def test_template_no_required_parameter(self):
        v = TemplateValidator()
        template_data = {
            "slug": "vm-linux",
            "version": "1.0.0",
            "type": "vm",
            "display_name": "Linux VM",
            "description": "A Linux VM.",
            "category": "Compute",
            "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
            "parameters": [
                {
                    "key": "optional",
                    "label": "Optional",
                    "type": "string",
                    "required": False,
                    "tofu_variable_name": "opt",
                    "display_order": 1,
                    "constraints": {},
                }
            ],
        }
        errors = v.validate_template(template_data)
        assert any("Pflichtparameter" in e or "required" in e.lower() for e in errors)

    def test_template_missing_display_name(self):
        v = TemplateValidator()
        template_data = {
            "slug": "vm-linux",
            "version": "1.0.0",
            "type": "vm",
            "display_name": "",
            "category": "Compute",
            "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
            "parameters": [
                {
                    "key": "cpu",
                    "label": "CPU",
                    "type": "integer",
                    "required": True,
                    "tofu_variable_name": "cpu",
                    "display_order": 1,
                    "constraints": {},
                }
            ],
        }
        errors = v.validate_template(template_data)
        assert len(errors) >= 1

    def test_invalid_tofu_module_source(self):
        v = TemplateValidator()
        template_data = {
            "slug": "vm-linux",
            "version": "1.0.0",
            "type": "vm",
            "display_name": "Linux VM",
            "category": "Compute",
            "tofu_module_source": "not-a-valid-source",
            "parameters": [
                {
                    "key": "cpu",
                    "label": "CPU",
                    "type": "integer",
                    "required": True,
                    "tofu_variable_name": "cpu",
                    "display_order": 1,
                    "constraints": {},
                }
            ],
        }
        errors = v.validate_template(template_data)
        assert any("Tofu" in e or "Modulquelle" in e or "source" in e.lower() for e in errors)

    def test_cross_parameter_rule_references_missing_key(self):
        v = TemplateValidator()
        template_data = {
            "slug": "vm-linux",
            "version": "1.0.0",
            "type": "vm",
            "display_name": "Linux VM",
            "category": "Compute",
            "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
            "parameters": [
                {
                    "key": "cpu",
                    "label": "CPU",
                    "type": "integer",
                    "required": True,
                    "tofu_variable_name": "cpu",
                    "display_order": 1,
                    "constraints": {},
                }
            ],
            "cross_parameter_rules": [
                {
                    "rule_id": "bad-rule",
                    "description": "Bad rule",
                    "parameter_keys": ["cpu", "nonexistent"],
                    "expression": "cpu > 1",
                    "error_message": "Bad",
                }
            ],
        }
        errors = v.validate_template(template_data)
        assert any("nonexistent" in e or "nicht existierenden" in e for e in errors)
```

- [ ] **Step 2: Run tests — verify FAIL**

- [ ] **Step 3: Implement TemplateValidator**

```python
# app/services/template_validator.py
import re
from app.domain.catalog import ServiceType, ParameterType

SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?$"
)
KEY_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
TOFU_SOURCE_PATTERNS = [
    re.compile(r"^\./"),
    re.compile(r"^registry\.terraform\.io/"),
    re.compile(r"^git::https://"),
]


class TemplateValidator:
    def validate_slug(self, slug: str) -> list[str]:
        if not SLUG_PATTERN.match(slug or ""):
            return [
                "Slug darf nur Kleinbuchstaben, Ziffern und Bindestriche enthalten "
                "und muss mit einem alphanumerischen Zeichen beginnen und enden (3-64 Zeichen)."
            ]
        return []

    def validate_version(self, version: str) -> list[str]:
        if not SEMVER_PATTERN.match(version or ""):
            return ["Versionsformat ungültig. Erwartet: MAJOR.MINOR.PATCH (z.B. '1.0.0')."]
        return []

    def validate_service_type(self, service_type: str) -> list[str]:
        if not ServiceType.is_valid(service_type or ""):
            return [
                f"Unbekannter Service-Typ. Erlaubte Werte: "
                f"{', '.join(sorted(ServiceType.all()))}."
            ]
        return []

    def validate_display_name(self, name: str) -> list[str]:
        if not name or len(name) < 3 or len(name) > 100:
            return ["Anzeigename muss zwischen 3 und 100 Zeichen lang sein."]
        return []

    def validate_description(self, desc: str | None) -> list[str]:
        if desc and len(desc) > 500:
            return ["Beschreibung darf maximal 500 Zeichen lang sein."]
        return []

    def validate_tofu_module_source(self, source: str) -> list[str]:
        if not source:
            return ["Ungültige Tofu-Modulquelle. Erlaubte Formate: lokaler Pfad, Terraform Registry oder Git-URL."]
        if not any(p.match(source) for p in TOFU_SOURCE_PATTERNS):
            return ["Ungültige Tofu-Modulquelle. Erlaubte Formate: lokaler Pfad, Terraform Registry oder Git-URL."]
        return []

    def validate_parameter(self, param: dict, existing_keys: set[str],
                           existing_tofu_names: set[str]) -> list[str]:
        errors = []
        key = param.get("key", "")
        if not KEY_PATTERN.match(key):
            errors.append(
                f"Parameterschlüssel '{key}' darf nur Kleinbuchstaben, Ziffern und "
                "Unterstriche enthalten und muss mit einem Buchstaben oder Unterstrich beginnen."
            )
        if key in existing_keys:
            errors.append(f"Parameterschlüssel '{key}' muss innerhalb des Templates eindeutig sein.")

        tofu_name = param.get("tofu_variable_name", "")
        if not KEY_PATTERN.match(tofu_name):
            errors.append(f"Tofu-Variablenname '{tofu_name}' muss snake_case sein.")
        if tofu_name in existing_tofu_names:
            errors.append(f"Tofu-Variablenname '{tofu_name}' muss innerhalb des Templates eindeutig sein.")

        param_type = param.get("type", "")
        if not ParameterType.is_valid(param_type):
            errors.append(
                f"Unbekannter Parametertyp '{param_type}'. Erlaubte Werte: "
                f"{', '.join(sorted(ParameterType.all()))}."
            )
        return errors

    def validate_template(self, data: dict) -> list[str]:
        errors = []
        errors.extend(self.validate_slug(data.get("slug", "")))
        errors.extend(self.validate_version(data.get("version", "")))
        errors.extend(self.validate_service_type(data.get("type", "")))
        errors.extend(self.validate_display_name(data.get("display_name", "")))
        errors.extend(self.validate_description(data.get("description")))
        errors.extend(self.validate_tofu_module_source(data.get("tofu_module_source", "")))

        cost = data.get("estimated_cost_eur_per_month")
        if cost is not None:
            if not isinstance(cost, (int, float)) or cost <= 0:
                errors.append("Die geschätzten monatlichen Kosten müssen ein positiver EUR-Betrag sein.")

        parameters = data.get("parameters", [])
        existing_keys: set[str] = set()
        existing_tofu_names: set[str] = set()
        for param in parameters:
            errors.extend(self.validate_parameter(param, existing_keys, existing_tofu_names))
            existing_keys.add(param.get("key", ""))
            existing_tofu_names.add(param.get("tofu_variable_name", ""))

        has_required = any(p.get("required") for p in parameters)
        if not has_required:
            errors.append("Ein Template muss mindestens einen Pflichtparameter definieren.")

        param_keys = {p.get("key") for p in parameters}
        for rule in data.get("cross_parameter_rules", []):
            for ref_key in rule.get("parameter_keys", []):
                if ref_key not in param_keys:
                    errors.append(
                        f"Kombinationsregel '{rule.get('rule_id')}' referenziert "
                        f"einen nicht existierenden Parameter '{ref_key}'."
                    )
        return errors
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests**
- [ ] **Step 6: Commit**

```bash
git add app/services/template_validator.py tests/unit/test_template_validator.py
git commit -m "feat: add TemplateValidator for registration validation (VAL-47..71)"
```

---

### Task 3: Database Model + Migration

**Files:**
- Create: `app/data/db/models/__init__.py`
- Create: `app/data/db/models/service_template.py`
- Test: `tests/integration/test_template_db_model.py`

- [ ] **Step 1: Write failing test**

```python
# tests/integration/test_template_db_model.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import text
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.db.models.service_template import ServiceTemplateModel


class TestServiceTemplateModel:
    def setup_method(self):
        self.engine = get_engine("postgresql://mpp:mpp@localhost:5432/mpp_test")
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.Session = get_session_factory(self.engine)

    def teardown_method(self):
        Base.metadata.drop_all(self.engine)

    def test_create_template(self):
        session = self.Session()
        template = ServiceTemplateModel(
            id=str(uuid.uuid4()),
            slug="vm-linux",
            version="1.0.0",
            type="vm",
            display_name="Linux VM",
            description="A test VM.",
            category="Compute",
            tofu_module_source="git::https://gitlab.internal/tofu/vm.git",
            parameters=[
                {
                    "key": "cpu_cores",
                    "label": "CPU",
                    "type": "integer",
                    "required": True,
                    "tofu_variable_name": "cpu_cores",
                    "display_order": 1,
                    "constraints": {"min": 1, "max": 64},
                }
            ],
            cross_parameter_rules=[],
            status="active",
        )
        session.add(template)
        session.commit()

        loaded = session.query(ServiceTemplateModel).filter_by(slug="vm-linux").first()
        assert loaded is not None
        assert loaded.version == "1.0.0"
        assert loaded.parameters[0]["key"] == "cpu_cores"
        session.close()

    def test_unique_constraint_slug_version(self):
        session = self.Session()
        t1 = ServiceTemplateModel(
            id=str(uuid.uuid4()), slug="vm-linux", version="1.0.0",
            type="vm", display_name="VM 1", category="Compute",
            tofu_module_source="git::https://gitlab.internal/tofu/vm.git",
            parameters=[{"key": "cpu", "label": "CPU", "type": "integer",
                         "required": True, "tofu_variable_name": "cpu",
                         "display_order": 1, "constraints": {}}],
            cross_parameter_rules=[], status="active",
        )
        t2 = ServiceTemplateModel(
            id=str(uuid.uuid4()), slug="vm-linux", version="1.0.0",
            type="vm", display_name="VM 2", category="Compute",
            tofu_module_source="git::https://gitlab.internal/tofu/vm.git",
            parameters=[{"key": "cpu", "label": "CPU", "type": "integer",
                         "required": True, "tofu_variable_name": "cpu",
                         "display_order": 1, "constraints": {}}],
            cross_parameter_rules=[], status="active",
        )
        session.add(t1)
        session.commit()
        session.add(t2)
        from sqlalchemy.exc import IntegrityError
        import pytest
        with pytest.raises(IntegrityError):
            session.commit()
        session.close()
```

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement SQLAlchemy model**

```python
# app/data/db/models/__init__.py
from app.data.db.models.service_template import ServiceTemplateModel
```

```python
# app/data/db/models/service_template.py
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Boolean, Numeric, DateTime, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from app.data.db.session import Base


class ServiceTemplateModel(Base):
    __tablename__ = "service_templates"

    id = Column(String(36), primary_key=True)
    slug = Column(String(64), nullable=False, index=True)
    version = Column(String(32), nullable=False)
    type = Column(String(32), nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(64), nullable=False, index=True)
    icon_identifier = Column(String(100), nullable=True)
    tofu_module_source = Column(String(500), nullable=False)
    parameters = Column(JSONB, nullable=False, default=list)
    cross_parameter_rules = Column(JSONB, nullable=False, default=list)
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deprecated_at = Column(DateTime(timezone=True), nullable=True)
    deprecated_by = Column(String(36), nullable=True)
    estimated_cost_eur_per_month = Column(Numeric(10, 2), nullable=True)
    approval_always_required = Column(Boolean, default=False, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)

    __table_args__ = (
        UniqueConstraint("slug", "version", name="uq_template_slug_version"),
        Index("ix_template_slug_status", "slug", "status"),
    )
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Create Alembic migration**

Run: `source venv/bin/activate && alembic revision --autogenerate -m "add service_templates table"`
Run: `alembic upgrade head`

- [ ] **Step 6: Run ALL tests**
- [ ] **Step 7: Commit**

```bash
git add app/data/db/models/ migrations/ tests/integration/test_template_db_model.py
git commit -m "feat: add ServiceTemplate database model with JSONB parameters and unique constraint"
```

---

### Task 4: Template Repository — CRUD + Query

**Files:**
- Create: `app/data/repositories/__init__.py`
- Create: `app/data/repositories/template_repository.py`
- Test: `tests/integration/test_template_repository.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_template_repository.py
import uuid
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.template_repository import TemplateRepository


@pytest.fixture
def repo():
    engine = get_engine("postgresql://mpp:mpp@localhost:5432/mpp_test")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    yield TemplateRepository(session)
    session.close()
    Base.metadata.drop_all(engine)


def _make_template(**overrides):
    defaults = {
        "slug": "vm-linux",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Linux VM",
        "description": "Test",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "cpu", "display_order": 1, "constraints": {"min": 1, "max": 64}}
        ],
    }
    defaults.update(overrides)
    return defaults


class TestTemplateRepository:
    def test_create_and_get_by_slug(self, repo):
        data = _make_template()
        created = repo.create(data)
        assert created.slug == "vm-linux"
        assert created.id is not None

        loaded = repo.get_by_slug("vm-linux")
        assert loaded is not None
        assert loaded.version == "1.0.0"

    def test_get_by_slug_and_version(self, repo):
        repo.create(_make_template(version="1.0.0"))
        repo.create(_make_template(version="2.0.0"))

        v1 = repo.get_by_slug_and_version("vm-linux", "1.0.0")
        assert v1 is not None
        assert v1.version == "1.0.0"

    def test_get_by_slug_returns_latest_active(self, repo):
        repo.create(_make_template(version="1.0.0"))
        repo.create(_make_template(version="2.0.0"))

        latest = repo.get_by_slug("vm-linux")
        assert latest.version == "2.0.0"

    def test_list_with_filters(self, repo):
        repo.create(_make_template(slug="vm-linux", type="vm", category="Compute"))
        repo.create(_make_template(slug="db-postgres", type="database", category="Database",
                                    display_name="PostgreSQL DB",
                                    tofu_module_source="git::https://gitlab.internal/tofu/db.git"))

        result = repo.list_templates(type_filter="vm")
        assert len(result["data"]) == 1
        assert result["data"][0].slug == "vm-linux"

    def test_list_with_search(self, repo):
        repo.create(_make_template(slug="vm-linux", display_name="Linux Virtual Machine"))
        repo.create(_make_template(slug="db-postgres", display_name="PostgreSQL DB",
                                    type="database", category="Database",
                                    tofu_module_source="git::https://gitlab.internal/tofu/db.git"))

        result = repo.list_templates(search="linux")
        assert len(result["data"]) == 1

    def test_list_pagination(self, repo):
        for i in range(5):
            repo.create(_make_template(slug=f"vm-{i}", version="1.0.0"))
        result = repo.list_templates(limit=2, offset=0)
        assert len(result["data"]) == 2
        assert result["total"] == 5

    def test_list_versions(self, repo):
        repo.create(_make_template(version="1.0.0"))
        repo.create(_make_template(version="2.0.0"))
        versions = repo.list_versions("vm-linux")
        assert len(versions) == 2

    def test_update_status(self, repo):
        created = repo.create(_make_template())
        repo.update_status(created.id, "deprecated", deprecated_by="some-other-id")
        loaded = repo.get_by_id(created.id)
        assert loaded.status == "deprecated"

    def test_duplicate_slug_version_raises(self, repo):
        repo.create(_make_template())
        with pytest.raises(repo.DuplicateTemplateError):
            repo.create(_make_template())

    def test_get_categories(self, repo):
        repo.create(_make_template(slug="vm-1", category="Compute"))
        repo.create(_make_template(slug="db-1", type="database", category="Database",
                                    tofu_module_source="git::https://gitlab.internal/tofu/db.git"))
        categories = repo.get_categories()
        assert len(categories) == 2
        names = [c["name"] for c in categories]
        assert "Compute" in names
        assert "Database" in names
```

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement TemplateRepository**

```python
# app/data/repositories/__init__.py
```

```python
# app/data/repositories/template_repository.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.data.db.models.service_template import ServiceTemplateModel


class TemplateRepository:
    class DuplicateTemplateError(Exception):
        pass

    class TemplateNotFoundError(Exception):
        pass

    def __init__(self, session: Session):
        self.session = session

    def create(self, data: dict) -> ServiceTemplateModel:
        template = ServiceTemplateModel(
            id=str(uuid.uuid4()),
            slug=data["slug"],
            version=data["version"],
            type=data["type"],
            display_name=data["display_name"],
            description=data.get("description"),
            category=data["category"],
            icon_identifier=data.get("icon_identifier"),
            tofu_module_source=data["tofu_module_source"],
            parameters=data.get("parameters", []),
            cross_parameter_rules=data.get("cross_parameter_rules", []),
            status="active",
            estimated_cost_eur_per_month=data.get("estimated_cost_eur_per_month"),
            approval_always_required=data.get("approval_always_required", False),
            metadata_=data.get("metadata", {}),
        )
        self.session.add(template)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise self.DuplicateTemplateError(
                f"A template with slug '{data['slug']}' and version '{data['version']}' already exists."
            )
        return template

    def get_by_id(self, template_id: str) -> ServiceTemplateModel | None:
        return self.session.query(ServiceTemplateModel).filter_by(id=template_id).first()

    def get_by_slug(self, slug: str, status: str = "active") -> ServiceTemplateModel | None:
        q = (
            self.session.query(ServiceTemplateModel)
            .filter_by(slug=slug)
        )
        if status != "all":
            q = q.filter_by(status=status)
        q = q.order_by(ServiceTemplateModel.created_at.desc())
        result = q.first()
        if result is None and status == "active":
            return self.get_by_slug(slug, status="deprecated")
        return result

    def get_by_slug_and_version(self, slug: str, version: str) -> ServiceTemplateModel | None:
        return (
            self.session.query(ServiceTemplateModel)
            .filter_by(slug=slug, version=version)
            .first()
        )

    def list_templates(self, status_filter: str = "active", type_filter: str | None = None,
                       category_filter: str | None = None, search: str | None = None,
                       limit: int = 20, offset: int = 0) -> dict:
        q = self.session.query(ServiceTemplateModel)
        if status_filter and status_filter != "all":
            q = q.filter_by(status=status_filter)
        if type_filter:
            q = q.filter_by(type=type_filter)
        if category_filter:
            q = q.filter(func.lower(ServiceTemplateModel.category) == category_filter.lower())
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            q = q.filter(
                or_(
                    func.lower(ServiceTemplateModel.display_name).like(term),
                    func.lower(ServiceTemplateModel.description).like(term),
                )
            )
        total = q.count()
        data = q.order_by(ServiceTemplateModel.created_at.desc()).offset(offset).limit(limit).all()
        return {"data": data, "total": total, "limit": limit, "offset": offset}

    def list_versions(self, slug: str, status_filter: str | None = None) -> list[ServiceTemplateModel]:
        q = self.session.query(ServiceTemplateModel).filter_by(slug=slug)
        if status_filter and status_filter != "all":
            q = q.filter_by(status=status_filter)
        return q.order_by(ServiceTemplateModel.created_at.desc()).all()

    def update_status(self, template_id: str, new_status: str,
                      deprecated_by: str | None = None) -> ServiceTemplateModel:
        template = self.get_by_id(template_id)
        if template is None:
            raise self.TemplateNotFoundError(f"Template '{template_id}' not found.")
        template.status = new_status
        if new_status == "deprecated":
            template.deprecated_at = datetime.now(timezone.utc)
            template.deprecated_by = deprecated_by
        self.session.commit()
        return template

    def get_categories(self) -> list[dict]:
        results = (
            self.session.query(
                ServiceTemplateModel.category,
                func.count(ServiceTemplateModel.id),
            )
            .filter(ServiceTemplateModel.status.in_(["active", "deprecated"]))
            .group_by(ServiceTemplateModel.category)
            .all()
        )
        return [{"name": name, "template_count": count} for name, count in results]
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests**
- [ ] **Step 6: Commit**

```bash
git add app/data/repositories/ tests/integration/test_template_repository.py
git commit -m "feat: add TemplateRepository with CRUD, filtering, search, and pagination"
```

---

### Task 5: Catalog Service — Business Logic

**Files:**
- Create: `app/services/catalog_service.py`
- Test: `tests/unit/test_catalog_service.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_catalog_service.py
import pytest
from unittest.mock import MagicMock
from app.services.catalog_service import CatalogService
from app.domain.catalog import DependencyRule


class TestCatalogServiceValidateParams:
    def setup_method(self):
        self.repo = MagicMock()
        self.service = CatalogService(self.repo)

    def test_valid_integer_parameter(self):
        template_params = [
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "cpu", "display_order": 1,
             "constraints": {"min": 1, "max": 64}, "depends_on": []}
        ]
        violations = self.service.validate_parameters(template_params, {"cpu": 4}, [])
        assert violations == []

    def test_integer_out_of_range(self):
        template_params = [
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "cpu", "display_order": 1,
             "constraints": {"min": 1, "max": 64}, "depends_on": []}
        ]
        violations = self.service.validate_parameters(template_params, {"cpu": 128}, [])
        assert len(violations) == 1
        assert violations[0]["parameter_key"] == "cpu"

    def test_missing_required_parameter(self):
        template_params = [
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "cpu", "display_order": 1,
             "constraints": {}, "depends_on": []}
        ]
        violations = self.service.validate_parameters(template_params, {}, [])
        assert len(violations) == 1

    def test_invisible_parameter_skipped(self):
        template_params = [
            {"key": "disk_type", "label": "Disk", "type": "enum", "required": True,
             "tofu_variable_name": "disk_type", "display_order": 1,
             "constraints": {"options": [{"value": "ssd", "label": "SSD", "enabled": True}]},
             "depends_on": [{"parameter_key": "os", "operator": "neq", "value": None, "effect": "visible"}]}
        ]
        violations = self.service.validate_parameters(template_params, {"os": None}, [])
        assert violations == []

    def test_enum_invalid_value(self):
        template_params = [
            {"key": "os", "label": "OS", "type": "enum", "required": True,
             "tofu_variable_name": "os", "display_order": 1,
             "constraints": {"options": [
                 {"value": "linux", "label": "Linux", "enabled": True},
                 {"value": "windows", "label": "Windows", "enabled": True},
             ]}, "depends_on": []}
        ]
        violations = self.service.validate_parameters(template_params, {"os": "macos"}, [])
        assert len(violations) == 1


class TestCatalogServiceResolveOptions:
    def setup_method(self):
        self.repo = MagicMock()
        self.service = CatalogService(self.repo)

    def test_resolve_dependency_visible(self):
        depends_on = [{"parameter_key": "os", "operator": "neq", "value": None, "effect": "visible"}]
        result = self.service.resolve_dependency_state(depends_on, {"os": "linux"})
        assert result["is_visible"] is True

    def test_resolve_dependency_not_visible(self):
        depends_on = [{"parameter_key": "os", "operator": "neq", "value": None, "effect": "visible"}]
        result = self.service.resolve_dependency_state(depends_on, {})
        assert result["is_visible"] is False
```

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement CatalogService**

```python
# app/services/catalog_service.py
from app.domain.catalog import DependencyRule, ParameterDefinition


class CatalogService:
    def __init__(self, repository):
        self.repository = repository

    def validate_parameters(self, template_params: list[dict],
                            values: dict, cross_rules: list[dict]) -> list[dict]:
        violations = []
        for p in template_params:
            depends_on = [
                DependencyRule(**r) for r in p.get("depends_on", [])
            ]
            param = ParameterDefinition(
                key=p["key"], label=p["label"], type=p["type"],
                required=p["required"], tofu_variable_name=p["tofu_variable_name"],
                display_order=p["display_order"], constraints=p.get("constraints", {}),
                depends_on=depends_on,
            )
            if not param.is_visible(values):
                continue

            key = p["key"]
            value = values.get(key)

            if param.is_required(values) and value is None:
                violations.append({
                    "parameter_key": key,
                    "rule": "required",
                    "message": f"Das Feld '{p['label']}' ist ein Pflichtfeld.",
                })
                continue

            if value is None:
                continue

            violations.extend(self._validate_constraints(p, value))

        return violations

    def _validate_constraints(self, param: dict, value) -> list[dict]:
        violations = []
        constraints = param.get("constraints", {})
        ptype = param["type"]
        key = param["key"]
        label = param["label"]

        if ptype in ("integer", "float", "range_integer", "range_float"):
            min_val = constraints.get("min") if "min" in constraints else constraints.get("min_bytes")
            max_val = constraints.get("max") if "max" in constraints else constraints.get("max_bytes")
            if min_val is not None and value < min_val:
                violations.append({
                    "parameter_key": key, "rule": "VAL-constraints",
                    "message": f"Der Wert für '{label}' muss mindestens {min_val} sein.",
                })
            if max_val is not None and value > max_val:
                violations.append({
                    "parameter_key": key, "rule": "VAL-constraints",
                    "message": f"Der Wert für '{label}' darf maximal {max_val} sein.",
                })

        elif ptype == "enum":
            options = constraints.get("options", [])
            valid_values = {o["value"] for o in options if o.get("enabled", True)}
            if value not in valid_values:
                violations.append({
                    "parameter_key": key, "rule": "VAL-constraints",
                    "message": f"Der Wert '{value}' ist für das Feld '{label}' nicht zulässig.",
                })

        elif ptype == "size_bytes":
            min_b = constraints.get("min_bytes")
            max_b = constraints.get("max_bytes")
            if min_b is not None and value < min_b:
                violations.append({
                    "parameter_key": key, "rule": "VAL-constraints",
                    "message": f"Minimale Größe unterschritten.",
                })
            if max_b is not None and value > max_b:
                violations.append({
                    "parameter_key": key, "rule": "VAL-constraints",
                    "message": f"Maximale Größe überschritten.",
                })

        return violations

    def resolve_dependency_state(self, depends_on: list[dict],
                                  current_values: dict) -> dict:
        is_visible = True
        is_required = False
        is_disabled = False

        for rule_data in depends_on:
            rule = DependencyRule(**rule_data)
            result = rule.evaluate(current_values)
            if rule.effect == "visible" and not result:
                is_visible = False
            elif rule.effect == "required" and result:
                is_required = True
            elif rule.effect == "disabled" and result:
                is_disabled = True

        return {
            "is_visible": is_visible,
            "is_required": is_required,
            "is_disabled": is_disabled,
        }
```

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests**
- [ ] **Step 6: Commit**

```bash
git add app/services/catalog_service.py tests/unit/test_catalog_service.py
git commit -m "feat: add CatalogService with parameter validation and dependency resolution"
```

---

### Task 6: API Blueprint — Catalog Endpoints (Read)

**Files:**
- Create: `app/api/v1/catalog.py`
- Modify: `app/__init__.py` (register blueprint)
- Test: `tests/integration/test_catalog_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_catalog_api.py
import pytest
from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.db.models.service_template import ServiceTemplateModel
from app.data.repositories.template_repository import TemplateRepository


@pytest.fixture
def catalog_app():
    app = create_app({
        "AUTH_MODE": "stub", "ENV": "development", "TESTING": "True",
        "DATABASE_URL": "postgresql://mpp:mpp@localhost:5432/mpp_test",
    })
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    repo = TemplateRepository(session)

    repo.create({
        "slug": "vm-linux", "version": "1.0.0", "type": "vm",
        "display_name": "Linux Virtual Machine", "description": "A Linux VM.",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [
            {"key": "cpu_cores", "label": "CPU-Kerne", "type": "integer",
             "required": True, "tofu_variable_name": "cpu_cores",
             "display_order": 1, "constraints": {"min": 1, "max": 64},
             "depends_on": [], "affects_options_of": []}
        ],
    })
    repo.create({
        "slug": "db-postgres", "version": "1.0.0", "type": "database",
        "display_name": "PostgreSQL Database", "description": "A PostgreSQL instance.",
        "category": "Database",
        "tofu_module_source": "git::https://gitlab.internal/tofu/db.git",
        "parameters": [
            {"key": "db_version", "label": "Version", "type": "enum",
             "required": True, "tofu_variable_name": "pg_version",
             "display_order": 1,
             "constraints": {"options": [
                 {"value": "14", "label": "PostgreSQL 14", "enabled": True},
                 {"value": "16", "label": "PostgreSQL 16", "enabled": True},
             ]},
             "depends_on": [], "affects_options_of": []}
        ],
    })

    yield app, engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def catalog_client(catalog_app):
    app, _ = catalog_app
    return app.test_client()


@pytest.fixture
def auth_header(catalog_client):
    resp = catalog_client.post("/api/v1/auth/login",
                                json={"username": "test-requester"})
    token = resp.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


class TestCatalogList:
    def test_list_templates(self, catalog_client, auth_header):
        resp = catalog_client.get("/api/v1/catalog/templates", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "data" in data
        assert data["total"] == 2

    def test_filter_by_type(self, catalog_client, auth_header):
        resp = catalog_client.get("/api/v1/catalog/templates?type=vm", headers=auth_header)
        data = resp.get_json()
        assert data["total"] == 1
        assert data["data"][0]["slug"] == "vm-linux"

    def test_search(self, catalog_client, auth_header):
        resp = catalog_client.get("/api/v1/catalog/templates?q=linux", headers=auth_header)
        data = resp.get_json()
        assert data["total"] == 1

    def test_unauthenticated(self, catalog_client):
        resp = catalog_client.get("/api/v1/catalog/templates")
        assert resp.status_code == 401


class TestCatalogDetail:
    def test_get_template_by_slug(self, catalog_client, auth_header):
        resp = catalog_client.get("/api/v1/catalog/templates/vm-linux", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["slug"] == "vm-linux"
        assert "parameters" in data

    def test_template_not_found(self, catalog_client, auth_header):
        resp = catalog_client.get("/api/v1/catalog/templates/nonexistent", headers=auth_header)
        assert resp.status_code == 404


class TestCatalogVersions:
    def test_list_versions(self, catalog_client, auth_header):
        resp = catalog_client.get("/api/v1/catalog/templates/vm-linux/versions", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["slug"] == "vm-linux"
        assert len(data["versions"]) == 1


class TestCatalogCategories:
    def test_list_categories(self, catalog_client, auth_header):
        resp = catalog_client.get("/api/v1/catalog/categories", headers=auth_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["categories"]) == 2
```

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement catalog blueprint**

Create `app/api/v1/catalog.py` with endpoints for:
- `GET /api/v1/catalog/templates` (list with filters, search, pagination)
- `GET /api/v1/catalog/templates/{slug}` (detail with optional version param)
- `GET /api/v1/catalog/templates/{slug}/versions` (version list)
- `GET /api/v1/catalog/categories` (category list)

All endpoints require authentication (`@login_required`).

The blueprint must get a DB session from the app factory. Add session management to `app/__init__.py` using `@app.teardown_appcontext`.

Register the blueprint in `app/__init__.py`.

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests**
- [ ] **Step 6: Commit**

```bash
git add app/api/v1/catalog.py app/__init__.py tests/integration/test_catalog_api.py
git commit -m "feat: add catalog API endpoints (list, detail, versions, categories)"
```

---

### Task 7: API Blueprint — Admin Endpoints (Register Template + Update Status)

**Files:**
- Modify: `app/api/v1/catalog.py` (add admin endpoints)
- Test: `tests/integration/test_catalog_admin_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_catalog_admin_api.py
import pytest
from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base


@pytest.fixture
def admin_app():
    app = create_app({
        "AUTH_MODE": "stub", "ENV": "development", "TESTING": "True",
        "DATABASE_URL": "postgresql://mpp:mpp@localhost:5432/mpp_test",
    })
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield app, engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def admin_client(admin_app):
    app, _ = admin_app
    return app.test_client()


@pytest.fixture
def admin_header(admin_client):
    resp = admin_client.post("/api/v1/auth/login", json={"username": "test-admin"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


@pytest.fixture
def requester_header(admin_client):
    resp = admin_client.post("/api/v1/auth/login", json={"username": "test-requester"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


def _valid_template(**overrides):
    t = {
        "slug": "vm-linux",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Linux VM",
        "description": "A Linux VM.",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "cpu_cores", "display_order": 1,
             "constraints": {"min": 1, "max": 64}}
        ],
    }
    t.update(overrides)
    return t


class TestRegisterTemplate:
    def test_register_success(self, admin_client, admin_header):
        resp = admin_client.post("/api/v1/admin/catalog/templates",
                                  json=_valid_template(), headers=admin_header)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["slug"] == "vm-linux"
        assert data["status"] == "active"
        assert "id" in data

    def test_register_requires_admin(self, admin_client, requester_header):
        resp = admin_client.post("/api/v1/admin/catalog/templates",
                                  json=_valid_template(), headers=requester_header)
        assert resp.status_code == 403

    def test_register_duplicate_returns_409(self, admin_client, admin_header):
        admin_client.post("/api/v1/admin/catalog/templates",
                           json=_valid_template(), headers=admin_header)
        resp = admin_client.post("/api/v1/admin/catalog/templates",
                                  json=_valid_template(), headers=admin_header)
        assert resp.status_code == 409

    def test_register_validation_error(self, admin_client, admin_header):
        bad = _valid_template(slug="INVALID!")
        resp = admin_client.post("/api/v1/admin/catalog/templates",
                                  json=bad, headers=admin_header)
        assert resp.status_code == 400

    def test_register_no_required_param(self, admin_client, admin_header):
        bad = _valid_template(parameters=[
            {"key": "opt", "label": "Opt", "type": "string", "required": False,
             "tofu_variable_name": "opt", "display_order": 1, "constraints": {}}
        ])
        resp = admin_client.post("/api/v1/admin/catalog/templates",
                                  json=bad, headers=admin_header)
        assert resp.status_code == 400


class TestUpdateTemplateStatus:
    def test_deprecate_template(self, admin_client, admin_header):
        # Create v1 and v2
        admin_client.post("/api/v1/admin/catalog/templates",
                           json=_valid_template(version="1.0.0"), headers=admin_header)
        resp2 = admin_client.post("/api/v1/admin/catalog/templates",
                                   json=_valid_template(version="2.0.0"), headers=admin_header)
        v2_id = resp2.get_json()["id"]

        # Get v1 id
        resp1 = admin_client.get("/api/v1/catalog/templates/vm-linux?version=1.0.0",
                                  headers=admin_header)
        v1_id = resp1.get_json()["id"]

        # Deprecate v1, pointing to v2
        resp = admin_client.patch(f"/api/v1/admin/catalog/templates/{v1_id}/status",
                                   json={"status": "deprecated", "deprecated_by": v2_id},
                                   headers=admin_header)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "deprecated"

    def test_invalid_transition(self, admin_client, admin_header):
        resp = admin_client.post("/api/v1/admin/catalog/templates",
                                  json=_valid_template(), headers=admin_header)
        tid = resp.get_json()["id"]

        # Disable it
        admin_client.patch(f"/api/v1/admin/catalog/templates/{tid}/status",
                            json={"status": "disabled"}, headers=admin_header)

        # Try to deprecate disabled template
        resp = admin_client.patch(f"/api/v1/admin/catalog/templates/{tid}/status",
                                   json={"status": "deprecated"}, headers=admin_header)
        assert resp.status_code == 409
```

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Add admin endpoints to catalog blueprint**

Add to `app/api/v1/catalog.py`:
- `POST /api/v1/admin/catalog/templates` — Register new template (admin only, validates with TemplateValidator)
- `PATCH /api/v1/admin/catalog/templates/{id}/status` — Update status (admin only, validates transitions)

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests**
- [ ] **Step 6: Commit**

```bash
git add app/api/v1/catalog.py tests/integration/test_catalog_admin_api.py
git commit -m "feat: add admin catalog endpoints (register template, update status)"
```

---

### Task 8: Validation + Resolve-Options Endpoints

**Files:**
- Modify: `app/api/v1/catalog.py`
- Test: `tests/integration/test_catalog_validation_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_catalog_validation_api.py
import pytest
from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.template_repository import TemplateRepository


@pytest.fixture
def val_app():
    app = create_app({
        "AUTH_MODE": "stub", "ENV": "development", "TESTING": "True",
        "DATABASE_URL": "postgresql://mpp:mpp@localhost:5432/mpp_test",
    })
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    repo = TemplateRepository(session)

    repo.create({
        "slug": "vm-linux", "version": "1.0.0", "type": "vm",
        "display_name": "Linux VM", "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [
            {"key": "cpu_cores", "label": "CPU-Kerne", "type": "integer",
             "required": True, "tofu_variable_name": "cpu_cores",
             "display_order": 1, "constraints": {"min": 1, "max": 64},
             "depends_on": [], "affects_options_of": []},
            {"key": "os_type", "label": "OS", "type": "enum",
             "required": True, "tofu_variable_name": "os_type",
             "display_order": 2, "constraints": {"options": [
                 {"value": "ubuntu", "label": "Ubuntu", "enabled": True},
                 {"value": "rhel", "label": "RHEL", "enabled": True},
             ]}, "depends_on": [], "affects_options_of": ["disk_type"]},
            {"key": "disk_type", "label": "Disk", "type": "enum",
             "required": True, "tofu_variable_name": "disk_type",
             "display_order": 3, "constraints": {"options": [
                 {"value": "ext4", "label": "ext4", "enabled": True},
                 {"value": "xfs", "label": "XFS", "enabled": True},
             ]},
             "depends_on": [{"parameter_key": "os_type", "operator": "neq",
                             "value": None, "effect": "visible"}],
             "affects_options_of": []},
        ],
    })
    yield app, engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def val_client(val_app):
    app, _ = val_app
    return app.test_client()


@pytest.fixture
def auth(val_client):
    resp = val_client.post("/api/v1/auth/login", json={"username": "test-requester"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


class TestValidateEndpoint:
    def test_valid_params(self, val_client, auth):
        resp = val_client.post("/api/v1/catalog/templates/vm-linux/validate",
                                json={"parameters": {"cpu_cores": 4, "os_type": "ubuntu", "disk_type": "ext4"}},
                                headers=auth)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["valid"] is True
        assert data["violations"] == []

    def test_invalid_params(self, val_client, auth):
        resp = val_client.post("/api/v1/catalog/templates/vm-linux/validate",
                                json={"parameters": {"cpu_cores": 128, "os_type": "ubuntu"}},
                                headers=auth)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["valid"] is False
        assert len(data["violations"]) >= 1

    def test_template_not_found(self, val_client, auth):
        resp = val_client.post("/api/v1/catalog/templates/nonexistent/validate",
                                json={"parameters": {}}, headers=auth)
        assert resp.status_code == 404


class TestResolveOptionsEndpoint:
    def test_resolve_visible(self, val_client, auth):
        resp = val_client.post("/api/v1/catalog/templates/vm-linux/resolve-options",
                                json={"parameter_key": "disk_type",
                                      "current_values": {"os_type": "ubuntu"}},
                                headers=auth)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["is_visible"] is True
        assert data["parameter_key"] == "disk_type"

    def test_resolve_not_visible(self, val_client, auth):
        resp = val_client.post("/api/v1/catalog/templates/vm-linux/resolve-options",
                                json={"parameter_key": "disk_type",
                                      "current_values": {}},
                                headers=auth)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["is_visible"] is False

    def test_unknown_parameter(self, val_client, auth):
        resp = val_client.post("/api/v1/catalog/templates/vm-linux/resolve-options",
                                json={"parameter_key": "nonexistent",
                                      "current_values": {}},
                                headers=auth)
        assert resp.status_code == 400
```

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Add validation and resolve-options endpoints**

Add to `app/api/v1/catalog.py`:
- `POST /api/v1/catalog/templates/{slug}/validate` — Always returns 200, violations in body
- `POST /api/v1/catalog/templates/{slug}/resolve-options` — Resolves dependency state for a parameter

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests**
- [ ] **Step 6: Commit**

```bash
git add app/api/v1/catalog.py tests/integration/test_catalog_validation_api.py
git commit -m "feat: add parameter validation and dynamic option resolution endpoints"
```

---

### Task 9: Version Diff Endpoint

**Files:**
- Modify: `app/api/v1/catalog.py`
- Modify: `app/services/catalog_service.py` (add diff logic)
- Test: `tests/integration/test_catalog_diff_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_catalog_diff_api.py
import pytest
from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.template_repository import TemplateRepository


@pytest.fixture
def diff_app():
    app = create_app({
        "AUTH_MODE": "stub", "ENV": "development", "TESTING": "True",
        "DATABASE_URL": "postgresql://mpp:mpp@localhost:5432/mpp_test",
    })
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    repo = TemplateRepository(session)

    repo.create({
        "slug": "vm-linux", "version": "1.0.0", "type": "vm",
        "display_name": "Linux VM", "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git?ref=v1",
        "parameters": [
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "cpu", "display_order": 1,
             "constraints": {"min": 1, "max": 32}},
            {"key": "legacy_bios", "label": "Legacy BIOS", "type": "boolean",
             "required": False, "tofu_variable_name": "legacy_bios", "display_order": 2,
             "constraints": {}},
        ],
    })
    repo.create({
        "slug": "vm-linux", "version": "2.0.0", "type": "vm",
        "display_name": "Linux VM v2", "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git?ref=v2",
        "parameters": [
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "cpu", "display_order": 1,
             "constraints": {"min": 1, "max": 64}},
            {"key": "backup", "label": "Backup", "type": "boolean", "required": False,
             "tofu_variable_name": "backup_enabled", "display_order": 2,
             "constraints": {}},
        ],
    })
    yield app, engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def diff_client(diff_app):
    app, _ = diff_app
    return app.test_client()


@pytest.fixture
def approver_auth(diff_client):
    resp = diff_client.post("/api/v1/auth/login", json={"username": "test-approver"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


class TestVersionDiff:
    def test_diff_shows_changes(self, diff_client, approver_auth):
        resp = diff_client.get(
            "/api/v1/catalog/templates/vm-linux/diff?from_version=1.0.0&to_version=2.0.0",
            headers=approver_auth)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["slug"] == "vm-linux"
        changes = data["changes"]
        assert len(changes["added_parameters"]) == 1
        assert changes["added_parameters"][0]["key"] == "backup"
        assert len(changes["removed_parameters"]) == 1
        assert changes["removed_parameters"][0]["key"] == "legacy_bios"
        assert len(changes["modified_parameters"]) >= 1

    def test_diff_missing_version(self, diff_client, approver_auth):
        resp = diff_client.get(
            "/api/v1/catalog/templates/vm-linux/diff?from_version=1.0.0&to_version=9.9.9",
            headers=approver_auth)
        assert resp.status_code == 404

    def test_diff_requires_approver_or_admin(self, diff_client):
        resp = diff_client.post("/api/v1/auth/login", json={"username": "test-requester"})
        token = resp.get_json()["token"]
        resp = diff_client.get(
            "/api/v1/catalog/templates/vm-linux/diff?from_version=1.0.0&to_version=2.0.0",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
```

- [ ] **Step 2: Run tests — verify FAIL**
- [ ] **Step 3: Implement diff logic and endpoint**

Add `compute_diff(from_template, to_template)` method to `CatalogService` that compares parameters and returns added/removed/modified.

Add `GET /api/v1/catalog/templates/{slug}/diff` endpoint (approver/admin only via `@role_required`).

- [ ] **Step 4: Run tests — verify PASS**
- [ ] **Step 5: Run ALL tests**
- [ ] **Step 6: Commit**

```bash
git add app/api/v1/catalog.py app/services/catalog_service.py tests/integration/test_catalog_diff_api.py
git commit -m "feat: add template version diff endpoint (approver/admin only)"
```

---

### Task 10: Final Verification

- [ ] **Step 1: Run complete test suite**

Run: `source venv/bin/activate && pytest tests/ -v --tb=short`

- [ ] **Step 2: Verify endpoint count**

Expected endpoints from this phase:
1. `GET /api/v1/catalog/templates` (list)
2. `GET /api/v1/catalog/templates/{slug}` (detail)
3. `GET /api/v1/catalog/templates/{slug}/versions` (versions)
4. `GET /api/v1/catalog/templates/{slug}/diff` (diff)
5. `POST /api/v1/catalog/templates/{slug}/resolve-options` (resolve)
6. `GET /api/v1/catalog/categories` (categories)
7. `POST /api/v1/catalog/templates/{slug}/validate` (validate)
8. `POST /api/v1/admin/catalog/templates` (register)
9. `PATCH /api/v1/admin/catalog/templates/{id}/status` (update status)

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: phase 2 complete — Service Catalog with 9 endpoints"
```
