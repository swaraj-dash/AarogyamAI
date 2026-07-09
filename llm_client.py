"""
LLM client abstraction.

Same rationale as embeddings.py: nothing in services/ or agents/ imports
google.generativeai directly. Everything talks to the `LLMClient`
interface, which means:
  - The whole agent graph is unit-testable with a scripted FakeLLMClient,
    with zero network calls and zero API key — that's how tests/ in this
    repo can run in a locked-down CI box.
  - `call_structured()` centralizes the "ask for JSON, parse it, retry once
    on a malformed response" pattern that was previously duplicated ad hoc
    across ai_engine.py in v1.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod

import config


class LLMClient(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, system: str = None) -> str:
        raise NotImplementedError

    def generate_json(self, prompt: str, system: str = None) -> dict:
        raw = self.generate_text(prompt, system=system)
        return _extract_json(raw)

    def call_structured(self, prompt: str, system: str = None, retries: int = 1) -> dict:
        """generate_json with one automatic repair retry on parse failure."""
        last_err = None
        for attempt in range(retries + 1):
            try:
                return self.generate_json(prompt, system=system)
            except (ValueError, json.JSONDecodeError) as e:
                last_err = e
                prompt = (
                    f"{prompt}\n\nYour previous response could not be parsed as JSON "
                    f"({e}). Respond with ONLY valid JSON, no markdown fences, no prose."
                )
        raise ValueError(f"LLM did not return valid JSON after {retries + 1} attempts: {last_err}")


def _extract_json(raw: str) -> dict:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


class GeminiLLMClient(LLMClient):
    def __init__(self, model: str = None, api_key: str = None):
        import google.generativeai as genai
        genai.configure(api_key=api_key or config.GOOGLE_API_KEY)
        self.model_name = model or config.LLM_MODEL
        self._model = genai.GenerativeModel(self.model_name)

    def generate_text(self, prompt: str, system: str = None) -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = self._model.generate_content(full_prompt)
        return response.text


class FakeLLMClient(LLMClient):
    """Scriptable stub for tests and offline demo mode.

    Usage:
        llm = FakeLLMClient(responses=["first reply", '{"a": 1}'])
        llm.generate_text(...) -> "first reply"
        llm.generate_text(...) -> '{"a": 1}'

    If `responses` is exhausted, falls back to `default_response` so a test
    that only cares about one call in a longer graph doesn't need to script
    every single node's output.
    """

    def __init__(self, responses: list[str] = None, default_response: str = '{"reply": "ok"}'):
        self._responses = list(responses or [])
        self._default = default_response
        self.calls: list[dict] = []

    def generate_text(self, prompt: str, system: str = None) -> str:
        self.calls.append({"prompt": prompt, "system": system})
        if self._responses:
            return self._responses.pop(0)
        return self._default


_llm_singleton: LLMClient | None = None


def get_llm() -> LLMClient:
    global _llm_singleton
    if _llm_singleton is not None:
        return _llm_singleton
    if config.OFFLINE_MODE:
        _llm_singleton = FakeLLMClient()
    else:
        _llm_singleton = GeminiLLMClient()
    return _llm_singleton
