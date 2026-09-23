"""Bounded-cardinality Prometheus metrics."""

from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter("qs_requests_total", "HTTP requests", ["route", "status"])
REQUEST_SECONDS = Histogram("qs_request_seconds", "HTTP request latency", ["route"])
QUERIES = Counter("qs_queries_total", "Queries by terminal status", ["status"])
QUERY_ATTEMPTS = Histogram("qs_query_attempts", "SQL attempts per query", buckets=(1, 2, 3))
POLICY_REJECTIONS = Counter("qs_policy_rejections_total", "SQL policy rejections", ["rule"])
SELF_HEAL_RECOVERIES = Counter("qs_selfheal_recoveries_total", "Recovered queries")
DB_SECONDS = Histogram("qs_db_exec_seconds", "Database execution latency", ["datasource"])
DB_ROWS = Histogram("qs_db_rows_returned", "Rows returned", buckets=(0, 1, 10, 100, 1000))
LLM_SECONDS = Histogram("qs_llm_latency_seconds", "LLM latency", ["prompt", "version"])
LLM_CALLS = Counter("qs_llm_calls_total", "LLM calls", ["prompt", "version", "outcome"])
LLM_TOKENS = Counter("qs_llm_tokens_total", "LLM tokens", ["type"])
RATE_LIMITED = Counter("qs_rate_limited_total", "Rate-limited requests")
CACHE = Counter("qs_schema_cache_total", "Schema cache accesses", ["result"])
JOB_QUEUE_DEPTH = Gauge("qs_job_queue_depth", "Queued jobs")
DEADLINES = Counter("qs_deadline_exceeded_total", "Exceeded request deadlines")
AUDIT_FAILURES = Counter("qs_audit_write_failures_total", "Audit persistence failures")
