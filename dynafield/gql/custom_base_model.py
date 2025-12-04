import types
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)
from uuid import UUID

import strawberry
from pydantic import BaseModel
from strawberry.scalars import JSON

from dynafield.logger.logger_config import get_logger

log = get_logger()

# Type variables
T = TypeVar("T")

# Type alias for Strawberry types
StrawberryTypeDef = Any  # Strawberry types are complex, so we use Any

# Global registries
_GLOBAL_ENUM_REGISTRY: Dict[str, Any] = {}
_GLOBAL_UNION_REGISTRY: Dict[str, Any] = {}
_GLOBAL_INPUT_UNION_REGISTRY: Dict[str, Any] = {}


class GqlBase(BaseModel):
    _strawberry_cache: ClassVar[Dict[str, StrawberryTypeDef]] = {}
    _strawberry_input_cache: ClassVar[Dict[str, StrawberryTypeDef]] = {}

    @classmethod
    def __class_getitem__(cls, item: Any) -> Any:
        return cls.get_strawberry_class()

    @classmethod
    def get_strawberry_class(
        cls, name: Optional[str] = None, description: Optional[str] = None
    ) -> StrawberryTypeDef:
        type_name = name or f"{cls.__name__}"
        cache_key = f"{cls.__module__}.{cls.__name__}.{type_name}"

        if cache_key in cls._strawberry_cache:
            return cls._strawberry_cache[cache_key]

        annotations = getattr(cls, "__annotations__", {})
        model_fields = cls.model_fields

        class_dict: Dict[str, Any] = {"__annotations__": {}}

        for field_name, field_type in annotations.items():
            field_info = model_fields.get(field_name)

            # Get default value
            field_default: Any = strawberry.UNSET
            if field_info and hasattr(field_info, "default"):
                actual_default = field_info.default
                if actual_default is not None and actual_default is not ...:
                    field_default = actual_default
            if field_default is strawberry.UNSET:
                field_default = getattr(cls, field_name, strawberry.UNSET)

            # Convert the type
            processed_type = convert_field_type(
                field_type, is_input=False, keep_optional=True
            )

            # DEBUG: Log the conversion
            log.debug(f"Field {field_name}: {field_type} -> {processed_type}")

            class_dict["__annotations__"][field_name] = processed_type

            # Determine if field is optional based on type annotation
            is_optional_type = is_optional_annotation(field_type)

            # Check if field has a default value
            has_default = field_default is not strawberry.UNSET

            # Check if Pydantic field is required
            is_pydantic_required = True
            if field_info is not None:
                is_pydantic_required = field_info.is_required()

            # Field is required in GraphQL only if:
            # 1. No default value AND
            # 2. Type is not optional AND
            # 3. Pydantic field is required
            is_graphql_required = (
                (not has_default) and (not is_optional_type) and is_pydantic_required
            )

            if has_default:
                # Field has a default value
                class_dict[field_name] = field_default
            elif not is_graphql_required:
                # Field is not required in GraphQL
                class_dict[field_name] = strawberry.field(default=None)
            else:
                # Field is required in GraphQL
                class_dict[field_name] = strawberry.field()

        StrawberryBase = type(type_name, (), class_dict)
        StrawberryType = strawberry.type(
            StrawberryBase, name=type_name, description=description
        )
        cls._strawberry_cache[cache_key] = StrawberryType
        return StrawberryType

    @classmethod
    def get_strawberry_input(
        cls, name: Optional[str] = None, description: Optional[str] = None
    ) -> StrawberryTypeDef:
        type_name = name or f"{cls.__name__}Input"
        cache_key = f"{cls.__module__}.{cls.__name__}.{type_name}"

        if cache_key in cls._strawberry_input_cache:
            return cls._strawberry_input_cache[cache_key]

        annotations = getattr(cls, "__annotations__", {})
        class_dict: Dict[str, Any] = {"__annotations__": {}}

        model_fields = cls.model_fields

        for field_name, field_type in annotations.items():
            field_info = model_fields.get(field_name)

            field_default: Any = strawberry.UNSET
            if field_info and hasattr(field_info, "default"):
                actual_default = field_info.default
                if actual_default is not None and actual_default is not ...:
                    field_default = actual_default
            if field_default is strawberry.UNSET:
                field_default = getattr(cls, field_name, strawberry.UNSET)

            processed_type = convert_field_type(
                field_type, is_input=True, keep_optional=True
            )
            class_dict["__annotations__"][field_name] = processed_type

            # Same logic for input types
            is_optional_type = is_optional_annotation(field_type)
            has_default = field_default is not strawberry.UNSET
            is_pydantic_required = field_info is not None and field_info.is_required()

            is_graphql_required = (
                (not has_default) and (not is_optional_type) and is_pydantic_required
            )

            if has_default:
                class_dict[field_name] = field_default
            elif not is_graphql_required:
                class_dict[field_name] = strawberry.field(default=None)
            else:
                class_dict[field_name] = strawberry.field()

        StrawberryBase = type(type_name, (), class_dict)
        StrawberryInput = strawberry.input(
            StrawberryBase, name=type_name, description=description
        )
        cls._strawberry_input_cache[cache_key] = StrawberryInput
        return StrawberryInput

    def to_strawberry(self) -> Any:
        strawberry_class = self.get_strawberry_class()

        field_values: Dict[str, Any] = {}
        for field_name in self.model_fields:
            value = getattr(self, field_name)

            if isinstance(value, GqlBase):  # Changed from BaseModel to GqlBase
                field_values[field_name] = value.to_strawberry()
            elif isinstance(value, list):
                field_values[field_name] = [
                    item.to_strawberry() if isinstance(item, GqlBase) else item  # Changed
                    for item in value
                ]
            elif isinstance(value, dict):
                field_values[field_name] = {
                    key: (
                        val.to_strawberry() if isinstance(val, GqlBase) else val  # Changed
                    )
                    for key, val in value.items()
                }
            else:
                field_values[field_name] = value

        return strawberry_class(**field_values)


