"""Utilities describing record schemas and runtime interactions with them."""

from __future__ import annotations

from typing import Annotated, Iterable, MutableMapping, Union
from uuid import UUID

from pydantic import Field

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
from dynafield.from_func import build_dynamic_model
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
    """Definition describing how to build a record for a specific table."""

    schema_id: UUID = Field(default_factory=lambda: uuid_7())
    tenant_id: str
    table_name: str
    record_name: str
    description: str | None = None
    field_definitions: list[TypeFieldsUnion]

    def build_record_model(self) -> type[BaseModel]:
        """Return a Pydantic model representing this record schema."""

        return build_dynamic_model(self.record_name, self.field_definitions)

    # ------------------------------------------------------------------
    # Backwards compatibility helpers
    # ------------------------------------------------------------------
    @property
    def id(self) -> UUID:  # pragma: no cover - compatibility shim
        return self.schema_id

    @property
    def name(self) -> str:  # pragma: no cover - compatibility shim
        return self.record_name

    @property
    def field_schema(self) -> list[TypeFieldsUnion]:  # pragma: no cover
        return self.field_definitions

    def to_pydantic(self) -> type[BaseModel]:  # pragma: no cover - legacy name
        return self.build_record_model()


class RecordSchemaRegistry:
    """In-memory registry for record schemas and typed record mutations."""

    def __init__(self, schemas: Iterable[RecordSchemaDefinition] | None = None):
        self._schemas_by_id: MutableMapping[UUID, RecordSchemaDefinition] = {}
        self._schemas_by_table: MutableMapping[str, dict[UUID, RecordSchemaDefinition]] = {}
        if schemas:
            for schema in schemas:
                self.register(schema)

    # ------------------------------------------------------------------
    # Registration & lookup
    # ------------------------------------------------------------------
    def register(self, schema: RecordSchemaDefinition) -> None:
        self._schemas_by_id[schema.schema_id] = schema
        self._schemas_by_table.setdefault(schema.table_name, {})[schema.schema_id] = schema

    def get(self, schema_id: UUID) -> RecordSchemaDefinition:
        return self._schemas_by_id[schema_id]

    def get_for_table(self, table_name: str, schema_id: UUID) -> RecordSchemaDefinition:
        return self._schemas_by_table[table_name][schema_id]

    # ------------------------------------------------------------------
    # Building & mutating records
    # ------------------------------------------------------------------
    def build_model(self, schema_id: UUID) -> type[BaseModel]:
        return self.get(schema_id).build_record_model()

    def build_records(
        self, schema_id: UUID, stored_records: Iterable[dict]
    ) -> list[BaseModel]:
        model_cls = self.build_model(schema_id)
        return [model_cls(**record) for record in stored_records]

    def mutate_records(
        self,
        schema_id: UUID,
        stored_records: list[dict],
        updates: list[dict],
    ) -> list[BaseModel]:
        """Apply partial updates to stored records using the schema definition."""

        model_cls = self.build_model(schema_id)
        typed_records: list[BaseModel] = []

        for index, record in enumerate(stored_records):
            merged = record.copy()
            if index < len(updates):
                merged |= updates[index]
            typed_records.append(model_cls(**merged))

        # Additional updates beyond existing records represent new entries
        for patch in updates[len(stored_records) :]:
            typed_records.append(model_cls(**patch))

        return typed_records


# Backwards compatible alias -------------------------------------------------
DynamicModelDocument = RecordSchemaDefinition
