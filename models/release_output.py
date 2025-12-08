from datetime import datetime
from typing import Dict

from pydantic import BaseModel


class ReleaseOutput(BaseModel):
    deployment_id: str
    environment: str
    versions: Dict[str, str]
    timestamp: datetime

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "deployment_id": (
                        "3e44ddaa31c4123fe60a75bf76ca5908fd140a0260aa3a"
                        "830fd05af8182b1886"
                    ),
                    "environment": "production",
                    "versions": {
                        "service-a": "1.0.1",
                        "service-b": "2.8.3",
                    },
                    "timestamp": "2024-01-01T00:00:00+00:00",
                }
            ]
        }
    }
