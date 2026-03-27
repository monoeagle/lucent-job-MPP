import json
import re
import uuid

from flask import request, g, current_app


# Fields to anonymize when DSGVO mode is active
_PERSON_FIELDS = {
    "requester_id", "requester_name", "decided_by",
    "recipient_email", "recipient_id",
    "orderer_email", "responsible_email", "contact_group_email",
    "email", "display_name",
}
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def _anonymize_value(key: str, value):
    """Mask a single value based on field name."""
    if value is None:
        return None
    if key in _PERSON_FIELDS:
        s = str(value)
        if len(s) <= 2:
            return "***"
        return s[0] + "***" + s[-1]
    return value


def _anonymize_obj(obj):
    """Recursively anonymize person fields in a dict/list."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k in _PERSON_FIELDS:
                result[k] = _anonymize_value(k, v)
            elif k == "parameters" and isinstance(v, dict):
                # Anonymize email values inside parameters
                result[k] = {
                    pk: (_anonymize_value(pk, pv) if pk in _PERSON_FIELDS or
                         (isinstance(pv, str) and _EMAIL_PATTERN.fullmatch(pv))
                         else pv)
                    for pk, pv in v.items()
                }
            else:
                result[k] = _anonymize_obj(v)
        return result
    elif isinstance(obj, list):
        return [_anonymize_obj(item) for item in obj]
    return obj


def register_middleware(app):
    @app.before_request
    def set_request_id():
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.request_id = request_id
        g.request_id = request_id

    @app.after_request
    def add_request_id_header(response):
        request_id = getattr(request, "request_id", "unknown")
        response.headers["X-Request-ID"] = request_id
        return response

    @app.after_request
    def dsgvo_anonymize(response):
        if not current_app.config.get("DSGVO_ANONYMIZE", False):
            return response
        if response.content_type and "application/json" not in response.content_type:
            return response
        try:
            data = response.get_json(silent=True)
            if data is None:
                return response
            anonymized = _anonymize_obj(data)
            response.set_data(json.dumps(anonymized))
        except Exception:
            pass
        return response
