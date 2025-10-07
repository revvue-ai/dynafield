from typing import Annotated, Union

from pydantic import Field

from dynafield.fields.base_field import DataTypeFieldBase, FieldTypeEnum
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
from dynafield.from_func import build_dynamic_model, build_model_from_function, fields_from_function

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
        "BoolField",
        "DateField",
        "DateTimeField",
        "EmailField",
        "EnumField",
        "FloatField",
        "IntField",
        "JsonField",
        "ListField",
        "StrField",
        "UuidField",
        "ObjectField",
    ],
    Field(discriminator="typename__"),
]

__all__ = [
    "build_model_from_function",
    "fields_from_function",
    "build_dynamic_model",
    "FieldTypeEnum",
    "DataTypeFieldBase",
    "BoolField",
    "DateField",
    "DateTimeField",
    "EmailField",
    "EnumField",
    "FloatField",
    "IntField",
    "JsonField",
    "ListField",
    "StrField",
    "UuidField",
    "ObjectField",
]
