from __future__ import annotations

import os
from typing import Protocol


class LLM(Protocol):
    def complete(self, prompt: str) -> str: ...


class MockLLM:
    """
    Local/dev-only model: returns a deterministic placeholder.
    Useful to prove your API + validation works before connecting a real LLM.
    """
    def complete(self, prompt: str) -> str:
        return (
            "I can answer after an LLM provider is connected.\n"
            "Citations: [STD-02]"
        )


def get_llm() -> LLM:
    """
    Factory: start with MockLLM.
    Later you can plug in OpenAI / Anthropic / local Ollama etc.
    """
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "mock":
        return MockLLM()

    raise RuntimeError(
        f"Unsupported LLM_PROVIDER={provider}. Use LLM_PROVIDER=mock for now."
    )
