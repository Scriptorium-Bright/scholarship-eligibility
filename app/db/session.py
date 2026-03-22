from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Dict, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.models.base import Base


@lru_cache(maxsize=4)
def build_engine(database_url: str):
    """Build a cached SQLAlchemy engine for the requested database URL."""

    connect_args = {}
    engine_kwargs = {
        "future": True,
        "pool_pre_ping": True,
        "connect_args": connect_args,
    }
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if database_url.endswith(":memory:"):
            engine_kwargs["poolclass"] = StaticPool

    return create_engine(database_url, **engine_kwargs)


@lru_cache(maxsize=4)
def build_session_factory(database_url: str):
    """Build a cached session factory bound to the configured engine."""

    return sessionmaker(
        bind=build_engine(database_url),
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )


def get_engine():
    """Return the engine for the current application settings."""

    return build_engine(get_settings().database_url)


def get_session_factory():
    """Return the session factory for the current application settings."""

    return build_session_factory(get_settings().database_url)


def get_session() -> Session:
    """Create a new database session from the cached factory."""

    return get_session_factory()()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Wrap a unit of work with commit or rollback semantics."""

    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all_tables() -> None:
    """Create all known tables for local tests and bootstrap flows."""

    import app.models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


def reset_engine_cache() -> None:
    """Clear cached engine and session factory instances between tests."""

    build_engine.cache_clear()
    build_session_factory.cache_clear()


def database_healthcheck() -> Dict[str, Any]:
    """Run a lightweight connectivity check used by the readiness route."""

    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "detail": "database connection succeeded"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
