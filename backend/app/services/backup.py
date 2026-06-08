"""
Backup and restore service for movie versions.
"""
import json
import logging
import shutil
import time
import zipfile
from datetime import datetime
from pathlib import Path

from sqlalchemy import or_

from app.config import settings
from app.database import SessionLocal
from app.models import Movie, Version, VersionEntry
from app.utils import now

logger = logging.getLogger(__name__)

BACKUP_DIR = Path("./data/backup")

# In-memory progress tracking
backup_progress = {
    "active": False,
    "type": "",  # "backup" or "restore"
    "step": "",
    "current": 0,
    "total": 0,
    "percent": 0,
    "detail": "",
    "message": "",
    "elapsed_seconds": 0,
    "result": None,  # 完成后的结果
}


def get_backup_progress() -> dict:
    """Get current backup/restore progress."""
    return dict(backup_progress)


def _reset_progress():
    """Reset progress to initial state."""
    backup_progress.update({
        "active": False,
        "type": "",
        "step": "",
        "current": 0,
        "total": 0,
        "percent": 0,
        "detail": "",
        "message": "",
        "elapsed_seconds": 0,
        "result": None,
    })


def _update_progress(**kwargs):
    """Update progress and calculate percent."""
    backup_progress.update(kwargs)
    if backup_progress["total"] > 0:
        backup_progress["percent"] = int(
            backup_progress["current"] / backup_progress["total"] * 100
        )


def get_versions_for_backup() -> list[dict]:
    """Get all versions available for backup."""
    db = SessionLocal()
    try:
        versions = db.query(Version).order_by(Version.tag.desc(), Version.source).all()
        result = []
        for v in versions:
            movie_count = db.query(VersionEntry).filter(
                VersionEntry.version_id == v.id
            ).count()
            result.append({
                "id": v.id,
                "tag": v.tag,
                "source": v.source,
                "status": v.status,
                "crawled_at": v.crawled_at.isoformat() if v.crawled_at else None,
                "movie_count": movie_count,
            })
        return result
    finally:
        db.close()


