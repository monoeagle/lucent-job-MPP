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
