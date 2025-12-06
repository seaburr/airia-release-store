from datetime import datetime, timezone
from sqlmodel import Field, SQLModel
from sqlalchemy import Column, JSON


class ReleaseBundle(SQLModel, table=True):
    deployment_hash: str = Field(default=None, primary_key=True)
    environment: str = Field(index=True)
    versions: dict[str, str] = Field(sa_column=Column(JSON))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
