import pytest
from app.domain.catalog import ParameterDefinition
from app.services.template_validator import TemplateValidator


class TestPerInstanceField:
    def test_default_is_false(self):
        p = ParameterDefinition(key="cpu", label="CPU", type="integer",
            required=True, tofu_variable_name="cpu", display_order=1, constraints={})
        assert p.per_instance is False

    def test_can_set_true(self):
        p = ParameterDefinition(key="tag", label="Tag", type="string",
            required=True, tofu_variable_name="tag", display_order=1,
            constraints={}, per_instance=True)
        assert p.per_instance is True

    def test_can_set_auto(self):
        p = ParameterDefinition(key="hostname", label="Hostname", type="string",
            required=True, tofu_variable_name="hostname", display_order=1,
            constraints={}, per_instance="auto")
        assert p.per_instance == "auto"


class TestPerInstanceValidation:
    def test_valid_per_instance_false(self):
        v = TemplateValidator()
        param = {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
                 "tofu_variable_name": "cpu", "display_order": 1, "constraints": {},
                 "per_instance": False}
        errors = v.validate_parameter(param, set(), set())
        assert errors == []

    def test_valid_per_instance_true(self):
        v = TemplateValidator()
        param = {"key": "tag", "label": "Tag", "type": "string", "required": True,
                 "tofu_variable_name": "tag", "display_order": 1, "constraints": {},
                 "per_instance": True}
        errors = v.validate_parameter(param, set(), set())
        assert errors == []

    def test_valid_per_instance_auto_string(self):
        v = TemplateValidator()
        param = {"key": "hostname", "label": "Hostname", "type": "string", "required": True,
                 "tofu_variable_name": "hostname", "display_order": 1, "constraints": {},
                 "per_instance": "auto"}
        errors = v.validate_parameter(param, set(), set())
        assert errors == []

    def test_invalid_per_instance_auto_non_string(self):
        v = TemplateValidator()
        param = {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
                 "tofu_variable_name": "cpu", "display_order": 1, "constraints": {},
                 "per_instance": "auto"}
        errors = v.validate_parameter(param, set(), set())
        assert len(errors) >= 1
        assert any("auto" in e.lower() or "string" in e.lower() for e in errors)

    def test_invalid_per_instance_value(self):
        v = TemplateValidator()
        param = {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
                 "tofu_variable_name": "cpu", "display_order": 1, "constraints": {},
                 "per_instance": "invalid"}
        errors = v.validate_parameter(param, set(), set())
        assert len(errors) >= 1

    def test_template_without_per_instance_still_valid(self):
        """Backwards compatibility: templates without per_instance field are valid."""
        v = TemplateValidator()
        template = {
            "slug": "vm-linux", "version": "1.0.0", "type": "vm",
            "display_name": "Linux VM", "category": "Compute",
            "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
            "parameters": [
                {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
                 "tofu_variable_name": "cpu", "display_order": 1, "constraints": {}}
            ],
        }
        errors = v.validate_template(template)
        assert errors == []
