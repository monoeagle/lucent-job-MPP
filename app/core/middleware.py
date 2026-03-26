import uuid

from flask import request, g


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
