from typing import Any, Literal

import strawberry
from pydantic import Field
from strawberry.experimental.pydantic import type as pyd_type

from dynafield.base_model import BaseModel
from dynafield.fields.base_field import DataTypeFieldBase, FieldTypeEnum


class StrFieldConstraints(BaseModel):
    min_length: int | None = Field(default_factory=lambda: None)
    max_length: int | None = Field(default_factory=lambda: None)

    def to_gql_type(self, extra: dict[str, Any] | None = None) -> "StrFieldConstraintsGql":
        obj = StrFieldConstraintsGql.from_pydantic(self, extra=extra)
        return obj


class StrField(DataTypeFieldBase):
    typename__: Literal[FieldTypeEnum.StrField.name] = Field(default=FieldTypeEnum.StrField.name, alias="__typename")  # type: ignore # mypy does not accept this
    default_str: str | None = Field(default=None, alias="defaultStr")
    constraints_str: StrFieldConstraints | None = Field(default=None, alias="constraintsStr")

    def to_pydantic_field(self) -> tuple[str, tuple[type[str], Any]]:
        field_kwargs: dict[str, Any] = {}
        if self.constraints_str and self.constraints_str.min_length is not None:
            field_kwargs["min_length"] = self.constraints_str.min_length
        if self.constraints_str and self.constraints_str.max_length is not None:
            field_kwargs["max_length"] = self.constraints_str.max_length

        return self.label, (str, self._build_field(default=self.default_str, **field_kwargs))

    def to_gql_type(self, extra: dict[str, Any] | None = None) -> "StrFieldGql":
        obj = StrFieldGql.from_pydantic(self, extra=extra)
        return obj


@pyd_type(model=StrFieldConstraints, all_fields=True)
class StrFieldConstraintsGql:
    pass


@pyd_type(model=StrField)
class StrFieldGql:
    id: strawberry.auto
    label: strawberry.auto
    description: strawberry.auto
    required: strawberry.auto
    default_str: strawberry.auto
    constraints_str: StrFieldConstraintsGql
