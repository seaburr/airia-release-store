from pydantic import BaseModel


class DeleteOutput(BaseModel):
    status: str
    deployment_id: str
