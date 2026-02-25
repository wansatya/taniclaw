"""SQLAlchemy Base and engine factory."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def create_session_factory(database_url: str):
    """Create SQLAlchemy engine and session factory."""
    if database_url.startswith("sqlite"):
        engine = create_engine(database_url)
    else:
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal
