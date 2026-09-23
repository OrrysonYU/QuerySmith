# QuerySmith

QuerySmith is a production-oriented, self-healing SQL data analyst. It treats every LLM output as
untrusted and places generated SQL inside a deterministic execution envelope: parse, authorize,
cap, execute through a read-only role, validate results, and only then analyze and visualize.

## Trust path

```text
User → typed LLM intent/SQL → SQLGlot parser → policy authorization
     → timeout/row/byte-capped read-only executor → shape validation
     → adversarial semantic critic → typed analysis/chart spec → trusted renderer
```

Security-blocked SQL is terminal and is never repaired. Repair attempts are limited to three,
normalized SQL hashes must be unique, resource and semantic retries have independent budgets, and
an absolute request deadline is authoritative.

## Current evidence

The deterministic local suite covers configuration, authentication primitives, SQL policy,
adversarial SQL, prompt boundaries, LangGraph routes, retry termination, executor caps, caching,
jobs, API contracts, evaluation metrics, and visualization. PostgreSQL, Docker, live-model,
OpenTelemetry-exporter, backup-restore, and deployment evidence is intentionally reported
separately in [`docs/readiness-review.md`](docs/readiness-review.md).

## Development

Requirements: Python 3.12+ and, for live integration, Docker with PostgreSQL 16.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
```

Quality gates:

```bash
pytest
ruff check .
ruff format --check .
mypy src/
alembic upgrade head --sql > /tmp/querysmith-migration.sql
```

Local stack when Docker is available:

```bash
docker compose up --build
alembic upgrade head
QS_BOOTSTRAP_ADMIN_NAME=admin python scripts/bootstrap_admin.py
```

The bootstrap key is printed once. Store it in a secret manager; it cannot be recovered later.

## Main components

- `src/querysmith/agent`: bounded LangGraph, typed state, repair, budgets, durable runner
- `src/querysmith/policy`: SQL parser, authorization, function controls, LIMIT and cost gates
- `src/querysmith/execution`: data-source registry, pools, streaming executor, cancellation boundary
- `src/querysmith/schema_intel`: introspection, versioned catalog, drift handling, secure retrieval
- `src/querysmith/llm`: provider-neutral client, GLM/OpenAI-compatible adapters, prompt registry
- `src/querysmith/api`: authenticated versioned API, job/status/event/cancel/schema/chart endpoints
- `src/querysmith/observability`: safe logs, Prometheus metrics, OTel spans, append-only audit/events
- `eval`: 60-question + 15-adversarial benchmark and measured report generation
- `infra`: non-root containers, production override, PostgreSQL seed/roles, monitoring/alerts

## Documentation

- [Architecture](docs/architecture.md)
- [Security](docs/security.md)
- [API](docs/api.md)
- [Database](docs/database.md)
- [Agent workflow](docs/agent-workflow.md)
- [Evaluation](docs/evaluation.md)
- [Deployment](docs/deployment.md)
- [Runbook](docs/runbook.md)
- [Implementation status](docs/implementation-status.md)
