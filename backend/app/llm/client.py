from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx

from app.core.config import Settings


class LLMClient:
    """OpenAI-compatible client for a locally hosted model (Ollama / llama.cpp).

    The system never requires this client: `available()` is checked before use and the caller
    falls back to the deterministic rules composer.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._available: bool | None = None
        self._checked_at = 0.0
        self.last_error: str | None = None

    def available(self) -> bool:
        if self._available is not None and time.time() - self._checked_at < 8:
            return self._available
        try:
            response = httpx.get(
                f"{self.settings.llm_base_url.rstrip('/')}/models",
                timeout=1.2,
                headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
            )
            self._available = response.status_code < 500
            self.last_error = None
        except Exception as exc:  # noqa: BLE001
            self._available = False
            self.last_error = str(exc)
        self._checked_at = time.time()
        return bool(self._available)

    def complete_json(self, system: str, user: str, temperature: float = 0.2) -> dict[str, Any] | None:
        if not self.available():
            return None
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": 1400,
            "stream": False,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        url = f"{self.settings.llm_base_url.rstrip('/')}/chat/completions"
        try:
            response = httpx.post(
                url, json=payload, headers=headers, timeout=self.settings.llm_timeout_s
            )
            if response.status_code == 400:
                payload.pop("response_format", None)
                response = httpx.post(
                    url, json=payload, headers=headers, timeout=self.settings.llm_timeout_s
                )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return _parse_json(content)
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            self._available = False
            return None


def _parse_json(content: str) -> dict[str, Any] | None:
    text = content.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                value = json.loads(text[start : end + 1])
                return value if isinstance(value, dict) else None
            except json.JSONDecodeError:
                return None
    return None
