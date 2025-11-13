from enum import Enum as PyEnum
from typing import Any, Literal

import strawberry
from pydantic import Field
from strawberry.experimental.pydantic import type as pyd_type

from dynafield.fields.base_field import DataTypeFieldBase, FieldTypeEnum


class EnumField(DataTypeFieldBase):
    typename__: Literal[FieldTypeEnum.EnumField.name] = Field(default=FieldTypeEnum.EnumField.name, alias="__typename")  # type: ignore # mypy does not accept this
    allowed_values: list[str] | None = Field(default=None, alias="allowedValues")
    default_str: str | None = Field(default=None, alias="defaultStr")

    def to_pydantic_field(self) -> tuple[str, tuple[type[PyEnum], Any]]:
        if not self.allowed_values:
            raise ValueError("EnumField requires 'allowed_values' to be defined")

        enum_name: str = f"{self.label.capitalize()}Enum"

        # Build the enum from allowed values
        enum_class = PyEnum(
            enum_name,
            {val.upper(): val for val in self.allowed_values},  # type: ignore[arg-type]
        )

        # Turn default_str into an actual enum member (or leave as None)
        if self.default_str is not None:
            try:
                enum_default = enum_class(self.default_str)
            except ValueError:
                raise ValueError(f"default_str={self.default_str!r} is not in allowed_values={self.allowed_values!r}")
        else:
            enum_default = None

        # Now build the Field using the enum instance as default
        field_info = self._build_field(default=enum_default)

        return self.label, (enum_class, field_info)

    def to_gql_type(self, extra: dict[str, Any] | None = None) -> "EnumFieldGql":
        obj = EnumFieldGql.from_pydantic(self, extra=extra)
        return obj


@pyd_type(model=EnumField)
class EnumFieldGql:
    id: strawberry.auto
    label: strawberry.auto
    description: strawberry.auto
    required: strawberry.auto
    default_str: strawberry.auto
    allowed_values: strawberry.auto
