# ADR-006: LLM Provider Abstraction

## Context
Relying heavily on a single LLM provider (e.g., OpenAI) creates vendor lock-in and limits flexibility if better or cheaper models emerge.

## Decision
We will use an abstraction layer (via LangChain/LangGraph abstractions or custom interfaces) that supports multiple providers (OpenAI, Google Gemini, Anthropic).

## Consequences
- Prompts must be designed to be generally robust across models.
- Avoids tying the architecture strictly to proprietary API features (like specific OpenAI tool calling quirks) without a fallback.
