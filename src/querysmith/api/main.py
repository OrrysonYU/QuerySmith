"""Configured ASGI entry point."""

from querysmith.api.app import create_app
from querysmith.api.bootstrap import build_runtime

runtime = build_runtime()
app = create_app(runtime.services)
