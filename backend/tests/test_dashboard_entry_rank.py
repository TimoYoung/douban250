"""回归测试: 概览-进出-新上榜电影排名应显示入榜那期的排名，而非最新版的排名。

场景:
- 4 个版本 v1, v2, v3, v4 (douban)
- v1: {A@1, B@2, C@3}
- v2: {A@1, B@2, D@3}         — C 跌出, D 新入 (rank=3)
- v3: {A@1, B@2, D@5}         — 同电影集合, D 排名变为 5
- v4: {A@1, B@2, D@7}         — 同电影集合, D 排名变为 7

"进出"卡片比较 v4 vs v1 (prev_changed=v1, 因为 v1 是第一个与 v4 集合不同的版本)
added = {D}, removed = {C}

新上榜 D:
  - 当前 bug: 显示 v4 的排名 #7 (latest version)
  - 期望行为: 显示 v2 的排名 #3 (入榜那一期)

跌出 C:
  - 显示 v1 的排名 #3 (跌出前最后一期) — 这是正确的
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone, timedelta

from app.models.movie import Movie, Version, VersionEntry
from app.api.analytics import get_dashboard


def seed_data(db):
    base = datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=8)))

    # 4 movies
    ma = Movie(id=1, douban_id="1001", title="Movie A")
    mb = Movie(id=2, douban_id="1002", title="Movie B")
    mc = Movie(id=3, douban_id="1003", title="Movie C")
    md = Movie(id=4, douban_id="1004", title="Movie D")
    db.add_all([ma, mb, mc, md])

    # 4 versions for douban
    v1 = Version(id=1, tag="2026-01-01", source="douban", status="confirmed",
                 crawled_at=base, movie_count=3)
    v2 = Version(id=2, tag="2026-01-02", source="douban", status="confirmed",
                 crawled_at=base + timedelta(days=1), movie_count=3)
    v3 = Version(id=3, tag="2026-01-03", source="douban", status="confirmed",
                 crawled_at=base + timedelta(days=2), movie_count=3)
    v4 = Version(id=4, tag="2026-01-04", source="douban", status="confirmed",
                 crawled_at=base + timedelta(days=3), movie_count=3)
    db.add_all([v1, v2, v3, v4])
    db.flush()

    # v1: A@1, B@2, C@3
    db.add_all([
        VersionEntry(version_id=1, movie_id=1, rank=1),
        VersionEntry(version_id=1, movie_id=2, rank=2),
        VersionEntry(version_id=1, movie_id=3, rank=3),
    ])
    # v2: A@1, B@2, D@3 (C dropped, D entered at rank 3)
    db.add_all([
        VersionEntry(version_id=2, movie_id=1, rank=1),
        VersionEntry(version_id=2, movie_id=2, rank=2),
        VersionEntry(version_id=2, movie_id=4, rank=3),
    ])
    # v3: A@1, B@2, D@5 (same movies, D rank changed to 5)
    db.add_all([
        VersionEntry(version_id=3, movie_id=1, rank=1),
        VersionEntry(version_id=3, movie_id=2, rank=2),
        VersionEntry(version_id=3, movie_id=4, rank=5),
    ])
    # v4: A@1, B@2, D@7 (same movies, D rank changed to 7)
    db.add_all([
        VersionEntry(version_id=4, movie_id=1, rank=1),
        VersionEntry(version_id=4, movie_id=2, rank=2),
        VersionEntry(version_id=4, movie_id=4, rank=7),
    ])
    db.commit()


def test_added_movie_shows_entry_rank(db_factory):
    db = db_factory()
    seed_data(db)

    result = get_dashboard(db=db)
    douban = result.douban

    print(f"\n=== Dashboard 进出卡片 ===")
    print(f"prev_changed: {douban.prev_changed_tag}")
    print(f"latest: {douban.latest_tag}")
    print(f"Added: {douban.changes.added}, Removed: {douban.changes.removed}")

    errors = []

    # 验证 prev_changed 是 v1
    if douban.prev_changed_tag != "2026-01-01":
        errors.append(f"prev_changed_tag={douban.prev_changed_tag}, expected 2026-01-01")

    # ── 新上榜 D: 应显示入榜版本 v2 的 rank=3, 而非最新版 v4 的 rank=7 ──
    added = douban.changes.added_movies
    print(f"\n新上榜 movies:")
    for m in added:
        print(f"  movie_id={m['movie_id']}, title={m['title']}, rank={m['rank']}")

    movie_d = next((m for m in added if m["movie_id"] == 4), None)
    if movie_d is None:
        errors.append("Movie D (id=4) not found in added_movies!")
    elif movie_d["rank"] != 3:
        errors.append(
            f"FAIL: Movie D added rank={movie_d['rank']}, expected 3 "
            f"(entry rank from v2), got {movie_d['rank']} "
            f"(latest v4 rank=7 is WRONG)"
        )
    else:
        print("✓ Movie D: added rank=3 (correct — from entry version v2)")

    # ── 跌出 C: 应显示 v1 的 rank=3 (跌出前最后一期) ──
    removed = douban.changes.removed_movies
    print(f"\n跌出榜 movies:")
    for m in removed:
        print(f"  movie_id={m['movie_id']}, title={m['title']}, rank={m['rank']}")

    movie_c = next((m for m in removed if m["movie_id"] == 3), None)
    if movie_c is None:
        errors.append("Movie C (id=3) not found in removed_movies!")
    elif movie_c["rank"] != 3:
        errors.append(f"FAIL: Movie C removed rank={movie_c['rank']}, expected 3")
    else:
        print("✓ Movie C: removed rank=3 (correct — from last version v1)")

    if errors:
        print(f"\n=== FAILURES ===")
        for e in errors:
            print(f"  {e}")
        print(f"\n❌ TEST FAILED — {len(errors)} error(s)")
        assert False, f"Dashboard 进出 rank errors: {errors}"
    else:
        print("\n✅ TEST PASSED")


if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.database import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    test_added_movie_shows_entry_rank(Session)
