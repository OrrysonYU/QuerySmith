"""Public QuerySmith API client; imports no backend internals."""

from typing import Any

import httpx


class QuerySmithClient:
    def __init__(
        self, base_url: str, api_key: str, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url, headers={"X-API-Key": api_key}, timeout=30, transport=transport
        )

    def close(self) -> None:
        self._client.close()

    def ask(self, question: str, mode: str = "async") -> dict[str, Any]:
        response = self._client.post("/api/v1/chat", json={"question": question, "mode": mode})
        response.raise_for_status()
        return response.json()

    def query(self, query_id: str) -> dict[str, Any]:
        response = self._client.get(f"/api/v1/queries/{query_id}")
        response.raise_for_status()
        return response.json()

    def events(self, query_id: str, after: int = 0) -> dict[str, Any]:
        response = self._client.get(f"/api/v1/queries/{query_id}/events", params={"after": after})
        response.raise_for_status()
        return response.json()

    def cancel(self, query_id: str) -> dict[str, Any]:
        response = self._client.post(f"/api/v1/queries/{query_id}/cancel")
        response.raise_for_status()
        return response.json()
