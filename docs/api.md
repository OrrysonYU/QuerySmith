# API

All routes are versioned under `/api/v1`; query routes require `X-API-Key`. Every response receives
`X-Request-Id`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and a no-referrer policy.
Cross-user query access returns 404 to avoid existence leaks.

- `POST /api/v1/chat` — creates a durable job; `mode=auto` waits for a bounded interval, `async`
  returns immediately. Optional idempotency key and conversation ID are persisted.
- `GET /api/v1/queries/{id}` — ownership-checked status and terminal result.
- `GET /api/v1/queries/{id}/events?after=N` — cursor-based safe trace events; no prompts or rows.
- `POST /api/v1/queries/{id}/cancel` — idempotent cancellation request.
- `GET /api/v1/queries/{id}/chart` — ownership-checked chart artifact with restrictive CSP.
- `GET /api/v1/schema` — permission-filtered catalog view.
- `GET /api/v1/health` — process liveness.
- `GET /api/v1/readiness` — app DB, data source, and LLM configuration checks.
- `GET /metrics` — Prometheus exposition.

All errors, including authentication and request validation, use:

```json
{"error":{"code":"UNAUTHENTICATED","message":"Unauthenticated","request_id":"req_...","details":{}}}
```
