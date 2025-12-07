from typing import Generator

from prometheus_client import Counter, Gauge
from sqlalchemy import event
from sqlmodel import SQLModel, Session, create_engine

engine = None

# Prometheus metrics
db_pool_checked_out = Gauge(
    "db_pool_checked_out", "Current number of checked-out DB connections"
)
db_pool_overflow = Gauge(
    "db_pool_overflow", "Current overflow connections beyond pool_size"
)
db_pool_size = Gauge("db_pool_size", "Configured DB pool size")
db_errors_total = Counter("db_errors_total", "Total DB errors", ["stage"])


def _get_connect_args(db_url: str) -> dict:
    if db_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def _register_pool_metrics(sql_engine):
    @event.listens_for(sql_engine, "connect")
    def _connect(dbapi_connection, connection_record):  # noqa: ANN001
        pool = sql_engine.pool
        db_pool_size.set(getattr(pool, "size", lambda: 0)())
        db_pool_checked_out.set(getattr(pool, "checkedout", lambda: 0)())
        db_pool_overflow.set(getattr(pool, "overflow", lambda: 0)())

    @event.listens_for(sql_engine, "checkout")
    def _checkout(dbapi_connection, connection_record, connection_proxy):  # noqa: ANN001
        pool = sql_engine.pool
        db_pool_checked_out.set(getattr(pool, "checkedout", lambda: 0)())
        db_pool_overflow.set(getattr(pool, "overflow", lambda: 0)())

    @event.listens_for(sql_engine, "checkin")
    def _checkin(dbapi_connection, connection_record):  # noqa: ANN001
        pool = sql_engine.pool
        db_pool_checked_out.set(getattr(pool, "checkedout", lambda: 0)())
        db_pool_overflow.set(getattr(pool, "overflow", lambda: 0)())

    @event.listens_for(sql_engine, "handle_error")
    def _handle_error(exception_context):  # noqa: ANN001
        db_errors_total.labels(stage="handle_error").inc()


def create_db_engine(db_url: str, echo: bool = False):
    connect_args = _get_connect_args(db_url)
    sql_engine = create_engine(db_url, echo=echo, connect_args=connect_args)
    _register_pool_metrics(sql_engine)
    return sql_engine


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
