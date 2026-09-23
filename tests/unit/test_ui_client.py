import importlib.util
import json
from pathlib import Path

import httpx


def test_ui_client_uses_public_api_contract() -> None:
    spec = importlib.util.spec_from_file_location("ui_client", Path("ui/client.py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-API-Key"] == "key"
        assert request.url.path == "/api/v1/chat"
        return httpx.Response(
            200, content=json.dumps({"query_id": "q", "status": "QUEUED"}).encode()
        )

    client = module.QuerySmithClient("https://example.invalid", "key", httpx.MockTransport(handler))
    assert client.ask("question")["query_id"] == "q"
    client.close()
