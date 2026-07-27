from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _run_migrations(db):
    """运行增量迁移。"""
    # 检查 pending_matches 表是否有 version_id 列
    result = db.execute(text("PRAGMA table_info(pending_matches)"))
    columns = {row[1] for row in result}
    if 'version_id' not in columns:
        db.execute(text(
            "ALTER TABLE pending_matches "
            "ADD COLUMN version_id INTEGER REFERENCES versions(id)"))
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS "
            "ix_pending_matches_version_id "
            "ON pending_matches(version_id)"))
        db.commit()

    # 版本表：tag 唯一约束改为 (tag, source) 联合唯一
    # SQLite 不支持修改约束，需要重建表
    indexes = db.execute(text("PRAGMA index_list(versions)")).fetchall()
    has_tag_only_unique = False
    for idx in indexes:
        idx_name = idx[1]
        idx_unique = idx[2]
        if idx_unique:
            cols = db.execute(text(
                f"PRAGMA index_info('{idx_name}')")).fetchall()
            col_names = [c[2] for c in cols]
            if col_names == ['tag']:
                has_tag_only_unique = True
                break
    if has_tag_only_unique:
        db.execute(text(
            "CREATE TABLE IF NOT EXISTS versions_new ("
            "id INTEGER PRIMARY KEY, "
            "tag VARCHAR(20) NOT NULL, "
            "source VARCHAR(20) NOT NULL DEFAULT 'douban', "
            "status VARCHAR(30) NOT NULL DEFAULT 'confirmed', "
            "crawled_at DATETIME NOT NULL, "
            "movie_count INTEGER NOT NULL DEFAULT 250, "
            "UNIQUE(tag, source))"))
        db.execute(text(
            "INSERT OR IGNORE INTO versions_new "
            "(id, tag, source, status, crawled_at, movie_count) "
            "SELECT id, tag, source, status, crawled_at, movie_count "
            "FROM versions"))
        db.execute(text("DROP TABLE versions"))
        db.execute(text("ALTER TABLE versions_new RENAME TO versions"))
        db.commit()

    # 检查 movies 表是否有 last_meta_fetch 列
    result = db.execute(text("PRAGMA table_info(movies)"))
    columns = {row[1] for row in result}
    if 'last_meta_fetch' not in columns:
        db.execute(text(
            "ALTER TABLE movies "
            "ADD COLUMN last_meta_fetch DATETIME"))
        db.commit()

    # 检查 movies 表是否有 meta_fetch_failures 和 last_meta_attempt 列
    result = db.execute(text("PRAGMA table_info(movies)"))
    columns = {row[1] for row in result}
    if 'meta_fetch_failures' not in columns:
        db.execute(text(
            "ALTER TABLE movies "
            "ADD COLUMN meta_fetch_failures INTEGER DEFAULT 0 NOT NULL"))
        db.commit()
    if 'last_meta_attempt' not in columns:
        db.execute(text(
            "ALTER TABLE movies "
            "ADD COLUMN last_meta_attempt DATETIME"))
        db.commit()

    # 检查 movies 表是否有 duration 列
    result = db.execute(text("PRAGMA table_info(movies)"))
    columns = {row[1] for row in result}
    if 'duration' not in columns:
        db.execute(text(
            "ALTER TABLE movies "
            "ADD COLUMN duration INTEGER"))
        db.commit()

    # 检查 crawl_logs 表是否有 retry_of 列
    result = db.execute(text("PRAGMA table_info(crawl_logs)"))
    columns = {row[1] for row in result}
    if 'retry_of' not in columns:
        db.execute(text(
            "ALTER TABLE crawl_logs "
            "ADD COLUMN retry_of INTEGER REFERENCES crawl_logs(id)"))
        db.commit()

    # 创建 users 表（多用户认证）
    tables = {row[0] for row in db.execute(
        text("SELECT name FROM sqlite_master WHERE type='table'")
    ).fetchall()}
    if 'users' not in tables:
        db.execute(text(
            "CREATE TABLE users ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "username VARCHAR(50) NOT NULL UNIQUE, "
            "hashed_password VARCHAR(200) NOT NULL, "
            "role VARCHAR(20) NOT NULL DEFAULT 'user', "
            "douban_user_id VARCHAR(20), "
            "douban_cookie TEXT, "
            "is_active BOOLEAN DEFAULT 1, "
            "created_at DATETIME, "
            "updated_at DATETIME)"))
        db.commit()

    # 引导默认管理员（表存在但无用户时执行）
    user_count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
    if user_count == 0:
        from app.utils import now as _now
        uid_row = db.execute(text(
            "SELECT value FROM settings WHERE key='douban_user_id'")).fetchone()
        cookie_row = db.execute(text(
            "SELECT value FROM settings WHERE key='douban_cookie'")).fetchone()
        migrated_uid = uid_row[0] if uid_row else None
        migrated_cookie = cookie_row[0] if cookie_row else None

        from passlib.context import CryptContext
        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd_ctx.hash(settings.default_admin_password)
        ts = _now().isoformat()

        db.execute(text(
            "INSERT INTO users (username, hashed_password, role, douban_user_id, "
            "douban_cookie, is_active, created_at, updated_at) "
            "VALUES ('admin', :hashed, 'admin', :uid, :cookie, 1, :ts, :ts)"),
            {"hashed": hashed, "uid": migrated_uid, "cookie": migrated_cookie, "ts": ts})
        # 迁移完成：清理旧的 Setting 行，admin User 是唯一数据源
        if migrated_cookie:
            db.execute(text("DELETE FROM settings WHERE key='douban_cookie'"))
        db.commit()


def init_db():
    Base.metadata.create_all(bind=engine)
    # 运行迁移
    db = SessionLocal()
    try:
        _run_migrations(db)
    finally:
        db.close()
