from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy import func
from sqlmodel import Session, select

from database.releasebundle import ReleaseBundle
from database.session import get_session
from utils.dependencies import require_basic_auth
from models.release import Release
from models.delete_output import DeleteOutput
from models.timespan import Timespan
from models.release_output import ReleaseOutput
from models.count_output import CountOutput
from utils.bundle_id import gen_release_bundle_hash

router = APIRouter(
    prefix="/api/v1/release",
    tags=["Release History API"],
    dependencies=[Depends(require_basic_auth)],
)

logger = logging.getLogger(__name__)


@router.post("/create", response_model=ReleaseOutput)
def create_release(
    release: Release,
    session: Session = Depends(get_session),
):
    release_id = gen_release_bundle_hash(release.environment, release.versions)
    existing = session.get(ReleaseBundle, release_id)
    if existing:
        logger.warning(
            "duplicate attempt to create release",
            extra={
                "environment": release.environment,
                "deployment_id": release_id,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This release already exists.",
        )

    release_bundle = ReleaseBundle(
        deployment_id=release_id,
        environment=release.environment,
        versions=release.versions,
    )
    session.add(release_bundle)
    session.commit()
    session.refresh(release_bundle)
    logger.info(
        "created release",
        extra={
            "environment": release.environment,
            "deployment_id": release_id,
        },
    )
    return ReleaseOutput.model_validate(release_bundle, from_attributes=True)


@router.get("/history/{environment}", response_model=list[ReleaseOutput])
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
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(exc.errors()),
        )

    statement = (
        select(ReleaseBundle)
        .where(ReleaseBundle.environment == environment)
        .where(ReleaseBundle.timestamp >= span.start_date)
        .where(ReleaseBundle.timestamp <= span.end_date)
        .order_by(ReleaseBundle.timestamp.desc())
    )
    results = session.exec(statement).all()
    logger.info(
        "fetched release history",
        extra={
            "environment": environment,
            "count": len(results),
        },
    )
    return [
        ReleaseOutput.model_validate(item, from_attributes=True)
        for item in results
    ]


@router.get("/history/{environment}/count", response_model=CountOutput)
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
        raise HTTPException(
            status_code=400,
            detail=jsonable_encoder(exc.errors()),
        )

    statement = (
        select(func.count())
        .select_from(ReleaseBundle)
        .where(ReleaseBundle.environment == environment)
        .where(ReleaseBundle.timestamp >= span.start_date)
        .where(ReleaseBundle.timestamp <= span.end_date)
    )
    count = session.exec(statement).one()
    logger.info(
        "fetched release count",
        extra={"environment": environment, "count": count},
    )
    return CountOutput(environment=environment, count=count)


@router.delete("/delete/{deployment_id}", response_model=DeleteOutput)
def delete_release(
    deployment_id: str,
    session: Session = Depends(get_session),
):
    release_bundle = session.get(ReleaseBundle, deployment_id)
    if not release_bundle:
        logger.warning(
            "delete requested for missing deployment",
            extra={"deployment_id": deployment_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No deployment found by deployment id {deployment_id}."
            ),
        )
    session.delete(release_bundle)
    session.commit()
    logger.info(
        "deleted release successfully",
        extra={"deployment_id": deployment_id},
    )
    return DeleteOutput(status="deleted", deployment_id=deployment_id)
