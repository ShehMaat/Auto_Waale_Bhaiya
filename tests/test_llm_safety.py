import pytest

from packages.llm.provider import LLMProvider


class MockLLMProvider(LLMProvider):
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        # Mock safety check: reject malicious prompt
        if "os.system" in prompt or "DROP TABLE" in prompt:
            raise ValueError("Malicious prompt detected")
        return "Safe response"

    def generate_structured(self, prompt: str, schema, system_prompt: str = ""):  # type: ignore[no-untyped-def]
        pass

    def embed(self, text: str) -> list[float]:
        return [0.0] * 1536


def test_llm_safety_rejection() -> None:  # type: ignore[no-untyped-def]
    provider = MockLLMProvider()

    with pytest.raises(ValueError, match="Malicious prompt detected"):
        provider.generate("Write a script using os.system('rm -rf /')")


def test_llm_safe_prompt() -> None:  # type: ignore[no-untyped-def]
    provider = MockLLMProvider()
    response = provider.generate("What is 2+2?")
    assert response == "Safe response"
