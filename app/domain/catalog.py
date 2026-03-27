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
    per_instance: bool | str = False

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
