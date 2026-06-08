"""
Backup and restore API endpoints.
"""
import threading

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models.user import User
from app.dependencies import require_admin
from app.services.backup import (
    get_versions_for_backup,
    create_backup,
    list_backup_files,
    get_backup_manifest,
    restore_backup,
    delete_backup,
    get_backup_progress,
)

router = APIRouter()


class CreateBackupRequest(BaseModel):
    version_ids: list[int]


class RestoreBackupRequest(BaseModel):
    filename: str
    mode: str = "append"  # "append" or "overwrite"


@router.get("/versions")
def list_versions_for_backup(admin: User = Depends(require_admin)):
    """Get all versions available for backup."""
    versions = get_versions_for_backup()
    return {"versions": versions}


@router.post("/create")
def create_backup_endpoint(
    request: CreateBackupRequest,
    admin: User = Depends(require_admin),
):
    """Start a backup operation in background."""
    if not request.version_ids:
        raise HTTPException(status_code=400, detail="请至少选择一个版本")

    # 在后台线程执行备份
    def run():
        create_backup(request.version_ids)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return {"success": True, "message": "备份已开始"}


@router.get("/progress")
def get_progress(admin: User = Depends(require_admin)):
    """Get current backup/restore progress."""
    return get_backup_progress()


@router.get("/files")
def list_files(admin: User = Depends(require_admin)):
    """List all backup files."""
    files = list_backup_files()
    return {"files": files}


@router.get("/files/{filename}")
def get_file_manifest(filename: str, admin: User = Depends(require_admin)):
    """Get manifest from a specific backup file."""
    manifest = get_backup_manifest(filename)
    if manifest is None:
        raise HTTPException(status_code=404, detail="备份文件不存在或已损坏")
    return {"filename": filename, "manifest": manifest}


@router.post("/restore")
def restore_backup_endpoint(
    request: RestoreBackupRequest,
    admin: User = Depends(require_admin),
):
    """Start a restore operation in background."""
    if request.mode not in ("append", "overwrite"):
        raise HTTPException(status_code=400, detail="恢复模式必须是 'append' 或 'overwrite'")

    # 在后台线程执行恢复
    def run():
        restore_backup(request.filename, request.mode)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return {"success": True, "message": "恢复已开始"}


@router.delete("/files/{filename}")
def delete_file(filename: str, admin: User = Depends(require_admin)):
    """Delete a backup file."""
    result = delete_backup(filename)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "删除失败"))
    return result
