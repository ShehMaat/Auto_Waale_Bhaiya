from packages.llm.gemini import GeminiProvider
from packages.llm.openai import OpenAIProvider


def test_llm_providers() -> None:  # type: ignore[no-untyped-def]
    openai = OpenAIProvider()
    gemini = GeminiProvider()
    assert openai.generate("test") == "dummy"
    assert gemini.generate("test") == "dummy"
