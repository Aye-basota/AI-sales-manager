import logging
from typing import Any

import httpx

from app.config import get_settings
from app.llm.guardrails import evaluate_guardrails

logger = logging.getLogger(__name__)

DEFAULT_MODELS = [
    "qwen-2.5-72b-instruct",
    "gemini-2.5-flash-preview-05-20",
    "deepseek-chat",
]

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

FALLBACK_TEXT = "Извините, не совсем понял, могу ли я уточнить..."


class LLMEngine:
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = base_url or OPENROUTER_BASE_URL
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
        return self._client

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> dict[str, Any]:
        target_model = model or DEFAULT_MODELS[0]
        payload = {
            "model": target_model,
            "messages": messages,
        }

        response = await self.client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        content = choice["message"]["content"]
        usage = data.get("usage", {})

        return {
            "text": content.strip(),
            "model": data.get("model", target_model),
            "tokens_used": usage.get("total_tokens", 0),
        }

    async def generate_with_fallback(
        self,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        last_exception: Exception | None = None
        for model in DEFAULT_MODELS:
            try:
                return await self.generate(messages, model=model)
            except Exception as exc:
                logger.warning("LLM call failed for model %s: %s", model, exc)
                last_exception = exc
        raise last_exception or RuntimeError("All LLM models failed")

    async def generate_response_with_guardrails(
        self,
        messages: list[dict[str, str]],
        last_messages: list[str],
        max_retries: int = 2,
    ) -> dict[str, Any]:
        current_messages = list(messages)
        strict_reminder = {
            "role": "system",
            "content": (
                "ВАЖНО: Не используй markdown, списки, жирный шрифт. "
                "Пиши plain text. Не признавайся, что ты бот или ИИ."
            ),
        }

        for attempt in range(max_retries + 1):
            result = await self.generate_with_fallback(current_messages)
            text = result["text"]
            gr = evaluate_guardrails(text, last_messages)

            if gr.approved:
                return result

            logger.warning(
                "Guardrails rejected response (attempt %d/%d): violations=%s",
                attempt + 1,
                max_retries + 1,
                gr.violations,
            )

            if attempt < max_retries:
                # Inject strict reminder only once
                if not any(
                    m.get("content") == strict_reminder["content"]
                    for m in current_messages
                ):
                    current_messages = current_messages + [strict_reminder]

        return {
            "text": FALLBACK_TEXT,
            "model": "fallback",
            "tokens_used": 0,
        }

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
