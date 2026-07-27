"""Tests for _get_cookie() — system cookie resolution.

System cookie is the admin user's douban_cookie.
No Setting fallback, no env var fallback.
"""
import pytest

from app.database import SessionLocal
from app.models import User, Setting
from app.utils.http_client import _get_cookie


@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(autouse=True)
def clean_cookie_state(db_session):
    """Each test starts with no cookies in User or Setting."""
    db_session.query(User).update({User.douban_cookie: None})
    db_session.query(Setting).filter(Setting.key == "douban_cookie").delete()
    db_session.commit()
    yield
    db_session.query(User).update({User.douban_cookie: None})
    db_session.query(Setting).filter(Setting.key == "douban_cookie").delete()
    db_session.commit()


class TestGetCookieResolution:
    """_get_cookie() returns the admin user's douban_cookie."""

    def test_returns_admin_cookie(self, db_session):
        """When admin has a cookie, _get_cookie() returns it."""
        admin = db_session.query(User).filter(User.role == "admin").first()
        admin.douban_cookie = "bid=admin_cookie_value; ck=abc"
        db_session.commit()

        assert _get_cookie() == "bid=admin_cookie_value; ck=abc"

    def test_returns_empty_when_no_admin_cookie(self, db_session):
        """When admin has no cookie configured, _get_cookie() returns empty string."""
        admin = db_session.query(User).filter(User.role == "admin").first()
        admin.douban_cookie = None
        db_session.commit()

        assert _get_cookie() == ""

    def test_ignores_setting_table(self, db_session):
        """Setting row with douban_cookie is ignored — admin User is the source of truth."""
        admin = db_session.query(User).filter(User.role == "admin").first()
        admin.douban_cookie = "bid=admin_value"
        # Setting has a DIFFERENT (stale) value
        setting = db_session.query(Setting).filter(Setting.key == "douban_cookie").first()
        if setting:
            setting.value = "bid=stale_setting_value"
        else:
            db_session.add(Setting(key="douban_cookie", value="bid=stale_setting_value"))
        db_session.commit()

        assert _get_cookie() == "bid=admin_value"

    def test_ignores_non_admin_cookies(self, db_session):
        """Non-admin users' cookies don't affect system cookie."""
        admin = db_session.query(User).filter(User.role == "admin").first()
        admin.douban_cookie = None

        # Create a regular user with a cookie
        regular = db_session.query(User).filter(User.role == "user").first()
        if regular:
            regular.douban_cookie = "bid=regular_user_cookie"
            db_session.commit()

        assert _get_cookie() == ""

    def test_picks_any_admin_with_cookie(self, db_session):
        """If multiple admins exist, returns one that has a cookie."""
        # Set all admins to None first
        db_session.query(User).filter(User.role == "admin").update({User.douban_cookie: None})

        admin = db_session.query(User).filter(User.role == "admin").first()
        admin.douban_cookie = "bid=picked_admin"
        db_session.commit()

        assert _get_cookie() == "bid=picked_admin"
