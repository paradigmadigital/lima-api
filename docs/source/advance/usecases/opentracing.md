# Opentracing

Lima-API only support [OpenTelemetry][open-telemetry] using [opentelemetry-instrumentation-httpx](https://pypi.org/project/opentelemetry-instrumentation-httpx/).
However, sometime you have old code that use [OpenTracing][open-tracing], in that case in order to migrate the clients to Lima-API you could use the following code:

```python
import random

from opentelemetry import trace as opentelemetry_trace
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.sdk.trace import TracerProvider, IdGenerator
from opentracing_instrumentation import get_current_span


class OpenTracingIdGenerator(IdGenerator):
   def generate_span_id(self) -> int:
       span = get_current_span()
       if not span:
           return random.getrandbits(64)
       return span.span_id

   def generate_trace_id(self) -> int:
       span = get_current_span()
       if not span:
           return random.getrandbits(128)
       return span.trace_id

tracer_provider = TracerProvider(id_generator=OpenTracingIdGenerator())
opentelemetry_trace.set_tracer_provider(tracer_provider)
HTTPXClientInstrumentor().instrument(tracer_provider=tracer_provider)
set_global_textmap(B3MultiFormat())
```
With that code all request that Lima-API do, will get the `span_id` and `trace_id` from [OpenTracing][open-tracing] and sending using [OpenTelemetry][open-telemetry].

[open-telemetry]: https://opentelemetry.io/
[open-tracing]: http://opentracing.io/
