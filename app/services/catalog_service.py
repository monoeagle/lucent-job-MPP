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
                    "message": "Minimale Größe unterschritten.",
                })
            if max_b is not None and value > max_b:
                violations.append({
                    "parameter_key": key, "rule": "VAL-constraints",
                    "message": "Maximale Größe überschritten.",
                })

        return violations

    def compute_diff(self, from_template, to_template) -> dict:
        from_params = {p["key"]: p for p in (from_template.parameters or [])}
        to_params = {p["key"]: p for p in (to_template.parameters or [])}

        added = [to_params[k] for k in to_params if k not in from_params]
        removed = [from_params[k] for k in from_params if k not in to_params]

        modified = []
        for key in from_params:
            if key in to_params and from_params[key] != to_params[key]:
                modified.append({
                    "key": key,
                    "from": from_params[key],
                    "to": to_params[key],
                })

        return {
            "added_parameters": added,
            "removed_parameters": removed,
            "modified_parameters": modified,
            "tofu_module_source_changed": (
                from_template.tofu_module_source != to_template.tofu_module_source
            ),
        }

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
