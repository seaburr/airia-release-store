import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from utils.config import Settings

security = HTTPBasic()


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def require_basic_auth(
    credentials: HTTPBasicCredentials = Depends(security),
    settings: Settings = Depends(get_app_settings),
) -> str:
    is_valid_user = secrets.compare_digest(
        credentials.username, settings.basic_auth_username
    )
    is_valid_password = secrets.compare_digest(
        credentials.password, settings.basic_auth_password
    )
    if not (is_valid_user and is_valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
