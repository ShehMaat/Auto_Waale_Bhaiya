from abc import ABC, abstractmethod
from typing import List, Type, TypeVar

T = TypeVar("T")


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate text from prompt"""
        pass

    @abstractmethod
    def generate_structured(self, prompt: str, schema: Type[T], system_prompt: str = "") -> T:
        """Generate structured output conforming to a Pydantic schema"""
        pass

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Generate vector embeddings for text"""
        pass
