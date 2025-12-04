from collections import defaultdict
from typing import Any
from uuid import UUID

import strawberry
from strawberry import Info
from strawberry.scalars import JSON

from dynafield.base_model import BaseModel
from dynafield.record_schema import RecordSchemaDefinition, RecordSchemaDefinitionGql, TypeFieldsUnion

db_record_schema: dict[UUID, RecordSchemaDefinition] = {}
db_records: dict[UUID, list[dict[str, Any]]] = defaultdict(list)


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


async def query_record_schema(info: Info, record_schema_id: UUID | None = None) -> RecordSchemas:
    data: list[RecordSchemaDefinition] = [db_record_schema[record_schema_id]] if record_schema_id else list(db_record_schema.values())
    schemas = [d.to_gql_type() for d in data] if data else []
    return RecordSchemas(schemas=schemas, count=len(schemas))


async def query_records(info: Info, record_schema_id: UUID | None = None) -> Records:
    if record_schema_id:
        values = db_records[record_schema_id]
    else:
        values = [v for items in list(db_records.values()) for v in items]
    return Records(records=values, count=len(values))


async def mutate_record_schema(info: Info, schema_to_add: JSON) -> RecordSchemas:
    schema = RecordSchemaDefinition(**schema_to_add)
    db_record_schema[schema.id] = schema
    return RecordSchemas(schemas=[schema.to_gql_type()], count=1)


async def mutate_records(info: Info, record_schema_id: UUID, records: JSON) -> Records:
    schema = db_record_schema[record_schema_id]
    model = schema.get_pydantic_model()
    values = []
    serialized_values: list[dict[str, Any]] = []
    for record in records:
        model_instance = model(**record)
        values.append(model_instance)
        serialized_values.append(model_instance.model_dump(mode="json", exclude_none=True))

    db_records[record_schema_id].extend(serialized_values)

    return Records(records=serialized_values, count=len(serialized_values))


@strawberry.type
class Query:
    record_schema: RecordSchemas = strawberry.field(resolver=query_record_schema)
    records: Records = strawberry.field(resolver=query_records)


@strawberry.type
class Mutation:
    record_schema: RecordSchemas = strawberry.mutation(resolver=mutate_record_schema)
    records: Records = strawberry.mutation(resolver=mutate_records)


Schema = strawberry.Schema(query=Query, mutation=Mutation)
