from typing import Annotated
from datetime import datetime, timezone
import hashlib
import json
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import RedirectResponse

from models.release import Release
from models.timespan import Timespan
from database.releasebundle import ReleaseBundle
from utils.bundle_id import gen_release_bundle_hash
import uvicorn

app = FastAPI()

@app.get("/")
def root():
    return RedirectResponse(url="/docs")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.post("/api/v1/release/create")
def create_release(release: Release):
    release_id = gen_release_bundle_hash(release.environment, release.versions)
    return {"release_hash": release_id, "status": "created"}

@app.get("/api/v1/release/history/{environment}")
def get_release_history(environment: str, start_date: datetime, end_date: datetime):
    return Timespan(start_date=start_date, end_date=end_date)

@app.delete("/api/v1/release/delete/{deployment_hash}")
def delete_release(deployment_hash: str):
    return f"deleted {deployment_hash}"

def main():
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    uvicorn.run('main:app', server_header=False, reload=True)

if __name__ == "__main__":
    main()