def create_backup(version_ids: list[int]) -> dict:
    """Create a backup file for selected versions."""
    global backup_progress

    if backup_progress["active"]:
        return {"success": False, "error": "备份/恢复操作正在进行中"}

    _reset_progress()
    start_time = time.time()

    try:
        db = SessionLocal()
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        # 1. 收集版本信息
        _update_progress(
            active=True,
            type="backup",
            step="collecting",
            current=0,
            total=len(version_ids),
            message="正在收集版本数据...",
        )

        versions = []
        for vid in version_ids:
            v = db.query(Version).filter(Version.id == vid).first()
            if v:
                versions.append(v)
            backup_progress["current"] += 1

        if not versions:
            _reset_progress()
            return {"success": False, "error": "未找到选中的版本"}

        # 2. 收集关联的电影
        _update_progress(
            step="collecting_movies",
            current=0,
            total=1,
            message="正在收集电影数据...",
        )

        # 获取所有关联的 movie_id
        movie_ids = set()
        version_entries = []
        for v in versions:
            entries = db.query(VersionEntry).filter(
                VersionEntry.version_id == v.id
            ).all()
            for e in entries:
                movie_ids.add(e.movie_id)
                version_entries.append(e)

        movies = db.query(Movie).filter(Movie.id.in_(movie_ids)).all()
        movie_map = {m.id: m for m in movies}

        backup_progress["current"] = 1

        # 3. 导出电影数据
        _update_progress(
            step="exporting_movies",
            current=0,
            total=len(movies),
            message=f"正在导出电影数据 ({len(movies)} 部)...",
        )

        movies_data = []
        for i, movie in enumerate(movies):
            movies_data.append({
                "douban_id": movie.douban_id,
                "imdb_id": movie.imdb_id,
                "title": movie.title,
                "original_title": movie.original_title,
                "year": movie.year,
                "country": movie.country,
                "genre": movie.genre,
                "director": movie.director,
                "cast_members": movie.cast_members,
                "duration": movie.duration,
                "rating": movie.rating,
                "rating_count": movie.rating_count,
                "tagline": movie.tagline,
                "summary": movie.summary,
                "poster_path": movie.poster_path,
                "douban_url": movie.douban_url,
            })
            _update_progress(current=i + 1, detail=f"电影数据 ({i + 1}/{len(movies)})")

        # 4. 导出版本数据
        _update_progress(
            step="exporting_versions",
            current=0,
            total=len(versions),
            message="正在导出版本数据...",
        )

        versions_data = []
        for i, v in enumerate(versions):
            versions_data.append({
                "tag": v.tag,
                "source": v.source,
                "status": v.status,
                "crawled_at": v.crawled_at.isoformat() if v.crawled_at else None,
                "movie_count": v.movie_count,
            })
            _update_progress(current=i + 1)

        # 5. 导出版本条目
        _update_progress(
            step="exporting_entries",
            current=0,
            total=len(version_entries),
            message="正在导出版本条目...",
        )

        entries_data = []
        for i, e in enumerate(version_entries):
            v = db.query(Version).filter(Version.id == e.version_id).first()
            m = movie_map.get(e.movie_id)
            if v and m:
                entries_data.append({
                    "version_tag": v.tag,
                    "version_source": v.source,
                    "movie_douban_id": m.douban_id,
                    "movie_imdb_id": m.imdb_id,
                    "rank": e.rank,
                    "rating": e.rating,
                })
            _update_progress(current=i + 1)

        # 6. 收集海报文件
        poster_files = set()
        for movie in movies:
            if movie.poster_path:
                poster_files.add(movie.poster_path)

        # 7. 准备数据
        data = {
            "movies": movies_data,
            "versions": versions_data,
            "version_entries": entries_data,
        }

        manifest = {
            "version": "1.0",
            "created_at": now().isoformat(),
            "app_version": "0.1.0",
            "versions": [
                {
                    "tag": v["tag"],
                    "source": v["source"],
                    "movie_count": v["movie_count"],
                }
                for v in versions_data
            ],
            "movie_count": len(movies_data),
            "poster_count": len(poster_files),
        }

        # 8. 创建压缩包
        _update_progress(
            step="creating_archive",
            current=0,
            total=len(poster_files) + 2,  # +2 for manifest and data
            message="正在创建压缩包...",
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{timestamp}.zip"
        filepath = BACKUP_DIR / filename

        with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 写入 manifest
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            _update_progress(current=1)

            # 写入 data
            zf.writestr("data.json", json.dumps(data, ensure_ascii=False, indent=2))
            _update_progress(current=2)

            # 写入海报
            posters_dir = settings.posters_dir
            for i, poster in enumerate(poster_files):
                poster_path = posters_dir / poster
                if poster_path.exists():
                    zf.write(poster_path, f"posters/{poster}")
                _update_progress(
                    current=i + 3,
                    detail=f"海报文件 ({i + 1}/{len(poster_files)})",
                )

        # 9. 完成
        file_size = filepath.stat().st_size
        elapsed = int(time.time() - start_time)

        _update_progress(
            active=False,
            step="completed",
            current=backup_progress["total"],
            total=backup_progress["total"],
            percent=100,
            message=f"备份完成！包含 {len(movies_data)} 部电影、{len(poster_files)} 张海报",
            elapsed_seconds=elapsed,
            result={
                "success": True,
                "filename": filename,
                "file_size": file_size,
                "movie_count": len(movies_data),
                "poster_count": len(poster_files),
                "version_count": len(versions_data),
                "elapsed_seconds": elapsed,
            },
        )

        logger.info(f"Backup created: {filename} ({len(movies_data)} movies, {len(poster_files)} posters)")
        return backup_progress["result"]

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        _reset_progress()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def list_backup_files() -> list[dict]:
    """List all backup files in backup directory."""
    if not BACKUP_DIR.exists():
        return []

    files = []
    for f in sorted(BACKUP_DIR.glob("backup_*.zip"), reverse=True):
        try:
            with zipfile.ZipFile(f, 'r') as zf:
                manifest_data = zf.read("manifest.json")
                manifest = json.loads(manifest_data)

            stat = f.stat()
            files.append({
                "filename": f.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "manifest": manifest,
                "movie_count": manifest.get("movie_count", 0),
                "poster_count": manifest.get("poster_count", 0),
                "versions": manifest.get("versions", []),
            })
        except Exception as e:
            logger.warning(f"Failed to read backup {f.name}: {e}")
            # 仍然列出文件，但标记为损坏
            files.append({
                "filename": f.name,
                "size": f.stat().st_size,
                "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "manifest": None,
                "movie_count": 0,
                "poster_count": 0,
                "versions": [],
                "corrupted": True,
            })

    return files


def get_backup_manifest(filename: str) -> dict | None:
    """Get manifest from a backup file."""
    filepath = BACKUP_DIR / filename
    if not filepath.exists():
        return None

    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            manifest_data = zf.read("manifest.json")
            return json.loads(manifest_data)
    except Exception as e:
        logger.error(f"Failed to read manifest from {filename}: {e}")
        return None


def restore_backup(filename: str, mode: str = "append") -> dict:
    """Restore backup from file."""
    global backup_progress

    if backup_progress["active"]:
        return {"success": False, "error": "备份/恢复操作正在进行中"}

    filepath = BACKUP_DIR / filename
    if not filepath.exists():
        return {"success": False, "error": f"备份文件不存在: {filename}"}

    _reset_progress()
    start_time = time.time()

    try:
        db = SessionLocal()

        # 1. 解压文件
        _update_progress(
            active=True,
            type="restore",
            step="extracting",
            current=50,
            total=100,
            message="正在解压备份文件...",
        )

        with zipfile.ZipFile(filepath, 'r') as zf:
            manifest = json.loads(zf.read("manifest.json"))
            data = json.loads(zf.read("data.json"))

            # 检查备份格式
            if "movies" not in data or "versions" not in data or "version_entries" not in data:
                _reset_progress()
                return {"success": False, "error": "备份文件格式无效"}

            # 提取海报到临时目录
            import tempfile
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)

                # 提取海报文件
                poster_files = [f for f in zf.namelist() if f.startswith("posters/")]
                for pf in poster_files:
                    zf.extract(pf, tmp_path)

                _update_progress(current=100)

                # 2. 覆盖模式：清除现有数据
                if mode == "overwrite":
                    _update_progress(
                        step="clearing",
                        current=0,
                        total=3,
                        message="正在清除现有数据...",
                    )

                    # 删除版本条目
                    db.query(VersionEntry).delete()
                    _update_progress(current=1)

                    # 删除版本
                    db.query(Version).delete()
                    _update_progress(current=2)

                    # 删除无关联的电影
                    # 先获取所有有关联的电影 ID
                    linked_movie_ids = set()
                    # 覆盖模式下暂时没有关联

                    db.commit()
                    _update_progress(current=3)

                # 3. 导入电影
                movies = data["movies"]
                _update_progress(
                    step="importing_movies",
                    current=0,
                    total=len(movies),
                    message=f"正在导入电影数据 ({len(movies)} 部)...",
                )

                imported_movies = 0
                skipped_movies = 0
                movie_id_map = {}  # douban_id -> movie.id

                for i, movie_data in enumerate(movies):
                    douban_id = movie_data.get("douban_id")
                    if not douban_id:
                        skipped_movies += 1
                        _update_progress(current=i + 1, detail=f"已导入 {imported_movies} | 跳过 {skipped_movies}")
                        continue

                    existing = db.query(Movie).filter(Movie.douban_id == douban_id).first()
                    if existing:
                        # 追加模式：跳过已存在的电影
                        movie_id_map[douban_id] = existing.id
                        skipped_movies += 1
                    else:
                        # 创建新电影
                        new_movie = Movie(
                            douban_id=douban_id,
                            imdb_id=movie_data.get("imdb_id"),
                            title=movie_data.get("title", ""),
                            original_title=movie_data.get("original_title"),
                            year=movie_data.get("year"),
                            country=movie_data.get("country"),
                            genre=movie_data.get("genre"),
                            director=movie_data.get("director"),
                            cast_members=movie_data.get("cast_members"),
                            duration=movie_data.get("duration"),
                            rating=movie_data.get("rating"),
                            rating_count=movie_data.get("rating_count"),
                            tagline=movie_data.get("tagline"),
                            summary=movie_data.get("summary"),
                            poster_path=movie_data.get("poster_path"),
                            douban_url=movie_data.get("douban_url"),
                            detail_fetched=True,
                        )
                        db.add(new_movie)
                        db.flush()
                        movie_id_map[douban_id] = new_movie.id
                        imported_movies += 1

                    _update_progress(
                        current=i + 1,
                        detail=f"已导入 {imported_movies} | 跳过 {skipped_movies}",
                    )

                db.commit()

                # 4. 导入版本
                versions = data["versions"]
                _update_progress(
                    step="importing_versions",
                    current=0,
                    total=len(versions),
                    message="正在导入版本数据...",
                )

                imported_versions = 0
                skipped_versions = 0
                version_id_map = {}  # (tag, source) -> version.id

                for i, version_data in enumerate(versions):
                    tag = version_data.get("tag")
                    source = version_data.get("source")

                    existing = db.query(Version).filter(
                        Version.tag == tag,
                        Version.source == source,
                    ).first()

                    if existing:
                        if mode == "append":
                            # 追加模式：跳过已存在的版本
                            version_id_map[(tag, source)] = existing.id
                            skipped_versions += 1
                        else:
                            # 覆盖模式：不应该到这里（已清除）
                            version_id_map[(tag, source)] = existing.id
                            skipped_versions += 1
                    else:
                        new_version = Version(
                            tag=tag,
                            source=source,
                            status=version_data.get("status", "confirmed"),
                            crawled_at=datetime.fromisoformat(version_data["crawled_at"]) if version_data.get("crawled_at") else now(),
                            movie_count=version_data.get("movie_count", 0),
                        )
                        db.add(new_version)
                        db.flush()
                        version_id_map[(tag, source)] = new_version.id
                        imported_versions += 1

                    _update_progress(current=i + 1)

                db.commit()

                # 5. 导入版本条目
                entries = data["version_entries"]
                _update_progress(
                    step="importing_entries",
                    current=0,
                    total=len(entries),
                    message="正在导入版本条目...",
                )

                imported_entries = 0
                skipped_entries = 0

                for i, entry_data in enumerate(entries):
                    tag = entry_data.get("version_tag")
                    source = entry_data.get("version_source")
                    douban_id = entry_data.get("movie_douban_id")

                    version_id = version_id_map.get((tag, source))
                    movie_id = movie_id_map.get(douban_id)

                    if not version_id or not movie_id:
                        skipped_entries += 1
                        _update_progress(current=i + 1)
                        continue

                    # 检查是否已存在
                    existing = db.query(VersionEntry).filter(
                        VersionEntry.version_id == version_id,
                        VersionEntry.movie_id == movie_id,
                    ).first()

                    if existing:
                        skipped_entries += 1
                    else:
                        new_entry = VersionEntry(
                            version_id=version_id,
                            movie_id=movie_id,
                            rank=entry_data.get("rank"),
                            rating=entry_data.get("rating"),
                        )
                        db.add(new_entry)
                        imported_entries += 1

                    _update_progress(current=i + 1)

                db.commit()

                # 6. 导入海报
                posters_dir = settings.posters_dir
                posters_dir.mkdir(parents=True, exist_ok=True)

                _update_progress(
                    step="importing_posters",
                    current=0,
                    total=len(poster_files),
                    message=f"正在导入海报文件 ({len(poster_files)} 张)...",
                )

                imported_posters = 0
                skipped_posters = 0

                for i, pf in enumerate(poster_files):
                    poster_name = pf.replace("posters/", "")
                    target_path = posters_dir / poster_name

                    if target_path.exists():
                        skipped_posters += 1
                    else:
                        source_path = tmp_path / pf
                        if source_path.exists():
                            shutil.copy2(source_path, target_path)
                            imported_posters += 1
                        else:
                            skipped_posters += 1

                    _update_progress(
                        current=i + 1,
                        detail=f"已导入 {imported_posters} | 跳过 {skipped_posters}",
                    )

        # 7. 完成
        elapsed = int(time.time() - start_time)

        _update_progress(
            active=False,
            step="completed",
            current=backup_progress["total"],
            total=backup_progress["total"],
            percent=100,
            message=f"恢复完成！",
            elapsed_seconds=elapsed,
            result={
                "success": True,
                "mode": mode,
                "movies_imported": imported_movies,
                "movies_skipped": skipped_movies,
                "versions_imported": imported_versions,
                "versions_skipped": skipped_versions,
                "entries_imported": imported_entries,
                "entries_skipped": skipped_entries,
                "posters_imported": imported_posters,
                "posters_skipped": skipped_posters,
                "elapsed_seconds": elapsed,
            },
        )

        logger.info(f"Restore completed: {filename} (mode={mode})")
        return backup_progress["result"]

    except Exception as e:
        logger.error(f"Restore failed: {e}")
        _reset_progress()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def delete_backup(filename: str) -> dict:
    """Delete a backup file."""
    filepath = BACKUP_DIR / filename
    if not filepath.exists():
        return {"success": False, "error": f"备份文件不存在: {filename}"}

    try:
        filepath.unlink()
        logger.info(f"Backup deleted: {filename}")
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to delete backup {filename}: {e}")
        return {"success": False, "error": str(e)}
