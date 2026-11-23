"""Explanation service (Phase 8 items 3, 6–8).

Flow for every request:

1. build the facts bundle (coordinates/PII stripped);
2. if AI is enabled and the per-client throttle allows, call the provider
   (adapter chosen by the settings-driven factory) and validate the output
   against the bundle;
3. on ANY failure — outage, timeout, refusal, misconfiguration, invalid or
   ungrounded output — serve the deterministic template instead. The caller
   always gets a 200 with an honest `source` marker; planning never depends
   on AI (exit criterion: "AI is optional and never required").
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from app.modules.ai_assistance.facts import FactsBundle, build_facts_bundle
from app.modules.ai_assistance.prompts import SYSTEM_PROMPT, build_user_message
from app.modules.ai_assistance.providers import (
    ProviderConfigError,
    ProviderError,
    create_provider,
)
from app.modules.ai_assistance.validation import (
    ValidatedExplanation,
    ValidationFailure,
    validate_model_output,
)

AI_NOTE = (
    "AI-generated explanation, grounded only in the plan facts shown above —"
    " always follow the step instructions themselves."
)
FALLBACK_NOTE = "Built-in deterministic explanation (no AI was used)."
ENGLISH_NOTE = "Explanations are English-only until native review (D-7)."


class SlidingWindowLimiter:
    """Tiny per-key sliding-window limiter (cost control, item 8).

    Good enough for Phase 8; Phase 9 replaces it with the shared
    rate-limiting infrastructure.
    """

    def __init__(self, max_per_minute: int) -> None:
        self._max = max_per_minute
        self._events: dict[str, deque[float]] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        window = self._events.setdefault(key, deque())
        while window and current - window[0] > 60.0:
            window.popleft()
        if len(window) >= self._max:
            return False
        window.append(current)
        return True


_limiter: SlidingWindowLimiter | None = None


def get_limiter(settings: Any) -> SlidingWindowLimiter:
    """Process-wide limiter (monkeypatchable in tests)."""
    global _limiter  # noqa: PLW0603
    if _limiter is None:
        _limiter = SlidingWindowLimiter(settings.ai_requests_per_minute)
    return _limiter


@dataclass(frozen=True)
class ExplanationResult:
    mode: str
    source: str  # "ai" | "deterministic_fallback"
    provider: str | None
    model: str | None
    explanation: str
    cites: tuple[str, ...]
    dataset_version: str | None
    notes: tuple[str, ...]

    def serialize(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "source": self.source,
            "provider": self.provider,
            "model": self.model,
            "explanation": self.explanation,
            "cites": list(self.cites),
            "dataset_version": self.dataset_version,
            "notes": list(self.notes),
            "language": "en",
        }


def _deterministic_explain_step(bundle: FactsBundle) -> str:
    step = bundle.facts["f_step"]
    summary = bundle.facts["f_summary"]
    duration = summary.get("estimated_duration_minutes") or {}
    parts = [
        f"This step: {step.get('text')}",
        "Its verification state in the current dataset is"
        f" '{step.get('confidence')}' — treat the on-screen wording as the"
        " authoritative instruction.",
        f"The whole journey is about {duration.get('min')}–{duration.get('max')}"
        f" minutes with {(summary.get('walking_distance_m') or 0)} m of walking"
        f" and {summary.get('transfer_count')} transfer(s).",
    ]
    warnings = bundle.facts["f_context"].get("warnings") or []
    if warnings:
        parts.append(f"Watch out for: {'; '.join(str(w) for w in warnings)}.")
    parts.append(
        "Everything here comes from the mapped dataset — no timetable, fare"
        " or live-availability claim is made."
    )
    return " ".join(parts)


def _deterministic_why_route(bundle: FactsBundle) -> str:
    summary = bundle.facts["f_summary"]
    context = bundle.facts["f_context"]
    labels = context.get("labels") or []
    duration = summary.get("estimated_duration_minutes") or {}
    parts = [
        "This option was returned by the deterministic planner because it is"
        " network-feasible on the mapped data: about"
        f" {duration.get('min')}–{duration.get('max')} minutes,"
        f" {(summary.get('walking_distance_m') or 0)} m of walking,"
        f" {summary.get('transfer_count')} transfer(s), confidence"
        f" '{summary.get('confidence')}'.",
        f"It uses {' and '.join(str(label) for label in labels)}." if labels else "",
    ]
    warnings = context.get("warnings") or []
    if warnings:
        parts.append(f"It carries warnings: {'; '.join(str(w) for w in warnings)}.")
    parts.append(
        "Alternatives are other feasible combinations of routes and walking;"
        " the planner does not use timetables, fares or live data, so"
        " 'fastest' means the shortest estimated travel time, not a"
        " scheduled arrival."
    )
    return " ".join(part for part in parts if part)


def reset_limiter() -> None:
    """Reset the process-wide limiter (tests)."""
    global _limiter  # noqa: PLW0603
    _limiter = None


def _fallback(
    bundle: FactsBundle, mode: str, note: str, *, step_index: int | None
) -> ExplanationResult:
    del step_index
    explanation = (
        _deterministic_explain_step(bundle)
        if mode == "explain_step"
        else _deterministic_why_route(bundle)
    )
    return ExplanationResult(
        mode=mode,
        source="deterministic_fallback",
        provider=None,
        model=None,
        explanation=explanation,
        cites=(),
        dataset_version=bundle.dataset_version,
        notes=(note, FALLBACK_NOTE, ENGLISH_NOTE),
    )


async def _generate(provider: Any, bundle: FactsBundle, mode: str) -> ValidatedExplanation:
    completion = await provider.complete(SYSTEM_PROMPT, build_user_message(bundle, mode))
    return validate_model_output(completion.text, bundle)


async def explain(
    payload: dict[str, Any],
    mode: str,
    option_index: int,
    step_index: int | None,
    settings: Any,
    client_key: str,
    provider: Any | None = None,
) -> ExplanationResult:
    """Produce one grounded explanation (AI when available, else fallback)."""
    bundle = build_facts_bundle(payload, option_index, step_index)

    if not settings.ai_explanations_enabled:
        return _fallback(
            bundle,
            mode,
            "AI explanations are turned off in this deployment.",
            step_index=step_index,
        )

    if not get_limiter(settings).allow(client_key):
        return _fallback(
            bundle,
            mode,
            "AI explanations are rate-limited right now.",
            step_index=step_index,
        )

    if provider is None:
        try:
            provider = create_provider(settings)
        except ProviderConfigError as exc:
            return _fallback(bundle, mode, f"AI unavailable: {exc}", step_index=step_index)

    try:
        validated = await _generate(provider, bundle, mode)
    except (ProviderError, ValidationFailure) as exc:
        return _fallback(bundle, mode, f"AI unavailable: {exc}", step_index=step_index)

    return ExplanationResult(
        mode=mode,
        source="ai",
        provider=getattr(provider, "name", "unknown"),
        model=getattr(provider, "model", None),
        explanation=validated.explanation,
        cites=validated.cites,
        dataset_version=bundle.dataset_version,
        notes=(AI_NOTE, ENGLISH_NOTE),
    )
