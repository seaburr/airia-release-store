from pydantic import BaseModel


class StatusOutput(BaseModel):
    status: str
