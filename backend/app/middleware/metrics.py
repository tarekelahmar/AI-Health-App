import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

try:
    from app.api.v1.metrics_system import REQUESTS, LATENCY
except Exception:  # pragma: no cover
    REQUESTS = None
    LATENCY = None


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        path = request.url.path
        method = request.method
        status = str(response.status_code)

        # avoid exploding label cardinality on docs/static
        if path.startswith("/api/"):
            if REQUESTS is not None:
                REQUESTS.labels(method=method, path=path, status=status).inc()
            if LATENCY is not None:
                LATENCY.labels(method=method, path=path).observe(elapsed)

        return response