def is_optional_annotation(field_type: Any) -> bool:
    """Check if a type annotation is optional (contains None)"""
    # Handle Python 3.10+ pipe syntax (A | B)
    if hasattr(types, "UnionType") and isinstance(field_type, types.UnionType):
        args = get_args(field_type)
        return type(None) in args

    # Handle typing.Union
    origin = get_origin(field_type)
    if origin is Union:
        args = get_args(field_type)
        return type(None) in args

    return False


def is_union_type(field_type: Any) -> bool:
    """Check if a type is a Union type (with multiple non-None types)"""
    # Handle Python 3.10+ pipe syntax
    if hasattr(types, "UnionType") and isinstance(field_type, types.UnionType):
        args = get_args(field_type)
        non_none_args = [arg for arg in args if arg is not type(None)]
        return len(non_none_args) > 1

    # Handle typing.Union
    origin = get_origin(field_type)
    if origin is Union:
        args = get_args(field_type)
        non_none_args = [arg for arg in args if arg is not type(None)]
        return len(non_none_args) > 1

    return False


def get_simple_type_name(t: Any) -> str:
    """Get a simple name for a type"""
    if t is type(None):
        return "None"

    if isinstance(t, type):
        return t.__name__
    elif hasattr(t, "__name__"):
        return t.__name__
    else:
        origin = get_origin(t)
        if origin:
            return origin.__name__
        else:
            type_str = str(t)
            type_str = type_str.replace("typing.", "")
            type_str = type_str.replace("builtins.", "")
            type_str = type_str.replace("<class '", "").replace("'>", "")
            if "[" in type_str:
                type_str = type_str.split("[")[0]
            return type_str


