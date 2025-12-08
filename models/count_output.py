from pydantic import BaseModel


class CountOutput(BaseModel):
    environment: str
    count: int
