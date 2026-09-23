FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
COPY prompts ./prompts
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts
RUN pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.12-slim
RUN groupadd --system querysmith && useradd --system --gid querysmith --home /app querysmith
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
USER querysmith
EXPOSE 8000
CMD ["uvicorn", "querysmith.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
