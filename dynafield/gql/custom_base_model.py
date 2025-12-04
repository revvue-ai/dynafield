import types
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar, Dict, List, Literal, Optional, TypeVar, Union, get_args, get_origin
from uuid import UUID

import strawberry
from pydantic import BaseModel

from ..logger.logger_config import get_logger

log = get_logger()

# Type variables for better typing
T = TypeVar("T")
StrawberryType = Any  # Since strawberry types are complex, we use Any for now

# Global enum registry to prevent redefinition
_GLOBAL_ENUM_REGISTRY: Dict[str, Any] = {}
# Global union registry to prevent redefinition
_GLOBAL_UNION_REGISTRY: Dict[str, Any] = {}
# Global input union registry (we'll handle these differently)
_GLOBAL_INPUT_UNION_REGISTRY: Dict[str, Any] = {}


class GqlBase(BaseModel):
    # Cache for generated Strawberry types
    _strawberry_cache: ClassVar[Dict[str, Any]] = {}
    _strawberry_input_cache: ClassVar[Dict[str, Any]] = {}

    @classmethod
    def __class_getitem__(cls, item: Any) -> Any:
        return cls.get_strawberry_class()

    @classmethod
    def get_strawberry_class(cls, name: Optional[str] = None, description: Optional[str] = None) -> Any:
        type_name = name or f"{cls.__name__}"
        cache_key = f"{cls.__module__}.{cls.__name__}.{type_name}"

        if cache_key in cls._strawberry_cache:
            return cls._strawberry_cache[cache_key]

        annotations = getattr(cls, "__annotations__", {})
        model_fields = cls.model_fields

        class_dict: Dict[str, Any] = {"__annotations__": {}}

        for field_name, field_type in annotations.items():
            field_info = model_fields.get(field_name)
            field_default = getattr(cls, field_name, strawberry.UNSET)
            processed_type = convert_field_type(field_type, is_input=False)

            class_dict["__annotations__"][field_name] = processed_type

            # Determine if field is required
            is_required = field_info is None or (field_info.is_required() and field_default is strawberry.UNSET)

            if field_default is not strawberry.UNSET:
                # Field has a default value
                class_dict[field_name] = field_default
            elif not is_required:
                # Field is not required and has no default
                class_dict[field_name] = None
            else:
                # Field is required - use strawberry.field()
                class_dict[field_name] = strawberry.field()

        StrawberryBase = type(type_name, (), class_dict)
        StrawberryType = strawberry.type(StrawberryBase, name=type_name, description=description)
        cls._strawberry_cache[cache_key] = StrawberryType
        return StrawberryType

    @classmethod
    def get_strawberry_input(cls, name: Optional[str] = None, description: Optional[str] = None) -> Any:
        type_name = name or f"{cls.__name__}Input"
        cache_key = f"{cls.__module__}.{cls.__name__}.{type_name}"

        if cache_key in cls._strawberry_input_cache:
            return cls._strawberry_input_cache[cache_key]

        annotations = getattr(cls, "__annotations__", {})
        class_dict: Dict[str, Any] = {"__annotations__": {}}

        model_fields = cls.model_fields

        for field_name, field_type in annotations.items():
            field_info = model_fields.get(field_name)
            field_default = getattr(cls, field_name, strawberry.UNSET)
            processed_type = convert_field_type(field_type, is_input=True)

            class_dict["__annotations__"][field_name] = processed_type

            # For input types, check if field is required
            is_required = field_info is None or (field_info.is_required() and field_default is strawberry.UNSET)

            if field_default is not strawberry.UNSET:
                # Field has a default value
                class_dict[field_name] = field_default
            elif not is_required:
                # Field is not required - set to None to make it optional
                class_dict[field_name] = None
            else:
                # Field is required - use strawberry.field() without default
                class_dict[field_name] = strawberry.field()

        StrawberryBase = type(type_name, (), class_dict)
        StrawberryInput = strawberry.input(StrawberryBase, name=type_name, description=description)
        cls._strawberry_input_cache[cache_key] = StrawberryInput
        return StrawberryInput

    def to_strawberry(self) -> Any:
        """Convert this Pydantic model instance to its corresponding Strawberry type"""
        strawberry_class = self.get_strawberry_class()

        # Get the field values from this instance
        field_values: Dict[str, Any] = {}
        for field_name in self.model_fields:
            value = getattr(self, field_name)

            # Recursively convert nested Pydantic models
            if isinstance(value, BaseModel):
                field_values[field_name] = value.to_strawberry()  # type: ignore
            elif isinstance(value, list):
                field_values[field_name] = [
                    item.to_strawberry() if isinstance(item, BaseModel) else item  # type: ignore
                    for item in value
                ]
            elif isinstance(value, dict):
                field_values[field_name] = {
                    key: (val.to_strawberry() if isinstance(val, BaseModel) else val)  # type: ignore
                    for key, val in value.items()
                }
            else:
                field_values[field_name] = value

        return strawberry_class(**field_values)


