from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Bounded cardinality labels only: method, endpoint, status_code
HTTP_REQUESTS_TOTAL = Counter(
    "syncops_http_requests_total",
    "Total count of HTTP requests processed by endpoint and status code.",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "syncops_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

HTTP_ERRORS_TOTAL = Counter(
    "syncops_http_errors_total",
    "Total count of 4xx and 5xx HTTP responses.",
    ["method", "endpoint", "status_code"],
)

# Incident lifecycle metrics (bounded labels: operation, severity, status)
INCIDENT_OPERATIONS_TOTAL = Counter(
    "syncops_incident_operations_total",
    "Count of incident lifecycle actions.",
    ["operation", "status"],
)

# Triage operational metrics (bounded labels: mode, outcome)
TRIAGE_OPERATIONS_TOTAL = Counter(
    "syncops_triage_operations_total",
    "Count of automated incident triage requests.",
    ["mode", "outcome"],
)

# Synthetic platform gauges
SYNTHETIC_SYNC_SUCCESS_RATE_GAUGE = Gauge(
    "syncops_synthetic_sync_success_rate",
    "Current synthetic sync success rate percentage (0-100)."
)

SYNTHETIC_ACTIVE_INCIDENTS_GAUGE = Gauge(
    "syncops_synthetic_active_incidents",
    "Number of active unmitigated incidents."
)

def get_metrics_payload() -> tuple[bytes, str]:
    """Generates Prometheus scrapable metrics payload and Content-Type."""
    return generate_latest(), CONTENT_TYPE_LATEST
