from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_serializer

from app.utils import BEIJING_TZ


class BeijingBaseModel(BaseModel):
    """Base model that ensures all datetime outputs include Beijing timezone."""

    model_config = {"from_attributes": True}

    @field_serializer("*")
    @classmethod
    def _beijing_datetime(cls, v: Any) -> Any:
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=BEIJING_TZ)
            return v
        return v
