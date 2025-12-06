from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy import func
from sqlmodel import Session, select

from database.releasebundle import ReleaseBundle
from database.session import get_session
from utils.dependencies import require_basic_auth
from models.release import Release
from models.timespan import Timespan
from utils.bundle_id import gen_release_bundle_hash

router = APIRouter(
    prefix="/api/v1/release",
    tags=["release"],
    dependencies=[Depends(require_basic_auth)],
)


@router.post("/create", response_model=ReleaseBundle)
def create_release(
    release: Release,
    session: Session = Depends(get_session),
):
    release_id = gen_release_bundle_hash(release.environment, release.versions)
    existing = session.get(ReleaseBundle, release_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="release_hash already exists",
        )

    release_bundle = ReleaseBundle(
        deployment_hash=release_id,
        environment=release.environment,
        versions=release.versions,
    )
    session.add(release_bundle)
    session.commit()
    session.refresh(release_bundle)
    return release_bundle


@router.get("/history/{environment}")
def get_release_history(
    environment: str,
    start_date: datetime = Query(
        ..., description="ISO 8601 datetime (e.g., 2024-01-01T00:00:00Z)"
    ),
    end_date: datetime = Query(
        ..., description="ISO 8601 datetime (e.g., 2024-01-31T23:59:59Z)"
    ),
    session: Session = Depends(get_session),
):
    try:
        span = Timespan(start_date=start_date, end_date=end_date)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors())

    statement = (
        select(ReleaseBundle)
        .where(ReleaseBundle.environment == environment)
        .where(ReleaseBundle.timestamp >= span.start_date)
        .where(ReleaseBundle.timestamp <= span.end_date)
        .order_by(ReleaseBundle.timestamp.desc())
    )
    results = session.exec(statement).all()
    return results


@router.get("/history/{environment}/count")
def get_release_history_count(
    environment: str,
    start_date: datetime = Query(
        ..., description="ISO 8601 datetime (e.g., 2024-01-01T00:00:00Z)"
    ),
    end_date: datetime = Query(
        ..., description="ISO 8601 datetime (e.g., 2024-01-31T23:59:59Z)"
    ),
    session: Session = Depends(get_session),
):
    try:
        span = Timespan(start_date=start_date, end_date=end_date)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors())

    statement = (
        select(func.count())
        .select_from(ReleaseBundle)
        .where(ReleaseBundle.environment == environment)
        .where(ReleaseBundle.timestamp >= span.start_date)
        .where(ReleaseBundle.timestamp <= span.end_date)
    )
    count = session.exec(statement).one()
    return {"environment": environment, "count": count}


@router.delete("/delete/{deployment_hash}")
def delete_release(
    deployment_hash: str,
    session: Session = Depends(get_session),
):
    release_bundle = session.get(ReleaseBundle, deployment_hash)
    if not release_bundle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    session.delete(release_bundle)
    session.commit()
    return {"status": "deleted", "release_hash": deployment_hash}
