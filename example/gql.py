from collections import defaultdict
from uuid import UUID

import strawberry
from strawberry import Info
from strawberry.scalars import JSON

from dynafield import TypeFieldsUnion
from dynafield.base_model import BaseModel
from dynafield.record_schema import RecordSchemaDefinition, RecordSchemaDefinitionGql

db_record_schema: dict[UUID, RecordSchemaDefinition] = {}
db_records = defaultdict(list)


class ParseField(BaseModel):
    fields: list[TypeFieldsUnion]


@strawberry.type
class RecordSchemas:
    schemas: list[RecordSchemaDefinitionGql]
    count: int


@strawberry.type
class Records:
    records: JSON
    count: int


async def query_record_schema(info: Info, record_schema_id: UUID) -> RecordSchemas:
    data: list[RecordSchemaDefinition] = [db_record_schema[record_schema_id]] if record_schema_id else list(db_record_schema.values())
    schemas = [d.to_gql_type() for d in data] if data else []
    return RecordSchemas(schemas=schemas, count=len(schemas))


async def query_records(info: Info, record_schema_id: UUID) -> Records:
    values = db_records[record_schema_id]
    return Records(records=values, count=len(values))


async def mutate_record_schema(info: Info, schema_to_add: JSON) -> RecordSchemas:
    schema = RecordSchemaDefinition(**schema_to_add)
    db_record_schema[schema.id] = schema
    return RecordSchemas(schemas=[schema.to_gql_type()], count=1)


async def mutate_records(info: Info, record_schema_id: UUID, records: JSON) -> Records:
    schema = db_record_schema[record_schema_id]
    model = schema.get_pydantic_model()
    values = []
    for record in records:
        values.append(model(**record))

    db_records[record_schema_id].append(values)

    return Records(records=values, count=len(values))


@strawberry.type
class Query:
    record_schema: RecordSchemas = strawberry.field(resolver=query_record_schema)
    records: Records = strawberry.field(resolver=query_records)


@strawberry.type
class Mutation:
    record_schema: RecordSchemas = strawberry.mutation(resolver=mutate_record_schema)
    records: Records = strawberry.mutation(resolver=mutate_records)


Schema = strawberry.Schema(query=Query, mutation=Mutation)
