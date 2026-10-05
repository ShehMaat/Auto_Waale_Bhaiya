from typing import List, Type

import openai
from openai.types.chat import ChatCompletionMessageParam

from packages.config.settings import settings
from packages.llm.provider import LLMProvider, T


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"
        self.embed_model = "text-embedding-3-small"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "sk-placeholder":
            return "MOCK_RESPONSE"

        messages: List[ChatCompletionMessageParam] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return response.choices[0].message.content or ""

    def generate_structured(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "sk-placeholder":
            # Return a mock instance of the schema for testing
            # Since T is a BaseModel, we can cast it to satisfy mypy
            from typing import cast

            return cast(T, schema.model_construct())  # type: ignore[attr-defined]

        messages: List[ChatCompletionMessageParam] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=schema,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Failed to parse response")
        return parsed

    def embed(self, text: str) -> List[float]:
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "sk-placeholder":
            return [0.0] * 1536

        response = self.client.embeddings.create(input=text, model=self.embed_model)
        return response.data[0].embedding
