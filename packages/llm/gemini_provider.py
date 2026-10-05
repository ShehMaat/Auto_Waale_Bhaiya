from typing import List, Type

import google.generativeai as genai

from packages.config.settings import settings
from packages.llm.provider import LLMProvider, T


class GeminiProvider(LLMProvider):
    def __init__(self) -> None:
        genai.configure(api_key=settings.GEMINI_API_KEY)  # type: ignore[attr-defined]
        self.model = genai.GenerativeModel("gemini-1.5-pro")  # type: ignore[attr-defined]
        self.embed_model = "models/embedding-001"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "AIza-placeholder":
            return "MOCK_RESPONSE"

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = self.model.generate_content(full_prompt)
        return str(response.text)

    def generate_structured(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "AIza-placeholder":
            from typing import cast

            return cast(T, schema.model_construct())  # type: ignore[attr-defined]

        # Using Gemini 1.5 JSON schema capabilities
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        response = self.model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                # Gemini currently expects json_schema dict, generating it from pydantic:
                response_schema=schema.model_json_schema(),  # type: ignore[attr-defined]
            ),
        )
        from typing import cast

        return cast(T, schema.model_validate_json(response.text))  # type: ignore[attr-defined]

    def embed(self, text: str) -> List[float]:
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "AIza-placeholder":
            return [
                0.0
            ] * 1536  # Note: Gemini typically returns 768 dims, but we standardized on 1536 in DB

        import google.generativeai as genai_module

        result = genai_module.embed_content(  # type: ignore[attr-defined]
            model=self.embed_model, content=text, task_type="retrieval_document"
        )
        # We need to pad to 1536 if we want to use the same DB column as OpenAI
        emb = result["embedding"]
        if len(emb) < 1536:
            emb.extend([0.0] * (1536 - len(emb)))
        return emb[:1536]
