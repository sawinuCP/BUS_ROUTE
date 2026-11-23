"""Provider-neutral AI adapters and the settings-driven factory (Phase 8 item 1).

The factory maps `AI_PROVIDER` from the environment onto an adapter:

- `openai_compatible` — any OpenAI-compatible chat endpoint (CommandCode,
  OpenAI, vLLM, …): base URL, model name and API key come from the
  environment (`AI_BASE_URL`, `AI_MODEL`, `AI_API_KEY`), so switching models
  is a config change, never a code change.
- `none` — disabled: the feature degrades to the deterministic explanations
  (the default, so local runs and tests need no key or network).

New providers are added by registering another factory function in
`PROVIDER_FACTORIES` and widening the `Settings.ai_provider` literal — the
rest of the module is provider-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class ProviderError(RuntimeError):
    """The provider failed (outage, timeout, refusal, bad response)."""


class ProviderConfigError(ProviderError):
    """The provider is misconfigured (missing base URL, model or key)."""


@dataclass(frozen=True)
class ProviderCompletion:
    """One completed generation, tagged with the adapter that produced it."""

    text: str
    provider: str
    model: str


class AIProvider(Protocol):
    """What every adapter must expose (provider-neutral, item 1)."""

    name: str
    model: str

    async def complete(self, system: str, user: str) -> ProviderCompletion:
        """Return the model's completion for one system/user message pair."""
        ...


class DisabledProvider:
    """AI disabled (`AI_PROVIDER=none`): every request fails fast.

    The service layer catches the error and serves the deterministic
    explanation — AI stays optional and never required (exit criterion).
    """

    name = "none"
    model = "none"

    async def complete(self, system: str, user: str) -> ProviderCompletion:
        del system, user
        raise ProviderError("AI provider is disabled (AI_PROVIDER=none)")


class OpenAICompatibleProvider:
    """Adapter for any OpenAI-compatible `/chat/completions` endpoint.

    Talks HTTP directly (no LLM SDK in domain code). Temperature 0 and a
    hard token cap keep explanations cheap and near-deterministic; the
    grounding contract is enforced downstream by `validation.py`, not here.
    """

    name = "openai_compatible"

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        timeout_seconds: float = 20.0,
        max_output_tokens: int = 600,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not base_url.strip():
            raise ProviderConfigError("AI_BASE_URL is required for AI_PROVIDER=openai_compatible")
        if not base_url.startswith(("http://", "https://")):
            raise ProviderConfigError("AI_BASE_URL must be an http(s) URL")
        if not model.strip():
            raise ProviderConfigError("AI_MODEL is required for AI_PROVIDER=openai_compatible")
        if not api_key.strip():
            raise ProviderConfigError(
                "AI_API_KEY is required for AI_PROVIDER=openai_compatible"
                " (set it in the environment or .env — never committed)"
            )
        self.model = model.strip()
        self._base_url = base_url.strip().rstrip("/")
        self._api_key = api_key.strip()
        self._timeout_seconds = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._transport = transport  # injectable for tests (default: real HTTP)

    async def complete(self, system: str, user: str) -> ProviderCompletion:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.0,
            "max_tokens": self._max_output_tokens,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds, transport=self._transport
            ) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions", json=payload, headers=headers
                )
        except httpx.TimeoutException as exc:
            raise ProviderError(f"AI provider timed out after {self._timeout_seconds}s") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"AI provider unreachable: {type(exc).__name__}") from exc

        if response.status_code != 200:
            # Never log the body: it can echo the key or prompt content.
            raise ProviderError(f"AI provider returned HTTP {response.status_code}")
        try:
            data = response.json()
            text = str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("AI provider response did not match the expected shape") from exc
        if not text.strip():
            raise ProviderError("AI provider returned an empty completion")
        return ProviderCompletion(text=text, provider=self.name, model=self.model)


def _make_openai_compatible(settings: Any) -> AIProvider:
    return OpenAICompatibleProvider(
        base_url=settings.ai_base_url,
        model=settings.ai_model,
        api_key=settings.ai_api_key,
        timeout_seconds=settings.ai_timeout_seconds,
        max_output_tokens=settings.ai_max_output_tokens,
    )


def _make_disabled(settings: Any) -> AIProvider:
    del settings
    return DisabledProvider()


PROVIDER_FACTORIES: dict[str, Any] = {
    "openai_compatible": _make_openai_compatible,
    "none": _make_disabled,
}


def create_provider(settings: Any) -> AIProvider:
    """Build the adapter named by `settings.ai_provider` (factory, item 1).

    Raises `ProviderConfigError` for an unknown provider name or a
    misconfigured adapter; the service layer treats that as "AI unavailable"
    and falls back to the deterministic explanation.
    """
    factory = PROVIDER_FACTORIES.get(settings.ai_provider)
    if factory is None:
        raise ProviderConfigError(
            f"Unsupported AI_PROVIDER '{settings.ai_provider}'."
            f" Supported: {sorted(PROVIDER_FACTORIES)}"
        )
    return factory(settings)
