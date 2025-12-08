from contextlib import asynccontextmanager
import logging
import time
from fastapi import Depends, FastAPI, HTTPException, Request, status
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import RedirectResponse
import uvicorn
from utils.config import Settings, get_settings
from database.healthcheck import HealthStatus
from database.session import get_session
from database.session import init_db
from routers import releases
from models.status_output import StatusOutput
from utils.logging_config import configure_logging
from sqlmodel import Session as SQLSession


logger = logging.getLogger(__name__)


def _configure_logging(level: str) -> None:
    configure_logging(level=level)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    _configure_logging(app_settings.logging_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(app_settings.database_url, echo=app_settings.sql_echo)
        yield

    app = FastAPI(
        title="Airia Release Store",
        lifespan=lifespan,
    )
    app.state.settings = app_settings

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log incoming requests with JSON structured logs."""
        start_time = time.perf_counter()
        access_logger = logging.getLogger("uvicorn.access")
        try:
            response = await call_next(request)
        except Exception:
            process_ms = (time.perf_counter() - start_time) * 1000
            access_logger.exception(
                "request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "process_ms": round(process_ms, 2),
                },
            )
            raise

        process_ms = (time.perf_counter() - start_time) * 1000
        access_logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_ms": round(process_ms, 2),
            },
        )
        return response

    @app.get("/", tags=["Lifecycle APIs"])
    def root():
        return RedirectResponse(url="/docs")

    @app.get("/livez", tags=["Lifecycle APIs"], response_model=StatusOutput)
    def livez():
        return {"status": "ok"}

    @app.get("/readyz", tags=["Lifecycle APIs"], response_model=StatusOutput)
    def readyz(session: SQLSession = Depends(get_session)):
        try:
            health = session.get(HealthStatus, 1)
            if health and health.ok:
                return {"status": "ok"}
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database not ready",
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("/readyz healthcheck failed.", exc_info=exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database not ready",
            )

    app.include_router(releases.router)

    # Expose Prometheus metrics and tag them for docs clarity
    Instrumentator().instrument(app).expose(
        app, endpoint="/metrics", tags=["Prometheus Metrics API"]
    )
    return app


app = create_app()


def main():
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        server_header=False,
        reload=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
