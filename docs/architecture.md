# Architecture

QuerySmith treats every LLM output as untrusted data. The enforced path is user → typed model
output → SQL parser → authorization policy → capped read-only executor → result validation → typed
analysis → deterministic response. Security-blocked SQL is terminal and never enters repair.

The Level-1 topology uses FastAPI, a bounded state machine, PostgreSQL control-plane persistence,
SQLGlot policy checks, a provider-neutral LLM client, and fixed Plotly renderers. Redis, brokers,
model-generated code, autonomous tool calling, and multi-tenancy are intentionally excluded.
