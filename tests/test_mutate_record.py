from datetime import datetime

from dynafield import RecordSchemaDefinition
from dynafield.fields.base_field import build_dynamic_model
from dynafield.fields.date_field import DateTimeField
from dynafield.fields.email_field import EmailField
from dynafield.fields.enum_field import EnumField
from dynafield.fields.int_field import IntField
from dynafield.fields.list_field import ListField
from dynafield.fields.str_field import StrField
from dynafield.utils import uuid_7
from example._client import Client

client = Client(url="http://localhost:1000/graphql")
schemaId = uuid_7()

customer_fields = [
    # Fixed literals
    StrField(
        label="tag",
        default_str="booking",
        description="Constant literal indicating this is a booking super tag.",
    ),
    # Booking payload
    IntField(label="numberOfGuests"),  # optional → no default
    DateTimeField(label="date"),  # optional
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
    ),
]


def test_mutate_schema_record():
    data = RecordSchemaDefinition(id=schemaId, name="customerField", field_definitions=customer_fields)
    client.mutate_record_schema(schema_to_add=data.dump(keep_data_types=False, exclude_none=True))


def test_mutate_record():
    customerInfo = build_dynamic_model("customerInfo", customer_fields)
    data = customerInfo(
        requestType="NEW_BOOKING",
        numberOfGuests=4,
        date=datetime.now(),
        firstName="Ada",
        lastName="Lovelace",
        email="ada@example.com",
        evidence=[{"field": "date", "text": "Tomorrow 19:00"}],
    )
    client.mutate_records(record_schema_id=schemaId, records=[data.dump(keep_data_types=False, exclude_none=True)])


def test_query_records():
    client.query_records(record_schema_id=schemaId)


def test_query_schema():
    client.query_record_schema(record_schema_id=schemaId)
