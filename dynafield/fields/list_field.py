from copy import deepcopy
from typing import Any, Literal

import strawberry
from pydantic import Field
from strawberry.experimental.pydantic import type as pyd_type
from strawberry.scalars import JSON

from dynafield.fields.base_field import DataTypeFieldBase, FieldTypeEnum


class ListField(DataTypeFieldBase):
    typename__: Literal[FieldTypeEnum.ListField] = Field(default=FieldTypeEnum.ListField, alias="__typename")
    default_list: list[Any] | None = Field(default=None, alias="defaultList")

    def to_pydantic_field(self) -> tuple[str, tuple[type[list[Any]], Any]]:
        if self.default_list is not None:

            def default_factory(value: list[Any] | None = self.default_list) -> dict[str, Any]:
                return deepcopy(value)

            return self.label, (list[Any], self._build_field(default_factory=default_factory))

        return self.label, (list[Any], self._build_field(default=None))

    def to_gql_type(self, extra: dict[str, Any] | None = None) -> "ListFieldGql":
        obj = ListFieldGql.from_pydantic(self, extra=extra)
        return obj


@pyd_type(model=ListField)
class ListFieldGql:
    id: strawberry.auto
    label: strawberry.auto
    description: strawberry.auto
    required: strawberry.auto
    default_list: JSON
