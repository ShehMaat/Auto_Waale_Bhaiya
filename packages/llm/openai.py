from typing import Any

from .provider import LLMProvider


class OpenAIProvider(LLMProvider):
    def generate(self, prompt: str) -> str:  # type: ignore[override]
        return "dummy"

    def generate_structured(self, prompt: str, schema: Any) -> Any:  # type: ignore[override]
        return {}

    def embed(self, text: str) -> list[float]:
        return [0.0]
