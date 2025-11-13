from typing import Any, Literal

import strawberry
from pydantic import Field
from strawberry.experimental.pydantic import type as pyd_type
from strawberry.scalars import JSON

from dynafield.base_model import BaseModel
from dynafield.fields.base_field import DataTypeFieldBase, FieldTypeEnum, build_dynamic_model


class ObjectField(DataTypeFieldBase):
    typename__: Literal[FieldTypeEnum.ObjectField.name] = Field(default=FieldTypeEnum.ObjectField.name, alias="__typename")  # type: ignore # mypy does not accept this
    fields: list[DataTypeFieldBase]

    def to_pydantic_field(self) -> tuple[str, tuple[type[BaseModel], Any]]:
        nested_model = build_dynamic_model(f"{self.label.title()}SubModel", self.fields)
        return self.label, (nested_model, self._build_field(default=None))

    def to_gql_type(self, extra: dict[str, Any] | None = None) -> "ObjectFieldGql":
        obj = ObjectFieldGql.from_pydantic(self, extra=extra)
        return obj


@pyd_type(model=ObjectField)
class ObjectFieldGql:
    id: strawberry.auto
    label: strawberry.auto
    description: strawberry.auto
    required: strawberry.auto
    fields: JSON
