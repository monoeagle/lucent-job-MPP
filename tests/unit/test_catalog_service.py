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
