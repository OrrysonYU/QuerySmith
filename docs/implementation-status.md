# QuerySmith implementation status

`COMPLETE` means repository implementation and locally executable acceptance checks are complete.
`IMPLEMENTED — RUNTIME VALIDATION PENDING` means the code, tests, and validation mechanism exist,
but this environment lacks the named external capability. No row below claims unexecuted evidence.

| Task | Status | Local evidence | External validation remaining |
|---|---|---|---|
| 01 Foundation | COMPLETE | Install, pytest, Ruff, MyPy | None |
| 02 Configuration | COMPLETE | Validation and secret tests | None |
| 03 Logging/errors/context | COMPLETE | Allowlist/log tests, typing | None |
| 04 CI | IMPLEMENTED — RUNTIME VALIDATION PENDING | Workflow static review | GitHub Actions run |
| 05 Compose/Chinook | IMPLEMENTED — RUNTIME VALIDATION PENDING | Compose/init artifacts | Docker/PG smoke and RO proof |
| 06 App DB/Alembic | IMPLEMENTED — RUNTIME VALIDATION PENDING | Offline migration SQL | PG up/down/round trips |
| 07 Data-source manager | IMPLEMENTED — RUNTIME VALIDATION PENDING | Typed lifecycle/health code | asyncpg/SQLite live checks |
| 08 Introspection | IMPLEMENTED — RUNTIME VALIDATION PENDING | Typed PK/FK/estimate implementation | Chinook snapshot on PG |
| 09 Catalog/cache/drift | COMPLETE | Cache/drift/enrichment tests | PG persistence round trip |
| 10 Controlled executor | COMPLETE | Timeout/row/byte tests | PG server cancellation proof |
| 11 SQL parser | COMPLETE | Structural/adversarial tests | None |
| 12 SQL authorization | COMPLETE | CTE/table/column/function/LIMIT tests | None |
| 13 SQL security suite | COMPLETE | 60-case corpus + regression suite | Real-PG end-to-end run |
| 14 Authentication | COMPLETE | Argon2, ownership, rate-limit/API tests | PG key repository integration |
| 15 LLM abstraction | COMPLETE | Mock + HTTP transport contract tests | Live GLM/provider call |
| 16 Prompt registry | COMPLETE | Strict rendering/injection tests | None |
| 17 Intent interpretation | COMPLETE | Typed LLM service and graph routes | Live-model quality |
| 18 Schema selection | COMPLETE | Permission-first retrieval + typed pruning | Live-model quality |
| 19 SQL generation | COMPLETE | Typed generation and policy boundary | Live-model quality |
| 20 LangGraph v1 | COMPLETE | Happy/blocked graph tests | Live data source |
| 21 Vertical API | COMPLETE | ASGI auth/chat/health tests | Configured PG/model stack |
| 22 Error classification | COMPLETE | Deterministic routing tests | None |
| 23 Repair node | COMPLETE | Memory/dedupe/budget tests | Live repair quality |
| 24 Full graph | COMPLETE | Terminal/security-route tests | Full-stack route run |
| 25 Shape validation | COMPLETE | Empty/top-N/null tests | None |
| 26 Semantic critic | COMPLETE | Typed critic service/routing | Live critic quality |
| 27 Analysis | COMPLETE | Typed analysis/caveat merge | Live-model quality |
| 28 Chart spec | COMPLETE | Compatibility/XSS/downgrade tests | None |
| 29 Plotly renderer | COMPLETE | Self-contained artifact test | Browser journey |
| 30 Durable runner | COMPLETE | Lifecycle/reconcile/cancel tests | PG job persistence run |
| 31 Query API | COMPLETE | Status/events/cancel/schema/ownership code | Full configured stack |
| 32 Audit/events | IMPLEMENTED — RUNTIME VALIDATION PENDING | Append-only APIs/type checks | PG order/failure tests |
| 33 OTel/metrics | IMPLEMENTED — RUNTIME VALIDATION PENDING | Metric/tracing implementation | Collector/dashboard evidence |
| 34 Streamlit UI | COMPLETE | Public-API client test | Docker/browser journeys |
| 35 Security hardening | COMPLETE | SQL, prompt, log, authz, budget, XSS tests | Live-model poisoned-cell run |
| 36 Evaluation | COMPLETE | 60+15 datasets, runner/report tests | Dated live baseline |
| 37 E2E | IMPLEMENTED — RUNTIME VALIDATION PENDING | Credential-gated journeys | Two consecutive live runs |
| 38 Documentation | COMPLETE | Docs synchronized with code | Stranger clean-clone walk-through |
| 39 Deployment hardening | IMPLEMENTED — RUNTIME VALIDATION PENDING | Images/override/alerts/backup script | Docker smoke, restore drill, alert fire |
| 40 Readiness review | COMPLETE | Evidence/gap review | PC verdict awaits pending evidence |
