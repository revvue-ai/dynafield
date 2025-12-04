from typing import Any, Dict, Type, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def assert_graphql_success(data: Dict[str, Any]) -> None:
    if "errors" in data:
        errors = data["errors"]
        errorMsg = "".join([errors[i]["message"] for i in range(len(errors)) if "message" in errors[i]])
        raise Exception(errorMsg)


def strawberry_to_dict(obj: Any) -> Any:
  """
  Recursively convert Strawberry input objects (and nested *Input objects)
  into plain dicts/lists/primitives that Pydantic can consume.
  """
  if obj is None:
    return None

  # Already a basic type or dict
  if isinstance(obj, (str, int, float, bool, dict)):
    return obj

  # Lists / tuples of inputs
  if isinstance(obj, (list, tuple, set, frozenset)):
    return [strawberry_to_dict(item) for item in obj]

  # Strawberry input-like object
  annotations = getattr(obj, "__annotations__", None)
  if annotations:
    data: dict[str, Any] = {}
    for field_name in annotations:
      if hasattr(obj, field_name):
        value = getattr(obj, field_name)

        # Keep your existing "Input" suffix stripping for field names
        if "Input" in field_name:
          key = field_name.replace("Input", "")
        else:
          key = field_name

        data[key] = strawberry_to_dict(value)
    return data

  # Fallback: return as-is (Pydantic may still handle it)
  return obj


def validate_with_pydantic(strawberry_input: Any, pydantic_model: Type[T]) -> T:
  """
  Convert Strawberry input (including nested *Input objects) to a structure
  that Pydantic can validate against `pydantic_model`.
  """
  try:
    input_data = strawberry_to_dict(strawberry_input)
    return pydantic_model(**input_data)

  except ValidationError as e:
    raise ValueError(f"Validation failed: {e}") from e
  except Exception as e:
    raise RuntimeError(f"Conversion error: {e}") from e