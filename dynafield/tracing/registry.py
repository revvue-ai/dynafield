from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider

from dynafield.logger.logger_config import get_logger

log = get_logger(__name__)


@dataclass
class TracingConfig:
    service_name: str
    host: str
    port: int
    protocol: str = "http://"
    batch_export_enabled: bool = True
    batch_export_params: Optional[Dict[str, Any]] = None


class TracingRegistry:
    def __init__(self) -> None:
        self._config: Optional[TracingConfig] = None
        self._tracer_provider: Optional[TracerProvider] = None
        self._instrumentors: List[FastAPIInstrumentor] = []  # Store instances, not classes

    def configure(self, config: TracingConfig) -> None:
        """Set up the tracing configuration"""
        self._config = config
        self._initialize_tracer_provider()

    def _initialize_tracer_provider(self) -> None:
        """Initialize the tracer provider with the configured settings"""
        if not self._config:
            raise ValueError("Tracing not configured")

        resource = Resource.create({SERVICE_NAME: self._config.service_name})
        self._tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(self._tracer_provider)

    def register_instrumentor(self, instrumentor_class: Callable[..., FastAPIInstrumentor]) -> None:
        """Register an instrumentor class to be instantiated and applied later"""
        # Create an instance of the instrumentor
        instrumentor = instrumentor_class()
        self._instrumentors.append(instrumentor)

    def instrument_app(self, app: FastAPI) -> None:
        """Instrument the FastAPI application and all registered instrumentors"""
        if not self._tracer_provider:
            raise ValueError("Tracer provider not initialized")

        # Instrument FastAPI first
        FastAPIInstrumentor.instrument_app(app, tracer_provider=self._tracer_provider)

        # Instrument all registered instrumentors
        for instrumentor in self._instrumentors:
            instrumentor.instrument(tracer_provider=self._tracer_provider)

    def get_tracer(self, name: Optional[str] = None) -> trace.Tracer:
        """Get a tracer instance"""
        if not self._tracer_provider:
            # raise ValueError("Tracer provider not initialized")
            log.warning("Tracer provider not initialized, returning default tracer")
        log.debug(f"Getting tracer for: {name or __name__}")
        return trace.get_tracer(name or __name__)


_registry = TracingRegistry()
