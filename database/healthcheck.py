from sqlmodel import Field, SQLModel


class HealthStatus(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    ok: bool = Field(default=True)
