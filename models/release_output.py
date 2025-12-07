from datetime import datetime
from typing import Dict

from pydantic import BaseModel


class ReleaseOutput(BaseModel):
    deployment_id: str
    environment: str
    versions: Dict[str, str]
    timestamp: datetime
