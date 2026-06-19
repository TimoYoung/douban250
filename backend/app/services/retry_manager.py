"""
重试管理器模块

统一管理爬虫任务的重试逻辑，包括：
- 跟踪重试状态（内存+数据库）
- 安排重试（使用APScheduler的DateTrigger）
- 处理取消请求
- 与定时任务协调
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

from app.database import SessionLocal
from app.models import Setting
from app.models.crawl import CrawlLog
from app.utils import now

logger = logging.getLogger(__name__)


class RetryState:
    """重试状态枚举"""
    PENDING = "pending"      # 等待重试
    RUNNING = "running"      # 正在重试
    CANCELLED = "cancelled"  # 已取消
    EXHAUSTED = "exhausted"  # 已耗尽所有重试次数
    FAILED = "failed"        # 最终失败（重试后仍失败）


class RetryManager:
    """
    重试管理器

    负责管理爬虫任务的重试逻辑，支持：
    - 内存+数据库双重状态存储
    - 使用APScheduler安排重试
    - 取消等待中的重试
    - 与定时任务协调
    """

    def __init__(self, scheduler: BackgroundScheduler):
        self.scheduler = scheduler
        self._lock = threading.Lock()
        # 内存中的重试状态缓存
        self._retry_states: Dict[str, Dict[str, Any]] = {}
        # 任务ID前缀
        self._job_id_prefix = "retry_"
        # 初始化数据库中的重试参数
        self._init_retry_params()

    def _init_retry_params(self):
        """初始化重试参数到数据库（如果不存在）"""
        db = SessionLocal()
        try:
            # 检查并设置默认重试参数
            self._ensure_setting(db, "retry_interval", "3600")  # 默认1小时
            self._ensure_setting(db, "max_retries", "3")        # 默认3次
        finally:
            db.close()

    def _ensure_setting(self, db, key: str, default: str):
        """确保设置存在，如果不存在则创建"""
        setting = db.query(Setting).filter(Setting.key == key).first()
        if not setting:
            setting = Setting(key=key, value=default)
            db.add(setting)
            db.commit()

    def get_retry_params(self) -> Dict[str, int]:
        """获取重试参数"""
        db = SessionLocal()
        try:
            interval = self._get_setting(db, "retry_interval", "3600")
            max_retries = self._get_setting(db, "max_retries", "3")
            return {
                "retry_interval": int(interval),
                "max_retries": int(max_retries),
            }
        finally:
            db.close()

    def _get_setting(self, db, key: str, default: str) -> str:
        """从数据库获取设置值"""
        setting = db.query(Setting).filter(Setting.key == key).first()
        return setting.value if setting and setting.value else default

    def schedule_retry(self, job_type: str, error_message: str, crawl_log_id: Optional[int] = None) -> bool:
        """
        安排重试

        Args:
            job_type: 任务类型（"top250" 或 "imdb"）
            error_message: 错误信息
            crawl_log_id: 关联的CrawlLog ID（可选）

        Returns:
            bool: 是否成功安排重试
        """
        with self._lock:
            # 获取重试参数
            params = self.get_retry_params()
            max_retries = params["max_retries"]
            retry_interval = params["retry_interval"]

            # 获取当前重试状态
            state = self._get_retry_state(job_type)

            # 检查是否已耗尽重试次数
            if state["retry_count"] >= max_retries:
                logger.info(f"Retry exhausted for {job_type}: {state['retry_count']}/{max_retries}")
                self._update_retry_state(job_type, RetryState.EXHAUSTED)
                return False

            # 计算下次重试时间
            next_retry = now() + timedelta(seconds=retry_interval)

            # 更新重试状态
            new_retry_count = state["retry_count"] + 1
            self._update_retry_state(
                job_type,
                RetryState.PENDING,
                retry_count=new_retry_count,
                next_retry=next_retry,
                last_error=error_message,
                crawl_log_id=crawl_log_id,
            )

            # 安排APScheduler任务
            job_id = f"{self._job_id_prefix}{job_type}"
            try:
                # 移除已有的重试任务（如果有）
                try:
                    self.scheduler.remove_job(job_id)
                except Exception:
                    pass

                # 添加新的重试任务
                self.scheduler.add_job(
                    self._execute_retry,
                    trigger=DateTrigger(run_date=next_retry),
                    args=[job_type],
                    id=job_id,
                    replace_existing=True,
                )

                logger.info(f"Scheduled retry for {job_type} at {next_retry} (attempt {new_retry_count}/{max_retries})")
                return True

            except Exception as e:
                logger.error(f"Failed to schedule retry for {job_type}: {e}")
                self._update_retry_state(job_type, RetryState.FAILED)
                return False

    def _execute_retry(self, job_type: str):
        """执行重试"""
        with self._lock:
            # 更新状态为运行中
            self._update_retry_state(job_type, RetryState.RUNNING)

        try:
            # 根据任务类型执行相应的爬虫
            if job_type == "top250":
                from app.services.crawler import crawl_top250
                result = crawl_top250()
                self._handle_retry_result(job_type, result)

            elif job_type == "imdb":
                from app.services.imdb_crawler import crawl_imdb_top250
                result = crawl_imdb_top250(SessionLocal)
                self._handle_retry_result(job_type, result)

            else:
                logger.error(f"Unknown job type for retry: {job_type}")
                self._update_retry_state(job_type, RetryState.FAILED)

        except Exception as e:
            logger.error(f"Retry failed for {job_type}: {e}")
            # 重新安排重试
            self.schedule_retry(job_type, str(e))

    def _handle_retry_result(self, job_type: str, result: dict):
        """处理重试结果：成功则清除状态，失败则重新调度。"""
        status = result.get("status", "") if isinstance(result, dict) else ""
        if status == "error":
            error_msg = result.get("message", "Unknown error")
            logger.error(f"Retry failed for {job_type}: {error_msg}")
            self.schedule_retry(job_type, error_msg)
        else:
            logger.info(f"Retry succeeded for {job_type}: {result}")
            self._clear_retry_state(job_type)

    def cancel_retry(self, job_type: str) -> bool:
        """
        取消等待中的重试

        Args:
            job_type: 任务类型

        Returns:
            bool: 是否成功取消
        """
        with self._lock:
            state = self._get_retry_state(job_type)

            # 只有等待中的重试才能取消
            if state["status"] != RetryState.PENDING:
                logger.warning(f"Cannot cancel retry for {job_type}: status is {state['status']}")
                return False

            # 移除APScheduler任务
            job_id = f"{self._job_id_prefix}{job_type}"
            try:
                self.scheduler.remove_job(job_id)
            except Exception:
                pass

            # 更新状态为已取消
            self._update_retry_state(job_type, RetryState.CANCELLED)

            logger.info(f"Cancelled retry for {job_type}")
            return True

    def cancel_all_retries(self):
        """取消所有等待中的重试"""
        with self._lock:
            for job_type in list(self._retry_states.keys()):
                self.cancel_retry(job_type)

    def get_retry_status(self, job_type: str) -> Dict[str, Any]:
        """
        获取重试状态

        Args:
            job_type: 任务类型

        Returns:
            Dict: 重试状态信息
        """
        with self._lock:
            state = self._get_retry_state(job_type)
            params = self.get_retry_params()

            return {
                "status": state["status"],
                "retry_count": state["retry_count"],
                "max_retries": params["max_retries"],
                "next_retry": state["next_retry"].isoformat() if state["next_retry"] else None,
                "last_error": state["last_error"],
                "interval": params["retry_interval"],
            }

    def has_pending_retry(self, job_type: str) -> bool:
        """检查是否有等待中的重试"""
        with self._lock:
            state = self._get_retry_state(job_type)
            return state["status"] == RetryState.PENDING

    def _get_retry_state(self, job_type: str) -> Dict[str, Any]:
        """获取重试状态（从内存或数据库）"""
        if job_type in self._retry_states:
            return self._retry_states[job_type]

        # 从数据库加载
        db = SessionLocal()
        try:
            state = self._load_retry_state_from_db(db, job_type)
            self._retry_states[job_type] = state
            return state
        finally:
            db.close()

    def _load_retry_state_from_db(self, db, job_type: str) -> Dict[str, Any]:
        """从数据库加载重试状态"""
        # 查询最近的失败记录
        last_failed = db.query(CrawlLog).filter(
            CrawlLog.job_type == job_type,
            CrawlLog.status == "failed",
        ).order_by(CrawlLog.finished_at.desc()).first()

        if not last_failed:
            return self._default_retry_state()

        # 检查是否有对应的重试记录
        retry_log = db.query(CrawlLog).filter(
            CrawlLog.job_type == job_type,
            CrawlLog.status == "running",
            CrawlLog.started_at > last_failed.finished_at,
        ).first()

        if retry_log:
            # 有重试记录，说明正在重试或已重试完成
            return {
                "status": RetryState.RUNNING,
                "retry_count": 1,  # 简化处理，实际应该统计重试次数
                "next_retry": None,
                "last_error": last_failed.error_message,
                "crawl_log_id": last_failed.id,
            }

        # 检查是否在重试时间窗口内（1小时内）
        if last_failed.finished_at:
            time_since_failure = now() - last_failed.finished_at
            if time_since_failure < timedelta(hours=1):
                # 还在重试窗口内，应该安排重试
                return {
                    "status": RetryState.PENDING,
                    "retry_count": 0,
                    "next_retry": last_failed.finished_at + timedelta(hours=1),
                    "last_error": last_failed.error_message,
                    "crawl_log_id": last_failed.id,
                }

        return self._default_retry_state()

    def _default_retry_state(self) -> Dict[str, Any]:
        """返回默认的重试状态"""
        return {
            "status": RetryState.EXHAUSTED,
            "retry_count": 0,
            "next_retry": None,
            "last_error": None,
            "crawl_log_id": None,
        }

    def _update_retry_state(self, job_type: str, status: str, **kwargs):
        """更新重试状态"""
        if job_type not in self._retry_states:
            self._retry_states[job_type] = self._default_retry_state()

        state = self._retry_states[job_type]
        state["status"] = status
        state.update(kwargs)

        # 持久化到数据库
        self._save_retry_state_to_db(job_type, state)

    def _save_retry_state_to_db(self, job_type: str, state: Dict[str, Any]):
        """保存重试状态到数据库"""
        # 这里可以扩展为更复杂的持久化逻辑
        # 目前主要依赖CrawlLog表记录重试信息
        pass

    def _clear_retry_state(self, job_type: str):
        """清除重试状态（成功后调用）"""
        with self._lock:
            if job_type in self._retry_states:
                del self._retry_states[job_type]

            # 移除APScheduler任务
            job_id = f"{self._job_id_prefix}{job_type}"
            try:
                self.scheduler.remove_job(job_id)
            except Exception:
                pass


# 全局重试管理器实例
retry_manager: Optional[RetryManager] = None


def init_retry_manager(scheduler: BackgroundScheduler) -> RetryManager:
    """初始化全局重试管理器"""
    global retry_manager
    retry_manager = RetryManager(scheduler)
    return retry_manager


def get_retry_manager() -> RetryManager:
    """获取全局重试管理器实例"""
    if retry_manager is None:
        raise RuntimeError("RetryManager not initialized. Call init_retry_manager() first.")
    return retry_manager
