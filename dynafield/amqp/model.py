import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Event(BaseModel):
    content: Dict[str, Any] = Field(default_factory=dict)
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    parentId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    eventTime: Optional[datetime] = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    tenantId: str
    eventType: Optional[str] = None

    class Config:
        use_enum_values = True

    def __init__(self, **data: Any) -> None:
        if "id" in data and isinstance(data["id"], str):
            data["id"] = uuid.UUID(data["id"])

        super().__init__(**data)
