from typing import Any, Dict, Type, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def assert_graphql_success(data: Dict[str, Any]) -> None:
    if "errors" in data:
        errors = data["errors"]
        errorMsg = "".join([errors[i]["message"] for i in range(len(errors)) if "message" in errors[i]])
        raise Exception(errorMsg)


def validate_with_pydantic(strawberry_input: Any, pydantic_model: Type[T]) -> T:
    """
    Convert Strawberry input to Pydantic model with proper error handling
    """
    try:
        # Extract all fields from strawberry input
        input_data = {}
        for field_name in strawberry_input.__annotations__:
            if hasattr(strawberry_input, field_name):
                input_data[field_name] = getattr(strawberry_input, field_name)

        # Validate with Pydantic
        return pydantic_model(**input_data)

    except ValidationError as e:
        raise ValueError(f"Validation failed: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Conversion error: {e}") from e
