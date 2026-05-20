from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Version
from app.schemas.version import VersionInfo, VersionDiff
from app.services.differ import compute_diff

router = APIRouter()


@router.get("", response_model=list[VersionInfo])
def list_versions(db: Session = Depends(get_db)):
    versions = db.query(Version).order_by(Version.tag.desc()).all()
    return [VersionInfo.model_validate(v) for v in versions]


@router.get("/{version_id}", response_model=VersionInfo)
def get_version(version_id: int, db: Session = Depends(get_db)):
    version = db.query(Version).filter(Version.id == version_id).first()
    if not version:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Version not found")
    return VersionInfo.model_validate(version)


@router.get("/{version_id}/diff", response_model=VersionDiff)
def get_version_diff(
    version_id: int,
    compare_id: int | None = Query(None),
    top_n: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException

    version_b = db.query(Version).filter(Version.id == version_id).first()
    if not version_b:
        raise HTTPException(status_code=404, detail="Version not found")

    # Default to previous version (by tag date)
    if compare_id is None:
        prev_version = (
            db.query(Version)
            .filter(Version.tag < version_b.tag)
            .order_by(Version.tag.desc())
            .first()
        )
        if not prev_version:
            raise HTTPException(status_code=404, detail="No previous version to compare")
        compare_id = prev_version.id

    version_a = db.query(Version).filter(Version.id == compare_id).first()
    if not version_a:
        raise HTTPException(status_code=404, detail="Compare version not found")

    diff = compute_diff(db, compare_id, version_id, top_n)

    return VersionDiff(
        version_a=VersionInfo.model_validate(version_a),
        version_b=VersionInfo.model_validate(version_b),
        **diff,
    )
