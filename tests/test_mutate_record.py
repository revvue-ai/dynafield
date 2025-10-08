from datetime import datetime
from typing import Any, AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport
from strawberry.fastapi import GraphQLRouter

from dynafield import RecordSchemaDefinition
from dynafield.base_model import CustomJSONResponse
from dynafield.fields.base_field import build_dynamic_model
from dynafield.fields.date_field import DateTimeField
from dynafield.fields.email_field import EmailField
from dynafield.fields.enum_field import EnumField
from dynafield.fields.int_field import IntField
from dynafield.fields.list_field import ListField
from dynafield.fields.str_field import StrField
from dynafield.utils import uuid_7
from example import gql
from example._client import Client
from example.gql import Schema

customer_fields = [
    StrField(
        label="tag",
        default_str="booking",
        description="Constant literal indicating this is a booking super tag.",
    ),
    IntField(label="numberOfGuests"),
    DateTimeField(label="date"),
    StrField(label="firstName"),
    StrField(label="lastName"),
    EmailField(label="email"),
    StrField(label="phone"),
    StrField(label="specialRequest"),
    EnumField(
        label="requestType",
        allowed_values=[
            "NEW_BOOKING",
            "CHANGE_GUESTS_NUMBER",
            "CHANGE_DATE_TIME",
            "ADD_SPECIAL_REQUEST",
            "OTHER_UPDATE",
            "CANCEL_BOOKING",
        ],
        description="Type of booking request.",
    ),
    StrField(label="bookingId"),
    ListField(
        label="evidence",
        description="Items explaining why each field was set; text must be a 1:1 copy from the analyzed content.",
        default_list=[],
    ),
]


def _schema_payload(schema_definition: RecordSchemaDefinition) -> dict:
    payload = schema_definition.dump(keep_data_types=False, exclude_none=True)
    field_definitions = payload.get("field_definitions", [])
    if field_definitions and schema_definition.field_definitions:
        for field_payload, field in zip(field_definitions, schema_definition.field_definitions, strict=True):
            field_payload["__typename"] = getattr(field.typename__, "value", field.typename__)
    return payload


@pytest.fixture(autouse=True)
def reset_in_memory_db() -> None:
    gql.db_record_schema.clear()
    gql.db_records.clear()
    yield
    gql.db_record_schema.clear()
    gql.db_records.clear()


@pytest_asyncio.fixture()
async def graphql_client() -> AsyncGenerator[Client, Any]:
    fastapi_app = FastAPI(default_response_class=CustomJSONResponse)
    fastapi_app.include_router(
        GraphQLRouter(Schema, default_response_class=CustomJSONResponse),
        prefix="/graphql",
    )
    transport = ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield Client(url="http://testserver/graphql", http_client=async_client)


@pytest.mark.asyncio
async def test_mutate_schema_and_fetch_schema(graphql_client: Client):
    schema_id = uuid_7()
    schema_definition = RecordSchemaDefinition(
        id=schema_id,
        name="customerField",
        field_definitions=customer_fields,
    )

    mutation_result = await graphql_client.mutate_record_schema(schema_to_add=_schema_payload(schema_definition))

    assert mutation_result.record_schema.count == 1
    created_schema = mutation_result.record_schema.schemas[0]
    assert str(created_schema.id) == str(schema_id)
    assert created_schema.name == "customerField"
    assert created_schema.field_definitions is not None
    created_labels = [field.label for field in created_schema.field_definitions]
    expected_labels = [field.label for field in customer_fields]
    assert created_labels == expected_labels

    query_result = await graphql_client.query_record_schema(record_schema_id=schema_id)

    assert query_result.record_schema.count == 1
    fetched_schema = query_result.record_schema.schemas[0]
    assert str(fetched_schema.id) == str(schema_id)
    fetched_labels = [field.label for field in fetched_schema.field_definitions] if fetched_schema.field_definitions else []
    assert fetched_labels == expected_labels


@pytest.mark.asyncio
async def test_mutate_records_and_fetch_records(graphql_client: Client):
    schema_id = uuid_7()
    schema_definition = RecordSchemaDefinition(
        id=schema_id,
        name="customerField",
        field_definitions=customer_fields,
    )
    await graphql_client.mutate_record_schema(schema_to_add=_schema_payload(schema_definition))

    customer_model = build_dynamic_model("customerInfo", customer_fields)
    record = customer_model(
        requestType="NEW_BOOKING",
        numberOfGuests=4,
        date=datetime(2024, 4, 1, 19, 0, 0),
        firstName="Ada",
        lastName="Lovelace",
        email="ada@example.com",
        phone="555-0100",
        specialRequest="Window seat",
        bookingId="BK-42",
        evidence=[{"field": "date", "text": "Tomorrow 19:00"}],
    )

    mutate_result = await graphql_client.mutate_records(
        record_schema_id=schema_id,
        records=[record.model_dump(mode="json", exclude_none=True)],
    )

    assert mutate_result.records.count == 1
    stored_records = mutate_result.records.records
    assert isinstance(stored_records, list)
    assert stored_records[0]["firstName"] == "Ada"
    assert stored_records[0]["requestType"] == "NEW_BOOKING"

    query_result = await graphql_client.query_records(record_schema_id=schema_id)

    assert query_result.records.count == 1
    fetched_batches = query_result.records.records
    assert isinstance(fetched_batches, list)
    assert len(fetched_batches) == 1
    fetched_records = fetched_batches[0]
    assert isinstance(fetched_records, list)
    assert fetched_records[0]["bookingId"] == "BK-42"
    assert fetched_records[0]["numberOfGuests"] == 4
