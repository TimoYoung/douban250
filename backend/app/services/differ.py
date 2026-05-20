from sqlalchemy.orm import Session

from app.models import Movie, Version, VersionEntry


def compute_diff(db: Session, version_id_a: int, version_id_b: int, top_n: int = 10) -> dict:
    """Compare two versions and return the diff."""
    # Get entries for both versions
    entries_a = _get_version_entries(db, version_id_a)
    entries_b = _get_version_entries(db, version_id_b)

    # Build lookup: douban_id -> rank
    map_a = {e["douban_id"]: e for e in entries_a}
    map_b = {e["douban_id"]: e for e in entries_b}

    ids_a = set(map_a.keys())
    ids_b = set(map_b.keys())

    added_ids = ids_b - ids_a
    removed_ids = ids_a - ids_b
    common_ids = ids_a & ids_b

    # Added movies (in B but not A)
    added = [map_b[did] for did in sorted(added_ids, key=lambda x: map_b[x]["rank"])]

    # Removed movies (in A but not B)
    removed = [map_a[did] for did in sorted(removed_ids, key=lambda x: map_a[x]["rank"])]

    # Rank changes (positive = rank went up, negative = rank went down)
    rank_changes = []
    for did in common_ids:
        old_rank = map_a[did]["rank"]
        new_rank = map_b[did]["rank"]
        delta = old_rank - new_rank  # positive means rank improved (went from 10 to 5 = +5)
        rank_changes.append({
            "douban_id": did,
            "title": map_b[did]["title"],
            "old_rank": old_rank,
            "new_rank": new_rank,
            "delta": delta,
        })

    rank_changes.sort(key=lambda x: abs(x["delta"]), reverse=True)
    rank_up = [r for r in rank_changes if r["delta"] > 0][:top_n]
    rank_down = [r for r in rank_changes if r["delta"] < 0][:top_n]

    return {
        "added": added,
        "removed": removed,
        "rank_up": rank_up,
        "rank_down": rank_down,
    }


def _get_version_entries(db: Session, version_id: int) -> list[dict]:
    """Get version entries with movie info."""
    results = (
        db.query(VersionEntry, Movie)
        .join(Movie, VersionEntry.movie_id == Movie.id)
        .filter(VersionEntry.version_id == version_id)
        .order_by(VersionEntry.rank)
        .all()
    )
    return [
        {
            "douban_id": movie.douban_id,
            "title": movie.title,
            "rank": entry.rank,
            "rating": entry.rating,
            "poster_path": movie.poster_path,
        }
        for entry, movie in results
    ]
