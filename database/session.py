from typing import Generator

from sqlmodel import SQLModel, Session, create_engine

engine = None


def _get_connect_args(db_url: str) -> dict:
    if db_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def create_db_engine(db_url: str, echo: bool = False):
    connect_args = _get_connect_args(db_url)
    return create_engine(db_url, echo=echo, connect_args=connect_args)


def init_db(db_url: str, echo: bool = False) -> None:
    """Initialize engine, create tables, and seed health status row."""
    global engine
    engine = create_db_engine(db_url, echo=echo)
    SQLModel.metadata.create_all(engine)

    from database.healthcheck import HealthStatus

    with Session(engine) as session:
        if not session.get(HealthStatus, 1):
            session.add(HealthStatus(id=1, ok=True))
            session.commit()


def get_session() -> Generator[Session, None, None]:
    if engine is None:
        raise RuntimeError("Database engine is not initialized")
    with Session(engine) as session:
        yield session
