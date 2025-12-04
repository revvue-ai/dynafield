# your_package/__init__.pyi
from typing import Any, ClassVar, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T")
StrawberryTypeDef = Any

class GqlBase(BaseModel):
    _strawberry_cache: ClassVar[Dict[str, StrawberryTypeDef]]
    _strawberry_input_cache: ClassVar[Dict[str, StrawberryTypeDef]]
    
    @classmethod
    def __class_getitem__(cls, item: Any) -> Any: ...
    
    @classmethod
    def get_strawberry_class(
        cls, name: Optional[str] = None, description: Optional[str] = None
    ) -> StrawberryTypeDef: ...
    
    @classmethod
    def get_strawberry_input(
        cls, name: Optional[str] = None, description: Optional[str] = None
    ) -> StrawberryTypeDef: ...
    
    def to_strawberry(self) -> Any: ...

# Export functions
def is_optional_annotation(field_type: Any) -> bool: ...
def is_union_type(field_type: Any) -> bool: ...
def convert_field_type(
    field_type: Any, is_input: bool = False, keep_optional: bool = False
) -> Any: ...
def create_union_type(
    union_name: str, types_list: List[Any], is_input: bool = False
) -> Any: ...
def assert_graphql_success(data: Dict[str, Any]) -> None: ...
def validate_with_pydantic(strawberry_input: Any, pydantic_model: Type[T]) -> T: ...
def strawberry_to_dict(obj: Any) -> Any: ...