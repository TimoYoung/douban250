from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas import BeijingBaseModel


class CookieCheckRequest(BaseModel):
    """Cookie 有效性检查请求体。

    使用 BaseModel 而非 BeijingBaseModel —— 本 schema 不含时间字段，
    不需要 UTC+8 时区序列化，避免误导维护者。
    """
    cookie: str | None = None


class CrawlLogInfo(BeijingBaseModel):
    id: int
    job_type: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    new_version_created: bool = False
    error_message: Optional[str] = None
    movies_found: Optional[int] = None
    retry_of: Optional[int] = None


class CrawlTriggerResponse(BeijingBaseModel):
    message: str
    triggered: bool


class RetryStatusResponse(BeijingBaseModel):
    """重试状态响应"""
    status: str  # "pending", "running", "cancelled", "exhausted", "failed"
    retry_count: int
    max_retries: int
    next_retry: Optional[datetime] = None
    last_error: Optional[str] = None
    interval: int


class RetryCancelResponse(BeijingBaseModel):
    """取消重试响应"""
    message: str
    cancelled: bool
