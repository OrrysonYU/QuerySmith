"""GLM adapter using its OpenAI-compatible API contract."""

from querysmith.llm.adapters.openai_compat import OpenAICompatibleAdapter


class GlmAdapter(OpenAICompatibleAdapter):
    """Named adapter retained for provider-specific configuration and future quirks."""
