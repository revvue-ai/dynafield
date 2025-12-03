from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.trace import Span

from dynafield import config

from ..logger.logger_config import get_logger
from .registry import TracingConfig, _registry

log = get_logger(__name__)


def configure_tracing() -> None:
    """Configure the tracing system with application settings"""
    tracing_config = TracingConfig(
        service_name=config.SERVICE_NAME,
        host=config.TRACING_HOST,
        port=config.TRACING_PORT,
        protocol=config.TRACING_HOST_PROTOCOL,
        batch_export_enabled=config.TRACING_BATCH_EXPORT_ENABLED,
        batch_export_params={
            "max_queue_size": config.TRACING_BATCH_EXPORT_MAX_QUEUE_SIZE,
            "schedule_delay_millis": config.TRACING_BATCH_EXPORT_SCHEDULE_DELAY_MILLIS,
            "max_export_batch_size": config.TRACING_BATCH_EXPORT_MAX_EXPORT_BATCH_SIZE,
            "export_timeout_millis": config.TRACING_BATCH_EXPORT_EXPORT_TIMEOUT_MILLIS,
        }
        if config.TRACING_BATCH_EXPORT_ENABLED
        else None,
    )

    _registry.configure(tracing_config)


def init_tracing() -> None:
    """Initialize tracing for the FastAPI application"""
    configure_tracing()


def instrument_app(app: FastAPI) -> None:
    log.debug("Instrumenting FastAPI app with tracing")
    _registry.instrument_app(app)


def get_tracer(name: str | None = None) -> trace.Tracer:
    """Get a tracer instance from the registry"""
    return _registry.get_tracer(name)


def log_trace_id(span: Span) -> None:
    """Log tracing information"""
    log.info(f"traceName={span} traceID={span.get_span_context().trace_id} spanID={span.get_span_context().span_id}")
