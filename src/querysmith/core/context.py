"""Request-local context without global mutable state."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
query_id_var: ContextVar[str | None] = ContextVar("query_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


@contextmanager
def bind_request_context(
    *, request_id: str, query_id: str | None = None, user_id: str | None = None
) -> Iterator[None]:
    tokens = (
        (request_id_var, request_id_var.set(request_id)),
        (query_id_var, query_id_var.set(query_id)),
        (user_id_var, user_id_var.set(user_id)),
    )
    try:
        yield
    finally:
        for variable, token in reversed(tokens):
            variable.reset(token)
