# Deployment

Local Compose defines the app database, seeded Chinook-like PostgreSQL source, API, and UI. API and
UI images run as non-root users; the production override drops capabilities, sets no-new-privileges,
uses a read-only filesystem with tmpfs, enables restarts, and health-checks the API. Secrets come
from environment/platform secret stores and are never baked into images.

Release order: provision secrets → run `alembic upgrade head` → deploy API → wait for readiness →
deploy UI. Roll back by immutable image version; migrations follow additive/expand-contract rules.
Prometheus configuration and alert rules cover error rate, policy spikes, deadlines, queue depth,
and audit failures. `scripts/backup_verify.sh` restores a dump only into an explicitly supplied
isolated target and verifies migration metadata.

Docker builds, Compose startup, live readiness, alert firing, and the restore drill require an
environment with Docker/PostgreSQL and are not claimed as executed here.
