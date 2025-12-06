from typing import Generator, Optional

from sqlmodel import SQLModel, Session, create_engine


engine = None


def _get_connect_args(db_url: str) -> dict:
    if db_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def create_db_engine(db_url: str):
    connect_args = _get_connect_args(db_url)
    return create_engine(db_url, echo=False, connect_args=connect_args)


def init_db(db_url: str) -> None:
    global engine
    engine = create_db_engine(db_url)
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    if engine is None:
        raise RuntimeError("Database engine is not initialized")
    with Session(engine) as session:
        yield session
