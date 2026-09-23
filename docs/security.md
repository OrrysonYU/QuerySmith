# Security

The model is untrusted. SQL passes through independent controls: prompt guidance (advisory),
SQLGlot parsing/single-SELECT classification, CTE-aware table/column/function authorization,
LIMIT/cost/resource gates, and a server-enforced read-only database role. Existing-but-forbidden
objects are terminal security blocks and never enter repair.

Other controls include Argon2id API-key hashes, constant-time lookup verification, per-key rate
limits, ownership-scoped 404 responses, permission filtering before schema selection, bounded model
calls/tokens/attempts/deadlines, structured outputs, delimited prompt data, allowlist-only logs,
ownership-checked chart files, fixed Plotly rendering, and append-only audit/event interfaces.

The deterministic suite covers 60 SQL evasions, destructive/multi-statement SQL, catalog and
function probing, qualified and unqualified blocked columns, prompt and poisoned-cell strings, log
secret removal, cross-user jobs, token exhaustion, chart-title injection, executor caps, and rate
limits. Live-model poisoned-cell behavior and real PostgreSQL role enforcement remain explicit
external validation items.
