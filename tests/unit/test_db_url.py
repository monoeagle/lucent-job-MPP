class TestResolveDatabaseUrl:
    def test_prefers_database_url_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://env/db1")
        from app.core.db_url import resolve_database_url
        assert resolve_database_url("postgresql://ini/db2") == "postgresql://env/db1"

    def test_falls_back_to_ini_when_env_absent(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        from app.core.db_url import resolve_database_url
        assert resolve_database_url("postgresql://ini/db2") == "postgresql://ini/db2"

    def test_empty_string_when_nothing_set(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        from app.core.db_url import resolve_database_url
        assert resolve_database_url(None) == ""
