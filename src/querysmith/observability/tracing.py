"""OpenTelemetry setup with a no-op-safe default and explicit safe attributes."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter


def configure_tracing(
    exporter: SpanExporter | None = None,
    *,
    endpoint: str | None = None,
) -> None:
    provider = TracerProvider()
    if exporter is None and endpoint:
        exporter = OTLPSpanExporter(endpoint=endpoint)
    if exporter is not None:
        provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


@contextmanager
def span(name: str, **safe_attributes: Any) -> Iterator[None]:
    tracer = trace.get_tracer("querysmith")
    with tracer.start_as_current_span(name, attributes=safe_attributes):
        yield