def is_union_type(field_type: Any) -> bool:
    """Check if a type is a Union type (including Python 3.10+ | syntax)"""
    origin = get_origin(field_type)

    # Handle typing.Union
    if origin is Union:
        args = get_args(field_type)
        # It's a proper union if there are multiple non-None types
        non_none_args = [arg for arg in args if arg is not type(None)]
        return len(non_none_args) > 1

    # Handle Python 3.10+ union types (A | B) - this creates types.UnionType
    if hasattr(types, "UnionType") and isinstance(field_type, types.UnionType):
        args = get_args(field_type)
        # It's a union if it has multiple non-None types
        non_none_args = [arg for arg in args if arg is not type(None)]
        return len(non_none_args) > 1

    return False


def create_union_type(union_name: str, types_list: List[Any], is_input: bool = False) -> Any:
    """Create a Strawberry union type and cache it"""
    union_key = f"{union_name}:{':'.join(sorted(str(t) for t in types_list))}:input_{is_input}"

    if is_input:
        registry = _GLOBAL_INPUT_UNION_REGISTRY
    else:
        registry = _GLOBAL_UNION_REGISTRY

    if union_key in registry:
        return registry[union_key]

    # Filter out None types and convert the rest to Strawberry types
    non_none_types: List[Any] = []
    for t in types_list:
        if t is not type(None):
            converted_type = convert_field_type(t, is_input=is_input)
            # Check if it's a proper Strawberry type using the new method
            if (
                hasattr(converted_type, "__strawberry_definition__")
                or hasattr(converted_type, "_type_definition")  # Fallback for older versions
                or converted_type in (str, int, float, bool, datetime, date, time, Decimal)
                or (isinstance(converted_type, type) and issubclass(converted_type, Enum))
            ):
                non_none_types.append(converted_type)
            else:
                log.debug(f"Warning: Type {converted_type} is not a proper Strawberry type for union {union_name}")

    if len(non_none_types) == 1:
        # If only one non-None type, it's actually Optional, not Union
        return Optional[non_none_types[0]]

    if len(non_none_types) == 0:
        log.debug(f"Warning: No valid types found for union {union_name}. Using JSON scalar.")
        return strawberry.scalars.JSON

    # For input types, we can't use GraphQL unions, so we fall back to JSON
    if is_input:
        log.debug(f"Warning: Using JSON scalar for input union {union_name} (GraphQL doesn't support input unions)")
        return strawberry.scalars.JSON

    # Create the union type (only for output types)
    try:
        union_type = strawberry.union(union_name, types=tuple(non_none_types))
        registry[union_key] = union_type
        return union_type
    except Exception as e:
        log.debug(f"Error creating union type {union_name}: {e}")
        log.debug(f"Types attempted: {non_none_types}")
        import traceback

        traceback.print_exc()
        return strawberry.scalars.JSON


# Track currently processing types to avoid infinite recursion
_PROCESSING_TYPES: set[Any] = set()


