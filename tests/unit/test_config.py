import os
import pytest


class TestConfig:
    def test_default_auth_mode_is_ldap(self, monkeypatch):
        monkeypatch.delenv("AUTH_MODE", raising=False)
        from app.core.config import get_config
        config = get_config()
        assert config.AUTH_MODE == "ldap"

    def test_stub_auth_mode(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "stub")
        monkeypatch.setenv("ENV", "development")
        from app.core.config import get_config
        config = get_config()
        assert config.AUTH_MODE == "stub"

    def test_stub_in_production_raises(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "stub")
        monkeypatch.setenv("ENV", "production")
        from app.core.config import get_config
        with pytest.raises(RuntimeError, match="must not be used in production"):
            get_config()

    def test_invalid_auth_mode_raises(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "invalid")
        from app.core.config import get_config
        with pytest.raises(ValueError, match="Unknown AUTH_MODE"):
            get_config()

    def test_jwt_secret_fallback_in_stub_mode(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "stub")
        monkeypatch.setenv("ENV", "development")
        monkeypatch.delenv("JWT_SECRET", raising=False)
        from app.core.config import get_config
        config = get_config()
        assert config.JWT_SECRET == "stub-jwt-secret-dev-only"

    def test_stub_token_ttl_default(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "stub")
        monkeypatch.setenv("ENV", "development")
        from app.core.config import get_config
        config = get_config()
        assert config.STUB_TOKEN_TTL_SECONDS == 86400

    def test_database_url_from_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/testdb")
        from app.core.config import get_config
        config = get_config()
        assert config.DATABASE_URL == "postgresql://test:test@localhost/testdb"
