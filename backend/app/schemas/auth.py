from pydantic import BaseModel

from app.schemas import BeijingBaseModel


class LoginRequest(BeijingBaseModel):
    username: str
    password: str


class LoginResponse(BeijingBaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserInfo"


class UserInfo(BeijingBaseModel):
    id: int
    username: str
    role: str
    douban_user_id: str | None = None
    douban_cookie: str | None = None
    is_active: bool = True


class PasswordChangeRequest(BeijingBaseModel):
    old_password: str
    new_password: str


class UserDoubanSettingsUpdate(BeijingBaseModel):
    douban_user_id: str | None = None
    douban_cookie: str | None = None


class AdminUserCreate(BeijingBaseModel):
    username: str
    password: str
    role: str = "user"
    douban_user_id: str | None = None
    douban_cookie: str | None = None


class AdminUserUpdate(BeijingBaseModel):
    role: str | None = None
    is_active: bool | None = None
    douban_user_id: str | None = None
    douban_cookie: str | None = None
    password: str | None = None


class UserListItem(BeijingBaseModel):
    id: int
    username: str
    role: str
    douban_user_id: str | None = None
    is_active: bool = True
    created_at: str | None = None
