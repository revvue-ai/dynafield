# dynafield

Dynamic data structures for rapidly evolving applications.

> [!IMPORTANT]
> **Project status:** dynafield is under active development. Public APIs and behaviors may change without notice and should be considered unstable.

## Overview

dynafield helps you describe, generate, and consume rich data schemas at runtime. By composing declarative field definitions you can build fully-typed [Pydantic](https://docs.pydantic.dev/latest/) models, expose them via [Strawberry GraphQL](https://strawberry.rocks/), and orchestrate runtime records without hand-writing large numbers of boilerplate classes.

The project powers internal tooling at [Revvue](https://revvue.ai) and is now open-source so other teams can benefit from the same dynamic schema capabilities.

## Key features

- **Dynamic model generation** – Produce Pydantic `BaseModel` subclasses on the fly from field definitions or existing functions.
- **Comprehensive field library** – Strings, numbers, UUIDs, JSON blobs, nested objects, lists, enumerations, and more – each with validation and default handling baked in.
- **GraphQL-ready schema types** – Convert record schemas into Strawberry GraphQL types so runtime structures can be queried just like static models.
- **Registry and record utilities** – Register multiple schemas, build typed instances from stored payloads, and apply partial updates safely.
- **JSON-friendly serialization** – Custom serializers ensure enumerations, datetimes, and nested models render predictably in API responses.

## Installation

```bash
pip install dynafield
```

The package targets Python 3.12. See `pyproject.toml` for dependency details.

## Quickstart

### Build a model from field definitions

```python
from dynafield import IntField, StrField, build_dynamic_model

fields = [
    StrField(label="customer_name", min_length=1, max_length=50),
    IntField(label="party_size", ge_int=1, le_int=12),
]

Booking = build_dynamic_model("Booking", fields)
record = Booking(customer_name="Ada", party_size=4)
print(record.dump())  # {'customer_name': 'Ada', 'party_size': 4}
```

### Infer fields from a function signature

```python
from datetime import datetime
from typing import Literal

from dynafield import build_model_from_function


def create_invoice(customer_email: str, amount: float, status: Literal["draft", "sent"], sent_at: datetime | None = None):
    ...

Invoice = build_model_from_function(create_invoice)
print(Invoice.model_fields.keys())
```

### Manage schemas with a registry

```python
from dynafield import IntField, RecordSchemaDefinition, RecordSchemaRegistry, StrField

schema = RecordSchemaDefinition(
    name="BookingRecord",
    description="Schema for booking records",
    field_definitions=[
        StrField(label="customer_name"),
        IntField(label="party_size"),
    ],
)
registry = RecordSchemaRegistry([schema])

stored = [{"customer_name": "Ada", "party_size": 4}]
typed_records = registry.build_records(schema.id, stored)
```

### Expose schemas via GraphQL

Every field type ships with a Strawberry GraphQL counterpart. Record schemas can be turned into GraphQL types with `RecordSchemaDefinition.to_gql_type`, making it straightforward to publish dynamic structures through Strawberry and FastAPI.

## Development

1. Clone the repository and install dependencies into a virtual environment.
2. Install the development extras:

   ```bash
   pip install -e .[dev]
   ```

3. Run the test suite:

   ```bash
   pytest
   ```

Example applications live under `example/` and demonstrate FastAPI + Strawberry integration.

## Contributing

Contributions, issues, and discussions are welcome! Please open an issue before making significant changes so we can coordinate direction.

## License

dynafield is released under the Apache 2.0 license.
