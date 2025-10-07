from dynafield.fields.int_field import IntField
from dynafield.fields.str_field import StrField
from dynafield.record_schema import RecordSchemaDefinition, RecordSchemaRegistry


def _build_sample_schema() -> RecordSchemaDefinition:
    return RecordSchemaDefinition(
        name="BookingRecord",
        description="Schema for booking records",
        field_definitions=[
            StrField(label="customer_name"),
            IntField(label="party_size"),
        ],
    )


def test_build_and_fetch_records_from_registry():
    schema = _build_sample_schema()
    registry = RecordSchemaRegistry([schema])

    stored_records = [
        {"customer_name": "Ada", "party_size": 4},
        {"customer_name": "Bob", "party_size": 2},
    ]

    typed_records = registry.build_records(schema.id, stored_records)

    assert len(typed_records) == 2
    assert typed_records[0].customer_name == "Ada"
    assert typed_records[1].party_size == 2

    fetched_schema = registry.get(schema.id)
    assert fetched_schema is schema


def test_mutate_records_with_registry():
    schema = _build_sample_schema()
    registry = RecordSchemaRegistry([schema])

    stored_records = [
        {"customer_name": "Ada", "party_size": 4},
        {"customer_name": "Bob", "party_size": 2},
    ]
    updates = [
        {"customer_name": "Ada Lovelace"},
        {"party_size": 3},
        {"customer_name": "Charlie", "party_size": 6},
    ]

    mutated_records = registry.mutate_records(schema.id, stored_records, updates)

    assert len(mutated_records) == 3
    assert mutated_records[0].customer_name == "Ada Lovelace"
    assert mutated_records[0].party_size == 4
    assert mutated_records[1].customer_name == "Bob"
    assert mutated_records[1].party_size == 3
    assert mutated_records[2].customer_name == "Charlie"
    assert mutated_records[2].party_size == 6
