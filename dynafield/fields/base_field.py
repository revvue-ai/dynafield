import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any, Callable, Sequence

from pydantic import EmailStr, Field, create_model

from dynafield.base_model import BaseModel
from dynafield.utils import uuid_7


class FieldTypeEnum(str, Enum):
    UuidField = "UuidField"
    StrField = "StringField"
    EmailField = "EmailField"
    IntField = "IntField"
    FloatField = "FloatField"
    BoolField = "BooleanField"
    DateField = "DateField"
    DateTimeField = "DateTimeField"
    JsonField = "JsonField"
    ListField = "ListField"
    EnumField = "EnumField"

    def to_py_type(self) -> Any:
        type_mapping = {
            FieldTypeEnum.UuidField: uuid.UUID,
            FieldTypeEnum.StrField: str,
            FieldTypeEnum.EmailField: EmailStr,
            FieldTypeEnum.IntField: int,
            FieldTypeEnum.FloatField: float,
            FieldTypeEnum.BoolField: bool,
            FieldTypeEnum.DateField: date,
            FieldTypeEnum.DateTimeField: datetime,
            FieldTypeEnum.JsonField: dict[str, Any],
            FieldTypeEnum.ListField: list[Any],
        }
        return type_mapping[self]


_MISSING = object()


class DataTypeFieldBase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid_7()))
    label: str
    description: str | None = None
    required: bool = False

    def _build_field(
        self,
        *,
        default: Any = _MISSING,
        default_factory: Callable[[], Any] | None = None,
        **field_kwargs: Any,
    ) -> Field:
        """Create a ``pydantic.Field`` honouring ``required`` and mutable defaults."""

        if self.description:
            field_kwargs.setdefault("description", self.description)

        if self.required:
            if default not in (_MISSING, None):
                raise ValueError(f"Required field '{self.label}' cannot specify a default value.")
            if default_factory is not None:
                raise ValueError(f"Required field '{self.label}' cannot define a default factory.")
            return Field(default=..., **field_kwargs)

        if default_factory is not None:
            return Field(default_factory=default_factory, **field_kwargs)

        if default is _MISSING:
            return Field(**field_kwargs)

        return Field(default=default, **field_kwargs)


def build_dynamic_model(name: str, fields: Sequence[DataTypeFieldBase]) -> type[BaseModel]:
    field_defs: dict[str, Any] = {}

    for field in fields:
        if hasattr(field, "to_pydantic_field"):
            key, (typ, field_def) = field.to_pydantic_field()
            field_defs[key] = (typ, field_def)

    return create_model(name, **field_defs)
