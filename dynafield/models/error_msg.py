from datetime import datetime
from typing import Any, Dict

from ..gql.custom_base_model import GqlBase


class ErrorMessage(GqlBase):
    message_id: str | None = None
    service_name: str | None = None
    body: Dict[str, Any] | None = None
    routing_key: str | None = None
    exchange: str | None = None
    headers: Dict[str, Any] | None = None
    timestamp: datetime | None = None
    redelivered: bool | None = None
    message_index: int | None = None
    tenant_id: str | None = None
    payload: Dict[str, Any] | None = None
    metadata: Dict[str, Any] | None = None


ErrorMessageGql = ErrorMessage.get_strawberry_class()
