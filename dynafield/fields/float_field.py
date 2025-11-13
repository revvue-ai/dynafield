from typing import Any, Literal

import strawberry
from pydantic import Field
from strawberry.experimental.pydantic import type as pyd_type

from dynafield.base_model import BaseModel
from dynafield.fields.base_field import DataTypeFieldBase, FieldTypeEnum


class FloatFieldConstraints(BaseModel):
    ge_float: float | None = Field(default=None, alias="geFloat")
    le_float: float | None = Field(default=None, alias="leFloat")

    def to_gql_type(self, extra: dict[str, Any] | None = None) -> "FloatFieldConstraintsGql":
        obj = FloatFieldConstraintsGql.from_pydantic(self, extra=extra)
        return obj


class FloatField(DataTypeFieldBase):
    typename__: Literal[FieldTypeEnum.FloatField.name] = Field(default=FieldTypeEnum.FloatField.name, alias="__typename")  # type: ignore # mypy does not accept this
    default_float: float | None = Field(default=None, alias="defaultFloat")
    constraints_float: FloatFieldConstraints | None = Field(default=None, alias="constraintsFloat")

    def to_pydantic_field(self) -> tuple[str, tuple[type[float], Any]]:
        field_kwargs: dict[str, Any] = {}
        if self.constraints_float and self.constraints_float.ge_float is not None:
            field_kwargs["ge"] = self.constraints_float.ge_float
        if self.constraints_float and self.constraints_float.le_float is not None:
            field_kwargs["le"] = self.constraints_float.le_float

        return self.label, (float, self._build_field(default=self.default_float, **field_kwargs))

    def to_gql_type(self, extra: dict[str, Any] | None = None) -> "FloatFieldGql":
        obj = FloatFieldGql.from_pydantic(self, extra=extra)
        return obj


@pyd_type(model=FloatFieldConstraints, all_fields=True)
class FloatFieldConstraintsGql:
    pass


@pyd_type(model=FloatField)
class FloatFieldGql:
    id: strawberry.auto
    label: strawberry.auto
    description: strawberry.auto
    required: strawberry.auto
    default_float: strawberry.auto
    constraints_float: FloatFieldConstraintsGql
