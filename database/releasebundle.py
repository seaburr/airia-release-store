from datetime import datetime, timezone
from sqlmodel import Field, Session, SQLModel, create_engine, select

class ReleaseBundle(SQLModel, table=True):
    deployment_hash: str = Field(default=None, primary_key=True)
    environment: str = Field(index=True)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )