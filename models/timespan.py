from datetime import datetime, timezone
from pydantic import BaseModel, model_validator


class Timespan(BaseModel):
    start_date: datetime
    end_date: datetime

    @model_validator(mode="after")
    def validate_range(self):
        start = self.start_date
        end = self.end_date

        # Require both datetimes to be similarly aware/naive
        # to avoid implicit conversions
        if (start.tzinfo is None) != (end.tzinfo is None):
            raise ValueError(
                "start_date and end_date must both be timezone-aware or "
                "both be naive."
            )

        start_cmp = start
        end_cmp = end
        if start.tzinfo and end.tzinfo:
            start_cmp = start.astimezone(timezone.utc)
            end_cmp = end.astimezone(timezone.utc)

        if start_cmp > end_cmp:
            raise ValueError("start_date must be before or equal to end_date.")

        return self

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
