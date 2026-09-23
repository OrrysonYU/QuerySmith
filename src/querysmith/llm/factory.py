"""Configured LLM client factory."""

from querysmith.core.config import LLMSettings
from querysmith.llm.adapters.glm import GlmAdapter
from querysmith.llm.adapters.openai_compat import OpenAICompatibleAdapter
from querysmith.llm.client import LLMClient
from querysmith.llm.prompts.registry import PromptRegistry


def build_llm_client(settings: LLMSettings, prompts: PromptRegistry) -> LLMClient:
    if settings.provider == "mock":
        raise ValueError("mock client must be explicitly scripted by the caller")
    if settings.api_key is None or settings.base_url is None:
        raise ValueError("LLM API key and base URL are required")
    adapter = GlmAdapter if settings.provider == "glm" else OpenAICompatibleAdapter
    return adapter(
        base_url=settings.base_url,
        api_key=settings.api_key.get_secret_value(),
        model=settings.model,
        prompts=prompts,
        timeout=settings.timeout_seconds,
    )
