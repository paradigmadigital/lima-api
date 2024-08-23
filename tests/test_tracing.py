from client import (
    SyncClient,
)
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from pytest_httpserver import HTTPServer


class TestOpentracing:
    def setup_method(self):
        self.client_cls = SyncClient

    def test_opentracing(self, httpserver: HTTPServer):
        base_url = httpserver.url_for("")
        httpserver.expect_request("/items").respond_with_json([])

        provider = TracerProvider()
        trace.set_tracer_provider(provider)
        tracer = trace.get_tracer("lima-example")

        with (
            tracer.start_as_current_span("event-loop") as span,
            self.client_cls(base_url) as client,
        ):
            client.sync_list()

        assert len(httpserver.log) == 1
        request, _ = httpserver.log[0]
        assert "Traceparent" in request.headers
        _, trace_id, span_id, _ = request.headers["Traceparent"].split("-")
        assert trace_id in hex(span.context.trace_id).replace("x", "")
        assert span_id not in hex(span.context.span_id).replace("x", "")