def create_union_type(union_name: str, types_list: List[Any], is_input: bool = False) -> Any:
    """Create a Strawberry union type"""
    # Filter out None types
    non_none_types = [t for t in types_list if t is not type(None)]

    if len(non_none_types) == 0:
        return JSON

    # Create cache key
    type_signatures = []
    for t in non_none_types:
        if isinstance(t, type):
            type_signatures.append(f"{t.__module__}.{t.__name__}")
        else:
            type_signatures.append(str(t))

    union_key = f"{union_name}:{':'.join(sorted(type_signatures))}:input_{is_input}"

    registry = _GLOBAL_INPUT_UNION_REGISTRY if is_input else _GLOBAL_UNION_REGISTRY

    if union_key in registry:
        return registry[union_key]

    # Convert types - IMPORTANT: Use keep_optional=False for union members
    converted_types: List[Any] = []
    for t in non_none_types:
        converted_type = convert_field_type(t, is_input=is_input, keep_optional=False)
        if converted_type is not None:
            converted_types.append(converted_type)
            log.debug(f"Union member {t} -> {converted_type}")

    if len(converted_types) == 0:
        return JSON

    if len(converted_types) == 1:
        return converted_types[0]

    if is_input:
        return JSON

    try:
        # Filter valid GraphQL types
        valid_types = []
        for t in converted_types:
            # Check if it's a Strawberry type
            if is_strawberry_type(t):
                valid_types.append(t)
                log.debug(f"Valid union type: {t}")
            else:
                log.debug(f"Invalid union type (not Strawberry): {t}")

        if len(valid_types) < 2:
            log.debug(
                f"Not enough valid GraphQL types for union {union_name}. Valid types: {valid_types}"
            )
            if valid_types:
                return cast(Any, valid_types[0])
            else:
                return JSON

        # Create the union
        union_type = strawberry.union(union_name, types=tuple(valid_types))
        registry[union_key] = union_type
        return union_type

    except Exception as e:
        log.debug(f"Error creating union {union_name}: {e}")
        import traceback

        traceback.print_exc()
        return JSON


def is_strawberry_type(t: Any) -> bool:
    """Check if a type is a valid Strawberry/GraphQL type"""
    # Basic GraphQL scalar types
    if t in (str, int, float, bool, datetime, date, time, Decimal):
        return True

    # Strawberry JSON scalar
    if t is JSON:
        return True

    # Strawberry enum
    if isinstance(t, type) and issubclass(t, Enum):
        return True

    # Check if it has Strawberry definition
    if hasattr(t, "__strawberry_definition__") or hasattr(t, "_type_definition"):
        return True

    # Check using strawberry's own function if available
    try:
        if hasattr(strawberry, "is_strawberry_type"):
            return cast(bool, strawberry.is_strawberry_type(t))
    except Exception:
        pass

    return False


_PROCESSING_TYPES: set[int] = set()


