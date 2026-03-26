from sqlalchemy import text


class TestDatabaseConnection:
    def test_db_engine_connects(self, app):
        from app.data.db.session import get_engine
        engine = get_engine(app.config["DATABASE_URL"])
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_db_session_lifecycle(self, app):
        from app.data.db.session import get_session_factory, get_engine
        engine = get_engine(app.config["DATABASE_URL"])
        SessionFactory = get_session_factory(engine)
        session = SessionFactory()
        result = session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        session.close()
