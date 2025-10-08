import uuid
from typing import Any, Literal

import strawberry
from pydantic import Field
from strawberry.experimental.pydantic import type as pyd_type

from dynafield.fields.base_field import DataTypeFieldBase, FieldTypeEnum


class UuidField(DataTypeFieldBase):
    typename__: Literal[FieldTypeEnum.UuidField] = Field(default=FieldTypeEnum.UuidField, alias="__typename")
    default_uuid: uuid.UUID | None = None

    def to_pydantic_field(self) -> tuple[str, tuple[type[uuid.UUID], Any]]:
        return self.label, (uuid.UUID, self._build_field(default=self.default_uuid))

    def to_gql_type(self, extra: dict[str, Any] | None = None) -> "UuidFieldGql":
        obj = UuidFieldGql.from_pydantic(self, extra=extra)
        return obj


@pyd_type(model=UuidField)
class UuidFieldGql:
    id: strawberry.auto
    label: strawberry.auto
    description: strawberry.auto
    required: strawberry.auto
    default_uuid: strawberry.auto
