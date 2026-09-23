"""Strict versioned prompt templates."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined

from querysmith.llm.client import PromptRef


@dataclass(frozen=True)
class RenderedPrompt:
    system: str
    user: str


class PromptRegistry:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._environment = Environment(undefined=StrictUndefined, autoescape=True)

    def render(self, ref: PromptRef, variables: dict[str, Any]) -> RenderedPrompt:
        path = self._root / ref.name / f"v{ref.version}.txt"
        source = path.read_text(encoding="utf-8")
        system, separator, user = source.partition("\n---\n")
        if not separator:
            raise ValueError(f"Invalid prompt file: {path}")
        return RenderedPrompt(
            self._environment.from_string(system).render(**variables),
            self._environment.from_string(user).render(**variables),
        )
