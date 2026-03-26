from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

_engines: dict[str, object] = {}


class Base(DeclarativeBase):
    pass


def get_engine(database_url: str):
    if database_url not in _engines:
        _engines[database_url] = create_engine(database_url, echo=False)
    return _engines[database_url]


def get_session_factory(engine):
    return sessionmaker(bind=engine)
