from werkzeug.middleware.proxy_fix import ProxyFix


class TestAppFactory:
    def test_proxyfix_is_applied(self, app):
        """Hinter nginx muss die App X-Forwarded-* auswerten (ProxyFix)."""
        assert isinstance(app.wsgi_app, ProxyFix)
