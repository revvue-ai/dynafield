import logging
import os
import sys
from typing import Literal, Optional

# Log formats
SIMPLE_FORMAT: str = "%(asctime)s - %(levelname)s - %(message)s"
DETAILED_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"


uvicorn_logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": True,
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
}


class ColorFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[41m\033[37m",  # Red background, white text
    }
    RESET = "\033[0m"

    def __init__(self, fmt: str, datefmt: Optional[str] = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors:
            # Create a copy of the record to avoid modifying the original
            record_copy = logging.LogRecord(
                name=record.name,
                level=record.levelno,
                pathname=record.pathname,
                lineno=record.lineno,
                msg=record.msg,
                args=record.args,
                exc_info=record.exc_info,
            )
            record_copy.__dict__.update(record.__dict__)

            color = self.COLORS.get(record.levelname, self.RESET)
            reset = self.RESET

            record_copy.levelname = f"{color}{record.levelname}{reset}"
            record_copy.msg = f"{color}{record.msg}{reset}"

            result = super().format(record_copy)
        else:
            result = super().format(record)

        return result


class LogFilter(logging.Filter):
    """Custom filter to add additional context to log records"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.service_name = os.getenv("SERVICE_NAME", "records-service")
        return True


def _supports_color() -> bool:
    """
    Check if colors should be enabled.
    In PyCharm, we enable colors if PYCHARM_HOSTED is detected,
    regardless of isatty() since we know ANSI works.
    """
    # Always enable colors in PyCharm (we saw ANSI works in diagnostics)
    if "PYCHARM_HOSTED" in os.environ:
        return True

    # For other environments, use normal detection
    if not sys.stdout.isatty():
        return False

    # Windows
    if sys.platform.startswith("win"):
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False

    return True


def setup_logging(
    level: str = "INFO",
    format_type: Literal["simple", "detailed"] = "detailed",
    enable_console: bool = True,
    enable_colors: bool = True,
) -> None:
    """
    Setup application logging configuration.
    """
    format_choices = {
        "simple": SIMPLE_FORMAT,
        "detailed": DETAILED_FORMAT,
    }

    log_format = format_choices.get(format_type, DETAILED_FORMAT)
    use_colors = enable_colors and _supports_color()

    handlers = []

    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        if use_colors:
            formatter = ColorFormatter(log_format, datefmt="%Y-%m-%d %H:%M:%S", use_colors=True)
        else:
            formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")  # type: ignore

        console_handler.setFormatter(formatter)
        console_handler.addFilter(LogFilter())
        handlers.append(console_handler)

    if not handlers:
        handlers.append(logging.NullHandler())  # type: ignore

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    for handler in handlers:
        root_logger.addHandler(handler)

    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Reduce access logs
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("strawberry").setLevel(logging.INFO)

    app_logger = logging.getLogger("app")
    app_logger.setLevel(level)
    for handler in handlers:
        app_logger.addHandler(handler)
    app_logger.propagate = False


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with the given name.
    """
    return logging.getLogger(name or "app")
