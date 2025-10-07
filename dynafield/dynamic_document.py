from typing import Annotated, Union
from uuid import UUID

from pydantic import Field

from dynafield.base_model import BaseModel
from dynafield.fields.bool_field import BoolField, BoolFieldGql
from dynafield.fields.date_field import DateField, DateFieldGql, DateTimeField, DateTimeFieldGql
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


class DynamicModelDocument(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid_7())
    tenant_id: str
    user_id: str
    name: str
    description: str
    field_schema: list[TypeFieldsUnion]

    def to_pydantic(self) -> type[BaseModel]:
        return build_dynamic_model(self.name, self.field_schema)
