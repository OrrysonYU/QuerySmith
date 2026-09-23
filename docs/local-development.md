# Local development

Create `.env` from `.env.example`, install `.[dev]`, and run quality gates from README. With Docker
available, `docker compose up --build` starts the app database, a seeded Chinook-like PostgreSQL
source, and the API. The data-source role is read-only by server policy.
