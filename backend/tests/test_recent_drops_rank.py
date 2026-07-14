"""Regression test: 首次跌出排名显示 #0 bug。

场景：
- 3 个版本 v1, v2, v3 (douban)
- Movie A (mid=1): 在 v1(rank=5), v2(rank=3), 不在 v3 → 应该在 v3 跌出，drop_rank=3
- Movie B (mid=2): 在 v1(rank=10), v2(rank=8), v3(rank=7) → 还在榜，不应出现在 drops
- Movie C (mid=3): 在 v1(rank=20), 不在 v2, 不在 v3 → 应该在 v2 跌出，drop_rank=20
"""

import sys
import os

# Ensure we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.movie import Movie, Version, VersionEntry
from app.api.analytics import get_recent_drops, get_recent_debuts


def setup_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def seed_data(db):
    now = datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=8)))

    # 3 movies
    m1 = Movie(id=1, douban_id="1001", title="Movie A")
    m2 = Movie(id=2, douban_id="1002", title="Movie B")
    m3 = Movie(id=3, douban_id="1003", title="Movie C")
    db.add_all([m1, m2, m3])

    # 3 versions for douban, ordered by crawled_at
    v1 = Version(id=1, tag="2026-01-01", source="douban", status="confirmed",
                 crawled_at=now, movie_count=2)
    v2 = Version(id=2, tag="2026-01-02", source="douban", status="confirmed",
                 crawled_at=now + timedelta(days=1), movie_count=2)
    v3 = Version(id=3, tag="2026-01-03", source="douban", status="confirmed",
                 crawled_at=now + timedelta(days=2), movie_count=1)
    db.add_all([v1, v2, v3])
    db.flush()

    # v1: m1(rank=5), m2(rank=10), m3(rank=20)
    db.add_all([
        VersionEntry(version_id=1, movie_id=1, rank=5),
        VersionEntry(version_id=1, movie_id=2, rank=10),
        VersionEntry(version_id=1, movie_id=3, rank=20),
    ])
    # v2: m1(rank=3), m2(rank=8)  → m3 dropped out
    db.add_all([
        VersionEntry(version_id=2, movie_id=1, rank=3),
        VersionEntry(version_id=2, movie_id=2, rank=8),
    ])
    # v3: m2(rank=7)  → m1 dropped out
    db.add_all([
        VersionEntry(version_id=3, movie_id=2, rank=7),
    ])
    db.commit()


def test_drops_show_correct_rank():
    db = setup_db()
    seed_data(db)

    # Override dependency — but since get_recent_drops uses Depends(get_db),
    # we call it directly passing db.
    result = get_recent_drops(top_n=3, db=db)

    # Expect: douban drops grouped by drop version
    douban_drops = result.douban
    print(f"\n=== RESULT ===")
    print(f"Number of drop groups: {len(douban_drops)}")

    all_drops = []
    for group in douban_drops:
        print(f"\nDrop group: tag={group.drop_tag}, version_id={group.drop_version_id}")
        for m in group.movies:
            print(f"  movie_id={m.movie_id}, title={m.title}, drop_rank={m.drop_rank}")
            all_drops.append(m)

    # Assertions
    errors = []

    # Movie A (id=1): last in v2(rank=3), dropped at v3 → drop_rank should be 3
    movie_a = next((m for m in all_drops if m.movie_id == 1), None)
    if movie_a is None:
        errors.append("FAIL: Movie A (id=1) not found in drops!")
    elif movie_a.drop_rank != 3:
        errors.append(f"FAIL: Movie A drop_rank={movie_a.drop_rank}, expected 3")
    else:
        print("\n✓ Movie A: drop_rank=3 (correct)")

    # Movie C (id=3): last in v1(rank=20), dropped at v2 → drop_rank should be 20
    movie_c = next((m for m in all_drops if m.movie_id == 3), None)
    if movie_c is None:
        errors.append("FAIL: Movie C (id=3) not found in drops!")
    elif movie_c.drop_rank != 20:
        errors.append(f"FAIL: Movie C drop_rank={movie_c.drop_rank}, expected 20")
    else:
        print("✓ Movie C: drop_rank=20 (correct)")

    # Movie B (id=2): still in v3 → should NOT appear in drops
    movie_b = next((m for m in all_drops if m.movie_id == 2), None)
    if movie_b is not None:
        errors.append(f"FAIL: Movie B (id=2) should NOT be in drops, but found with drop_rank={movie_b.drop_rank}")
    else:
        print("✓ Movie B: correctly absent from drops")

    if errors:
        print("\n=== FAILURES ===")
        for e in errors:
            print(f"  {e}")
        print(f"\n❌ TEST FAILED — {len(errors)} error(s)")
        assert False, f"Drop rank errors: {errors}"
    else:
        print("\n✅ DROP TEST PASSED")

    # ── Also verify debuts are unaffected ──
    print("\n--- Debuts Check ---")
    result_debuts = get_recent_debuts(top_n=3, db=db)
    douban_debuts = result_debuts.douban
    print(f"Number of debut groups: {len(douban_debuts)}")

    debut_errors = []
    for group in douban_debuts:
        print(f"\nDebut group: tag={group.debut_tag}, version_id={group.debut_version_id}")
        for m in group.movies:
            print(f"  movie_id={m.movie_id}, title={m.title}, debut_rank={m.debut_rank}")

    # All 3 movies first appear in v1
    if len(douban_debuts) != 1:
        debut_errors.append(f"Expected 1 debut group, got {len(douban_debuts)}")
    else:
        group = douban_debuts[0]
        expected_ranks = {1: 5, 2: 10, 3: 20}
        for m in group.movies:
            expected = expected_ranks.get(m.movie_id)
            if m.debut_rank != expected:
                debut_errors.append(f"Movie {m.movie_id} debut_rank={m.debut_rank}, expected {expected}")
            else:
                print(f"✓ Movie {m.movie_id}: debut_rank={expected} (correct)")

    if debut_errors:
        for e in debut_errors:
            print(f"  {e}")
        print(f"\n❌ DEBUT TEST FAILED")
        assert False, f"Debut test failed: {debut_errors}"
    else:
        print("\n✅ DEBUT TEST PASSED")


if __name__ == "__main__":
    test_drops_show_correct_rank()