def convert_field_type(
    field_type: Any, is_input: bool = False, keep_optional: bool = False
) -> Any:
    """
    Convert Pydantic types to Strawberry-compatible types.

    Args:
        keep_optional: If True, preserve Optional wrapper for Optional[T] types.
                      If False, return just T for Optional[T].
    """
    log.debug(f"convert_field_type called: {field_type}, keep_optional={keep_optional}")

    if field_type is type(None):
        return None

    type_id = id(field_type)
    if type_id in _PROCESSING_TYPES:
        return JSON

    _PROCESSING_TYPES.add(type_id)

    try:
        # Handle Python 3.10+ pipe syntax
        is_pipe_union = hasattr(types, "UnionType") and isinstance(
            field_type, types.UnionType
        )

        # Get origin and args
        origin = get_origin(field_type)
        args = get_args(field_type)

        log.debug(f"  Origin: {origin}, Args: {args}, is_pipe_union: {is_pipe_union}")

        # Check if it's an Optional type (contains None)
        if (origin is Union or is_pipe_union) and args and type(None) in args:
            log.debug(f"  Detected Optional type")
            non_none_args = [arg for arg in args if arg is not type(None)]

            if len(non_none_args) == 1:
                # Optional[T]
                inner_type = convert_field_type(
                    non_none_args[0], is_input=is_input, keep_optional=False
                )
                log.debug(f"  Optional inner type: {inner_type}")
                if keep_optional and inner_type is not None:
                    # Keep the Optional wrapper
                    result_type: Any = Optional[inner_type]
                    log.debug(f"  Returning Optional[{inner_type}]")
                    return result_type
                else:
                    # Return just the inner type
                    log.debug(f"  Returning {inner_type} (no Optional wrapper)")
                    return inner_type

            elif len(non_none_args) > 1:
                # Union[A, B, None]
                log.debug(f"  Union with None: {non_none_args}")
                type_names = []
                for t in non_none_args:
                    name = get_simple_type_name(t)
                    if name not in type_names:
                        type_names.append(name)
                union_name = "Or".join(type_names)

                union_type = create_union_type(union_name, non_none_args, is_input=is_input)
                if keep_optional and union_type is not None:
                    result_type = Optional[union_type]
                    log.debug(f"  Returning Optional[{union_type}]")
                    return result_type
                else:
                    log.debug(f"  Returning {union_type}")
                    return union_type

        # Handle regular Union (without None)
        if is_union_type(field_type):
            log.debug(f"  Detected regular union type")
            if origin is Union or is_pipe_union:
                union_types = list(args)
            else:
                union_types = []

            if union_types:
                type_names = []
                for t in union_types:
                    name = get_simple_type_name(t)
                    if name not in type_names:
                        type_names.append(name)
                union_name = "Or".join(type_names)

                result = create_union_type(union_name, union_types, is_input=is_input)
                log.debug(f"  Union result: {result}")
                return result

        # Handle List types
        if origin is list and args:
            inner_type = convert_field_type(
                args[0], is_input=is_input, keep_optional=keep_optional
            )
            if inner_type is not None:
                result_type = List[inner_type]  # type: ignore[valid-type]
                log.debug(f"  List result: {result_type}")
                return result_type

        # Handle Python 3.10+ list[T] syntax
        if hasattr(field_type, "__origin__") and field_type.__origin__ is list:
            args = get_args(field_type)
            if args:
                inner_type = convert_field_type(
                    args[0], is_input=is_input, keep_optional=keep_optional
                )
                if inner_type is not None:
                    result_type = List[inner_type]  # type: ignore[valid-type]
                    log.debug(f"  List[T] result: {result_type}")
                    return result_type

        # Handle Dict types
        if origin is dict or field_type is dict:
            log.debug(f"  Dict -> JSON scalar")
            return JSON

        if hasattr(field_type, "__origin__") and field_type.__origin__ is dict:
            log.debug(f"  Dict[K, V] -> JSON scalar")
            return JSON

        # Handle Any type
        if field_type is Any:
            log.debug(f"  Any -> JSON scalar")
            return JSON

        # Handle UUID
        if field_type is UUID or (
            isinstance(field_type, type)
            and getattr(field_type, "__name__", "") == "UUID"
        ):
            log.debug(f"  UUID -> str")
            return str

        # Handle datetime types
        if field_type in (datetime, date, time):
            log.debug(f"  datetime type: {field_type}")
            return field_type

        # Handle Decimal
        if field_type is Decimal:
            log.debug(f"  Decimal")
            return Decimal

        # Handle Literal
        if origin is Literal:
            log.debug(f"  Literal -> str")
            return str

        # Handle Enum
        if isinstance(field_type, type) and issubclass(field_type, Enum):
            log.debug(f"  Enum: {field_type}")
            enum_key = f"{field_type.__module__}.{field_type.__name__}"
            if enum_key in _GLOBAL_ENUM_REGISTRY:
                return _GLOBAL_ENUM_REGISTRY[enum_key]
            strawberry_enum = strawberry.enum(field_type)
            _GLOBAL_ENUM_REGISTRY[enum_key] = strawberry_enum
            return strawberry_enum

        # Handle nested Pydantic models that inherit from GqlBase
        if isinstance(field_type, type) and issubclass(field_type, BaseModel):
            log.debug(f"  Pydantic model: {field_type}")

            # Check if it's a GqlBase
            if issubclass(field_type, GqlBase):
                try:
                    if is_input:
                        nested_type = field_type.get_strawberry_input()
                    else:
                        nested_type = field_type.get_strawberry_class()
                    log.debug(f"  GqlBase -> Strawberry type: {nested_type}")
                    return nested_type
                except Exception as e:
                    log.debug(f"  Error getting Strawberry type for {field_type}: {e}")
                    return JSON
            else:
                # Not a GqlBase, try to wrap it
                try:
                    # Create a temporary GqlBase subclass
                    temp_class_name = f"Temp{field_type.__name__}"
                    temp_class = type(temp_class_name, (GqlBase, field_type), {})
                    if is_input:
                        nested_type = temp_class.get_strawberry_input()
                    else:
                        nested_type = temp_class.get_strawberry_class()
                    log.debug(f"  Wrapped Pydantic model -> Strawberry type: {nested_type}")
                    return nested_type
                except Exception as e:
                    log.debug(f"  Could not wrap {field_type}: {e}")
                    return JSON

        # Handle bytes
        if field_type is bytes:
            log.debug(f"  bytes -> str")
            return str

        # Primitive types
        if field_type in (str, int, float, bool):
            log.debug(f"  Primitive type: {field_type}")
            return field_type

        # Fallback - log what we got
        log.debug(f"  Fallback for unknown type: {field_type} (type: {type(field_type)})")
        return JSON

    finally:
        _PROCESSING_TYPES.discard(type_id)