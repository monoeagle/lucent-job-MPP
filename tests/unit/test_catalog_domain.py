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
