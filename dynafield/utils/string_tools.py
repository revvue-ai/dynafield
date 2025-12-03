import uuid
from typing import Any, Optional, Union


def is_valid_uuid(value: Any) -> bool:
    """Check if a value is a valid UUID (either UUID object or valid UUID string).

    Args:
        value: Input to check

    Returns:
        True if valid UUID, False otherwise
    """
    if isinstance(value, uuid.UUID):
        return True
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def get_valid_uuid(value: Any) -> Optional[uuid.UUID]:
    """Attempt to convert a value to UUID, returning None if invalid.

    Args:
        value: Input value to convert (any type that can be stringified)

    Returns:
        Valid UUID object or None if conversion fails
    """
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def is_string_empty(param: Union[str, uuid.UUID, None]) -> bool:
    """Check if a parameter is None or empty string (after stripping whitespace).

    Args:
        param: Input to check (can be string, UUID, or None)

    Returns:
        True if None or empty string, False otherwise
    """
    if param is None:
        return True
    return not str(param).strip()
