"""Utilities describing record schemas and runtime interactions with them."""

from __future__ import annotations

from typing import Annotated, Any, Iterable, MutableMapping, Union
from uuid import UUID

import strawberry
from pydantic import Field

from dynafield import build_dynamic_model
from dynafield.base_model import BaseModel
from dynafield.fields.bool_field import BoolField, BoolFieldGql
from dynafield.fields.date_field import (
    DateField,
    DateFieldGql,
    DateTimeField,
    DateTimeFieldGql,
)
from dynafield.fields.email_field import EmailField, EmailFieldGql
from dynafield.fields.enum_field import EnumField, EnumFieldGql
from dynafield.fields.float_field import FloatField, FloatFieldGql
from dynafield.fields.int_field import IntField, IntFieldGql
from dynafield.fields.json_field import JsonField, JsonFieldGql
from dynafield.fields.list_field import ListField, ListFieldGql
from dynafield.fields.object_field import ObjectField, ObjectFieldGql
from dynafield.fields.str_field import StrField, StrFieldGql
from dynafield.fields.uuid_field import UuidField, UuidFieldGql
from dynafield.utils import uuid_7

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


class RecordSchemaDefinition(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid_7())
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
