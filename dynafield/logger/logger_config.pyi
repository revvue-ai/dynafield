import logging
from typing import Any, Dict, Literal, Optional

SIMPLE_FORMAT: str
DETAILED_FORMAT: str
uvicorn_logging_config: Dict[str, Any]

class ColorFormatter(logging.Formatter):
    COLORS: Dict[str, str]
    RESET: str
    
    def __init__(self, fmt: str, datefmt: Optional[str] = ..., use_colors: bool = ...) -> None: ...
    def format(self, record: logging.LogRecord) -> str: ...

class LogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool: ...

def _supports_color() -> bool: ...

def setup_logging(
    level: str = ...,
    format_type: Literal["simple", "detailed"] = ...,
    enable_console: bool = ...,
    enable_colors: bool = ...,
) -> None: ...

def get_logger(name: Optional[str] = ...) -> logging.Logger: ...