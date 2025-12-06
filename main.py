from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import RedirectResponse
import uvicorn

from utils.config import Settings, get_settings
from database.session import init_db
from routers import releases
from utils.logging_config import configure_logging

logger = logging.getLogger(__name__)


def _configure_logging(level: str) -> None:
    configure_logging(level=level)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    _configure_logging(app_settings.logging_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(app_settings.database_url)
        yield

    app = FastAPI(lifespan=lifespan)
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

    @app.get("/")
    def root():
        return RedirectResponse(url="/docs")

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    app.include_router(releases.router)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
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
