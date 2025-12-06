from datetime import datetime
from pydantic import BaseModel

class Timespan(BaseModel):
    start_date: datetime
    end_date: datetime

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "start_date": "2025-11-01 00:00:00.0+00:00",
                    "end_date": "2025-12-01 00:00:00.0+00:00",
                }
            ]
        }
    }