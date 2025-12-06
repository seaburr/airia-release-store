from pydantic import BaseModel

class Release(BaseModel):
    environment: str
    versions: dict[str, str]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "environment": "production",
                    "versions": {
                        "service-a": "1.0.1",
                        "service-b": "2.8.3",
                    }
                }
            ]
        }
    }
