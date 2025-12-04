"""Utilities describing record schemas and runtime interactions with them."""

from __future__ import annotations

import typing as t
import uuid
from enum import Enum as PyEnum
from typing import Annotated, Any, Iterable, MutableMapping, Union
from uuid import UUID

import strawberry
from pydantic import Field
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from .base_model import BaseModel
from .fields.base_field import build_dynamic_model
from .fields.bool_field import BoolField, BoolFieldGql
from .fields.date_field import (
    DateField,
    DateFieldGql,
    DateTimeField,
    DateTimeFieldGql,
)
from .fields.email_field import EmailField, EmailFieldGql
from .fields.enum_field import EnumField, EnumFieldGql
from .fields.float_field import FloatField, FloatFieldConstraints, FloatFieldGql
from .fields.int_field import IntField, IntFieldGql
from .fields.json_field import JsonField, JsonFieldGql
from .fields.list_field import ListField, ListFieldGql
from .fields.object_field import ObjectField, ObjectFieldGql
from .fields.str_field import StrField, StrFieldConstraints, StrFieldGql
from .fields.uuid_field import UuidField, UuidFieldGql
from .from_func import build_model_from_function
from .utils.uuid import uuid_7

TypeFieldsUnionGql = (
    BoolFieldGql
    | DateFieldGql
    | DateTimeFieldGql
    | EmailFieldGql
    | EnumFieldGql
    | FloatFieldGql
    | IntFieldGql
    | JsonFieldGql
    | ListFieldGql
    | StrFieldGql
    | UuidFieldGql
    | ObjectFieldGql
)
TypeFieldsUnion = Annotated[
    Union[
        BoolField,
        DateField,
        DateTimeField,
        EmailField,
        EnumField,
        FloatField,
        IntField,
        JsonField,
        ListField,
        StrField,
        UuidField,
        ObjectField,
    ],
    Field(discriminator="typename__"),
]


def _get_default(info: FieldInfo):
    """Return a usable default value (None if undefined)."""
    if info.default is not PydanticUndefined:
        return info.default
    if info.default_factory is not None:
        return info.default_factory()
    return None


def pydantic_field_to_dyn_field(name: str, info: FieldInfo) -> TypeFieldsUnion:
    """
    Convert a single Pydantic FieldInfo to one of:
    BoolField, FloatField, StrField, EnumField, ...

    Extend this with more types as needed.
    """
    ann = info.annotation
    default = _get_default(info)

    # -------------------
    # Bool -> BoolField
    # -------------------
    if ann is bool:
        return BoolField(
            label=name,
            default_bool=default,
        )

    # -------------------
    # Float -> FloatField (+ constraints)
    # -------------------
    if ann is float:
        ge = getattr(info, "ge", None)
        le = getattr(info, "le", None)

        constraints = None
        if ge is not None or le is not None:
            constraints = FloatFieldConstraints(
                ge_float=ge,
                le_float=le,
            )

        return FloatField(
            label=name,
            default_float=default,
            constraints_float=constraints,
        )

    # -------------------
    # Str -> StrField (+ constraints)
    # -------------------
    if ann is str:
        min_length = getattr(info, "min_length", None)
        max_length = getattr(info, "max_length", None)

        constraints = None
        if min_length is not None or max_length is not None:
            constraints = StrFieldConstraints(
                min_length=min_length,
                max_length=max_length,
            )

        return StrField(
            label=name,
            default_str=default,
            constraints_str=constraints,
        )

    # -------------------
    # Enum -> EnumField
    # -------------------
    if isinstance(ann, type) and issubclass(ann, PyEnum):
        # allowed_values are the enum values
        allowed_values = [member.value for member in ann]

        if isinstance(default, PyEnum):
            default_str = default.value
        else:
            default_str = None

        return EnumField(
            label=name,
            allowed_values=allowed_values,
            default_str=default_str,
        )

    # -------------------
    # Fallback: str / json / whatever you want
    # -------------------
    # For now, we can default to StrField with no constraints.
    # You can swap this to JsonField or raise an error.
    return StrField(
        label=name,
        default_str=str(default) if default is not None else None,
    )


class RecordSchemaDefinition(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid_7())
    ref: str | None = None  # Unique record name
    name: str = "record name"
    description: str | None = None
    field_definitions: list[TypeFieldsUnion] | None = Field(None, alias="fieldDefinitions")

    def build_record_model(self) -> type[BaseModel]:
        if not self.field_definitions:
            raise ValueError("No field definitions defined")
        return build_dynamic_model(self.name, self.field_definitions)

    def get_pydantic_model(self) -> type[BaseModel]:  # pragma: no cover - legacy name
        return self.build_record_model()

    def to_gql_type(self, extra: dict[str, Any] | None = None) -> "RecordSchemaDefinitionGql":
        obj = RecordSchemaDefinitionGql(
            id=self.id,
            name=self.name,
            description=self.description,
            field_definitions=[v.to_gql_type() for v in self.field_definitions] if self.field_definitions else None,
        )
        return obj

    def from_func(
        func: t.Callable[..., t.Any],
        *,
        name: str | None = None,
        description: str | None = None,
        exclude: t.Iterable[str] | None = None,
        overrides: dict[str, dict[str, t.Any]] | None = None,
    ) -> RecordSchemaDefinition:
        model = build_model_from_function(my_func)
        exclude = exclude or set()

        dyn_fields: list[TypeFieldsUnion] = []

        for field_name, field_info in model.model_fields.items():
            if field_name in exclude:
                continue
            # you can also skip internal fields here if needed (e.g. if field_name startswith "_")

            dyn_field = pydantic_field_to_dyn_field(field_name, field_info)
            dyn_fields.append(dyn_field)

        return RecordSchemaDefinition(
            name=name or model.__name__,
            description=description,
            field_definitions=dyn_fields,
        )


@strawberry.type
class RecordSchemaDefinitionGql:
    id: UUID
    name: str
    description: str | None
    field_definitions: list[TypeFieldsUnionGql] | None


class RecordSchemaRegistry:
    def __init__(self, schemas: Iterable[RecordSchemaDefinition] | None = None):
        self._schemas_by_id: MutableMapping[UUID, RecordSchemaDefinition] = {}
        if schemas:
            for schema in schemas:
                self.register(schema)

    def register(self, schema: RecordSchemaDefinition) -> None:
        self._schemas_by_id[schema.id] = schema

    def get(self, schema_id: UUID) -> RecordSchemaDefinition:
        return self._schemas_by_id[schema_id]

    def build_model(self, schema_id: UUID) -> type[BaseModel]:
        return self.get(schema_id).build_record_model()

    def build_records(self, schema_id: UUID, stored_records: Iterable[dict[str, Any]]) -> list[BaseModel]:
        model_cls = self.build_model(schema_id)
        return [model_cls(**record) for record in stored_records]

    def mutate_records(
        self,
        schema_id: UUID,
        stored_records: list[dict[str, Any]],
        updates: list[dict[str, Any]],
    ) -> list[BaseModel]:
        model_cls = self.build_model(schema_id)
        typed_records: list[BaseModel] = []

        for index, record in enumerate(stored_records):
            merged = record.copy()
            if index < len(updates):
                merged |= updates[index]
            typed_records.append(model_cls(**merged))

        for patch in updates[len(stored_records) :]:
            typed_records.append(model_cls(**patch))

        return typed_records


if __name__ == "__main__":

    def my_func(
        name: str,
        age: int,
        email: str | None = None,
        internal_id: uuid.UUID | None = None,
    ) -> None: ...

    schema = RecordSchemaDefinition.from_func(
        my_func,
        exclude=["internal_id"],
    )
