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
