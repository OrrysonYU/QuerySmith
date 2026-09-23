from pathlib import Path

from querysmith.llm.client import PromptRef
from querysmith.llm.prompts.registry import PromptRegistry


def test_prompt_variables_do_not_execute_as_templates() -> None:
    rendered = PromptRegistry(Path("prompts")).render(
        PromptRef("interpret_question", 1), {"question": "{{ 7 * 7 }}", "conversation_summary": ""}
    )
    assert "{{ 7 * 7 }}" in rendered.user
    assert "49" not in rendered.user
