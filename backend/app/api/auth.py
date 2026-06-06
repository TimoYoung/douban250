from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.auth import hash_password, verify_password, create_access_token
from app.dependencies import require_user, require_admin
from app.schemas.auth import (
    LoginRequest, LoginResponse, UserInfo,
    PasswordChangeRequest, UserDoubanSettingsUpdate,
    AdminUserCreate, AdminUserUpdate, UserListItem,
)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "用户名或密码错误")
    if not user.is_active:
        raise HTTPException(403, "账号已被禁用")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return LoginResponse(
        access_token=token,
        user=UserInfo(
            id=user.id,
            username=user.username,
            role=user.role,
            douban_user_id=user.douban_user_id,
            douban_cookie=user.douban_cookie,
            is_active=user.is_active,
        ),
    )


@router.get("/me", response_model=UserInfo)
def get_me(user: User = Depends(require_user)):
    return UserInfo(
        id=user.id,
        username=user.username,
        role=user.role,
        douban_user_id=user.douban_user_id,
        douban_cookie=user.douban_cookie,
        is_active=user.is_active,
    )


@router.put("/password")
def change_password(body: PasswordChangeRequest, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if not verify_password(body.old_password, user.hashed_password):
        raise HTTPException(400, "原密码错误")
    user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"message": "密码修改成功"}


@router.put("/douban-settings", response_model=UserInfo)
def update_my_douban_settings(body: UserDoubanSettingsUpdate, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if body.douban_user_id is not None:
        user.douban_user_id = body.douban_user_id or None
    if body.douban_cookie is not None:
        user.douban_cookie = body.douban_cookie or None
    db.commit()
    db.refresh(user)
    return UserInfo(
        id=user.id,
        username=user.username,
        role=user.role,
        douban_user_id=user.douban_user_id,
        is_active=user.is_active,
    )


# ── Admin endpoints ──────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserListItem])
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id).all()
    return [
        UserListItem(
            id=u.id, username=u.username, role=u.role,
            douban_user_id=u.douban_user_id, is_active=u.is_active,
            created_at=u.created_at.isoformat() if u.created_at else None,
        )
        for u in users
    ]


@router.post("/users", response_model=UserListItem)
def create_user(body: AdminUserCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, "用户名已存在")
    if body.role not in ("user", "admin"):
        raise HTTPException(400, "角色只能是 user 或 admin")
    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        role=body.role,
        douban_user_id=body.douban_user_id or None,
        douban_cookie=body.douban_cookie or None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserListItem(
        id=user.id, username=user.username, role=user.role,
        douban_user_id=user.douban_user_id, is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.put("/users/{user_id}", response_model=UserListItem)
def update_user(user_id: int, body: AdminUserUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    if body.role is not None:
        if body.role not in ("user", "admin"):
            raise HTTPException(400, "角色只能是 user 或 admin")
        if user_id == admin.id and body.role != "admin":
            raise HTTPException(400, "不能修改自己的角色")
        user.role = body.role
    if body.is_active is not None:
        if user_id == admin.id and not body.is_active:
            raise HTTPException(400, "不能禁用自己")
        user.is_active = body.is_active
    if body.password is not None:
        user.hashed_password = hash_password(body.password)
    if body.douban_user_id is not None:
        user.douban_user_id = body.douban_user_id or None
    if body.douban_cookie is not None:
        user.douban_cookie = body.douban_cookie or None
    db.commit()
    db.refresh(user)
    return UserListItem(
        id=user.id, username=user.username, role=user.role,
        douban_user_id=user.douban_user_id, is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if user_id == admin.id:
        raise HTTPException(400, "不能删除自己")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    db.delete(user)
    db.commit()
    return {"message": "用户已删除"}
