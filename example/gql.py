import strawberry
from strawberry import Info
from strawberry.scalars import JSON

from dynafield import TypeFieldsUnion, TypeFieldsUnionGql
from dynafield.base_model import BaseModel

db_local_store = {}


class ParseField(BaseModel):
    fields: list[TypeFieldsUnion]


@strawberry.type
class TypeFieldsDefinedGql:
    fields: list[TypeFieldsUnionGql]
    count: int


async def query_typed_fields(info: Info) -> TypeFieldsDefinedGql:
    data: list[TypeFieldsUnion] = db_local_store.get("fields")
    fields = [d.to_gql_type() for d in data] if data else []
    return TypeFieldsDefinedGql(fields=fields, count=len(fields))


async def mutate_typed_fields(info: Info, fields_to_add: JSON) -> TypeFieldsDefinedGql:
    parsed = ParseField(fields=fields_to_add)
    db_local_store["fields"] = parsed.fields
    fields = [d.to_gql_type() for d in parsed] if parsed else []
    return TypeFieldsDefinedGql(fields=fields, count=len(fields))


@strawberry.type
class Query:
    typed_fields: TypeFieldsDefinedGql = strawberry.field(resolver=query_typed_fields)


@strawberry.type
class Mutation:
    typed_fields: TypeFieldsDefinedGql = strawberry.mutation(resolver=mutate_typed_fields)


Schema = strawberry.Schema(query=Query, mutation=Mutation)