def convert_field_type(field_type: Any, is_input: bool = False) -> Any:
    """Convert Pydantic types to Strawberry-compatible types with proper scalar handling"""
    # Create a unique identifier for this type to track recursion
    type_id = id(field_type)
    if type_id in _PROCESSING_TYPES:
        log.debug(f"Warning: Recursion detected for type {field_type}, using JSON scalar as fallback")
        return strawberry.scalars.JSON

    _PROCESSING_TYPES.add(type_id)

    try:
        origin = get_origin(field_type)
        args = get_args(field_type)

        # Handle Union types (both typing.Union and Python 3.10+ | syntax)
        if is_union_type(field_type):
            log.debug(f"Processing union type: {field_type}, origin: {origin}, args: {args}")

            # Handle typing.Union
            if origin is Union:
                union_name = "Union_" + "_or_".join(
                    [
                        getattr(
                            arg,
                            "__name__",
                            str(arg).replace("[", "_").replace("]", "_").replace(" ", "_").replace("|", "_or_"),
                        )
                        for arg in args
                        if arg is not type(None)
                    ]
                )
            # Handle Python 3.10+ union types (types.UnionType)
            elif hasattr(types, "UnionType") and isinstance(field_type, types.UnionType):
                union_name = "Union_" + "_or_".join(
                    [
                        getattr(
                            arg,
                            "__name__",
                            str(arg).replace("[", "_").replace("]", "_").replace(" ", "_").replace("|", "_or_"),
                        )
                        for arg in args
                        if arg is not type(None)
                    ]
                )
            else:
                # Fallback for other union-like types
                union_name = "Union_Unknown"

            # Limit union name length to avoid issues
            union_name = union_name[:100]
            result = create_union_type(union_name, list(args), is_input=is_input)
            return result

        # Handle Optional types (Union with None) - including Python 3.10+ syntax
        if (
            origin is Union
            or (hasattr(types, "UnionType") and isinstance(field_type, types.UnionType))
            or (hasattr(field_type, "__args__") and not hasattr(field_type, "__origin__"))
        ):
            if type(None) in args:
                non_none_args = [arg for arg in args if arg is not type(None)]
                if len(non_none_args) == 1:
                    result = Optional[convert_field_type(non_none_args[0], is_input=is_input)]
                    return result

        # Handle List types
        if origin is list and args:
            inner_type: Any = convert_field_type(args[0], is_input=is_input)
            result = List[inner_type]
            return result

        # Handle Dict types
        if origin is dict or field_type is dict:
            return strawberry.scalars.JSON

        # Handle Any type
        if field_type is Any:
            return strawberry.scalars.JSON

        # Handle UUID
        if field_type is UUID or (hasattr(field_type, "__name__") and getattr(field_type, "__name__") == "UUID"):
            return str

        # Handle datetime types
        if field_type is datetime:
            return datetime
        if field_type is date:
            return date
        if field_type is time:
            return time

        # Handle Decimal
        if field_type is Decimal:
            return Decimal

        # Handle Literal types
        if origin is Literal:
            return str

        # Handle custom enums with GLOBAL registry
        if isinstance(field_type, type) and issubclass(field_type, Enum):
            enum_key = f"{field_type.__module__}.{field_type.__name__}"
            if enum_key in _GLOBAL_ENUM_REGISTRY:
                return _GLOBAL_ENUM_REGISTRY[enum_key]
            strawberry_enum = strawberry.enum(field_type)
            _GLOBAL_ENUM_REGISTRY[enum_key] = strawberry_enum
            return strawberry_enum

        # Handle nested Pydantic models
        if isinstance(field_type, type) and hasattr(field_type, "get_strawberry_class"):
            try:
                if is_input:
                    nested_type = field_type.get_strawberry_input()  # type: ignore
                else:
                    nested_type = field_type.get_strawberry_class()
                return nested_type
            except Exception as e:
                log.debug(f"Error creating nested type for {field_type}: {e}")
                import traceback

                traceback.print_exc()
                return strawberry.scalars.JSON

        # Handle bytes
        if field_type is bytes:
            return str

        # Primitive types
        if field_type in (str, int, float, bool):
            return field_type

        # Handle other class types (like your objA and objB)
        if isinstance(field_type, type):
            if issubclass(field_type, BaseModel) and hasattr(field_type, "get_strawberry_class"):
                try:
                    if is_input:
                        return field_type.get_strawberry_input()  # type: ignore
                    else:
                        return field_type.get_strawberry_class()  # Removed is_sub_class parameter
                except Exception as e:
                    log.debug(f"Error converting Pydantic model {field_type}: {e}")

            # For other classes, try to use them as-is (they might be Strawberry types already)
            return field_type

        # Fallback for unknown types
        log.debug(f"Warning: Using JSON scalar for unknown type: {field_type} (origin: {origin}, type: {type(field_type)})")
        return strawberry.scalars.JSON

    finally:
        _PROCESSING_TYPES.discard(type_id)
