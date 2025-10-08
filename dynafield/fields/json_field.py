from copy import deepcopy
from typing import Any, Literal

import strawberry
from pydantic import Field
from strawberry.experimental.pydantic import type as pyd_type
from strawberry.scalars import JSON

from dynafield.fields.base_field import DataTypeFieldBase, FieldTypeEnum


class JsonField(DataTypeFieldBase):
    typename__: Literal[FieldTypeEnum.JsonField] = Field(default=FieldTypeEnum.JsonField, alias="__typename")
    default_dict: dict[str, Any] | None = Field(default=None, alias="defaultDict")

    def to_pydantic_field(self) -> tuple[str, tuple[type[dict[str, Any]], Any]]:
        if self.default_dict is not None:

            def default_factory(value: dict[str, Any] | None = self.default_dict) -> dict[str, Any] | None:
                return deepcopy(value) if value is not None else None

            return self.label, (dict[str, Any], self._build_field(default_factory=default_factory))

        return self.label, (dict[str, Any], self._build_field(default=None))

    def to_gql_type(self, extra: dict[str, Any] | None = None) -> "JsonFieldGql":
        obj = JsonFieldGql.from_pydantic(self, extra=extra)
        return obj


@pyd_type(model=JsonField)
class JsonFieldGql:
    id: strawberry.auto
    label: strawberry.auto
    description: strawberry.auto
    required: strawberry.auto
    default_dict: JSON
