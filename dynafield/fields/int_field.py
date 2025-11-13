from typing import Any, Literal

import strawberry
from pydantic import Field
from strawberry.experimental.pydantic import type as pyd_type

from dynafield.base_model import BaseModel
from dynafield.fields.base_field import DataTypeFieldBase, FieldTypeEnum


class IntFieldConstraints(BaseModel):
    ge_int: int | None = Field(default=None, alias="geInt")
    le_int: int | None = Field(default=None, alias="leInt")

    def to_gql_type(self, extra: dict[str, Any] | None = None) -> "IntFieldConstraintsGql":
        obj = IntFieldConstraintsGql.from_pydantic(self, extra=extra)
        return obj


class IntField(DataTypeFieldBase):
    typename__: Literal[FieldTypeEnum.IntField.name] = Field(default=FieldTypeEnum.IntField.name, alias="__typename")  # type: ignore # mypy does not accept this
    default_int: int | None = Field(default=None, alias="defaultInt")
    constraints_int: IntFieldConstraints | None = Field(default=None, alias="constraintsInt")

    def to_pydantic_field(self) -> tuple[str, tuple[type[int], Any]]:
        field_kwargs: dict[str, Any] = {}
        if self.constraints_int and self.constraints_int.ge_int is not None:
            field_kwargs["ge"] = self.constraints_int.ge_int
        if self.constraints_int and self.constraints_int.le_int is not None:
            field_kwargs["le"] = self.constraints_int.le_int

        return self.label, (int, self._build_field(default=self.default_int, **field_kwargs))

    def to_gql_type(self, extra: dict[str, Any] | None = None) -> "IntFieldGql":
        obj = IntFieldGql.from_pydantic(self, extra=extra)
        return obj


@pyd_type(model=IntFieldConstraints, all_fields=True)
class IntFieldConstraintsGql:
    pass


@pyd_type(model=IntField)
class IntFieldGql:
    id: strawberry.auto
    label: strawberry.auto
    description: strawberry.auto
    required: strawberry.auto
    default_int: strawberry.auto
    constraints_int: IntFieldConstraintsGql
