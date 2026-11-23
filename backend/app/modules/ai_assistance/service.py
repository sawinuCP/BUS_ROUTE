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

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.modules.ai_assistance.facts import FactsBundle, build_facts_bundle
from app.modules.ai_assistance.prompts import (
    CLASSIFICATION_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_classification_user_message,
    build_user_message,
)
from app.modules.ai_assistance.providers import (
    ProviderConfigError,
    ProviderError,
    create_provider,
)
from app.modules.ai_assistance.validation import (
    ValidatedClassification,
    ValidatedExplanation,
    ValidationFailure,
    validate_classification_output,
    validate_model_output,
)
from app.modules.reports import REPORT_CATEGORIES
from app.platform.rate_limit import SlidingWindowLimiter, get_rate_limiter, reset_rate_limiters

AI_NOTE = (
    "AI-generated explanation, grounded only in the plan facts shown above —"
    " always follow the step instructions themselves."
)
FALLBACK_NOTE = "Built-in deterministic explanation (no AI was used)."
ENGLISH_NOTE = "Explanations are English-only until native review (D-7)."

# Phase 9: the limiter moved to the shared platform infrastructure
# (app.platform.rate_limit) so AI calls and report submissions share one
# mechanism. Thin wrappers keep the existing call sites and tests stable.


def get_limiter(settings: Any) -> SlidingWindowLimiter:
    """The AI namespace's shared limiter (Phase 9 infrastructure)."""
    return get_rate_limiter("ai", settings)


def reset_limiter() -> None:
    """Compatibility alias for the tests (resets all namespaces)."""
    reset_rate_limiters()


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
    require_entity = mode == "explain_step" and bool(
        bundle.allowed_route_codes or bundle.allowed_stop_names
    )
    return validate_model_output(completion.text, bundle, require_entity_mention=require_entity)


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


# --------------------------------------------------------------------------- #
# Report classification suggestions (item 5 — human decides, AI suggests)
# --------------------------------------------------------------------------- #

CLASSIFICATION_NOTE = (
    "AI category suggestion for the moderation queue — a human moderator"
    " decides; nothing about the report changes automatically."
)
KEYWORD_NOTE = "Keyword-based suggestion (no AI was used); a human moderator decides."


@dataclass(frozen=True)
class ClassificationResult:
    suggested_category: str
    rationale: str
    source: str  # "ai" | "deterministic_fallback"
    provider: str | None
    model: str | None
    notes: tuple[str, ...]

    def serialize(self) -> dict[str, Any]:
        return {
            "suggested_category": self.suggested_category,
            "rationale": self.rationale,
            "source": self.source,
            "provider": self.provider,
            "model": self.model,
            "notes": list(self.notes),
        }


_CATEGORY_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("fare", "fare"),
    ("price", "fare"),
    ("ticket", "fare"),
    ("charged", "fare"),
    ("conductor", "fare"),
    ("step-free", "access_attribute"),
    ("wheelchair", "access_attribute"),
    ("ramp", "access_attribute"),
    ("shelter", "access_attribute"),
    ("accessib", "access_attribute"),
    ("wrong stop", "wrong_stop"),
    ("different stop", "wrong_stop"),
    ("opposite side", "wrong_stop"),
    ("stop location", "wrong_stop"),
    ("not this stop", "wrong_stop"),
    ("direction", "direction"),
    ("headsign", "direction"),
    ("opposite way", "direction"),
    ("wrong way", "direction"),
    ("transfer", "transfer_path"),
    ("change buses", "transfer_path"),
    ("walk between", "transfer_path"),
    ("outdated", "outdated_data"),
    ("no longer", "outdated_data"),
    ("closed", "outdated_data"),
    ("variant", "route_variant"),
    ("pattern", "route_variant"),
    ("different route", "route_variant"),
    ("landmark", "landmark_name"),
    ("name is wrong", "landmark_name"),
    ("renamed", "landmark_name"),
)


def _deterministic_classification(description: str) -> ValidatedClassification:
    """Keyword-based fallback classifier — honest, rule-based, no AI."""
    lowered = description.lower()
    for keyword, category in _CATEGORY_KEYWORDS:
        if keyword in lowered:
            rationale = (
                f"Keyword-based suggestion: the report mentions '{keyword}',"
                f" which maps to the '{category}' category. A human moderator"
                " decides."
            )
            return ValidatedClassification(category, rationale)
    rationale = (
        "Keyword-based suggestion: no category keyword matched the report"
        " text, so 'other' is the honest default. A human moderator decides."
    )
    return ValidatedClassification("other", rationale)


def _classification_fallback(description: str, note: str) -> ClassificationResult:
    fallback = _deterministic_classification(description)
    return ClassificationResult(
        suggested_category=fallback.suggested_category,
        rationale=fallback.rationale,
        source="deterministic_fallback",
        provider=None,
        model=None,
        notes=(note, KEYWORD_NOTE),
    )


async def _generate_classification(
    provider: Any, report: dict[str, Any], categories: Sequence[str]
) -> ValidatedClassification:
    completion = await provider.complete(
        CLASSIFICATION_SYSTEM_PROMPT, build_classification_user_message(categories, report)
    )
    return validate_classification_output(completion.text, categories)


async def suggest_classification(
    report: dict[str, Any],
    settings: Any,
    client_key: str,
    provider: Any | None = None,
) -> ClassificationResult:
    """Suggest a category for one traveller report (item 5).

    **Suggestion only** — the caller must never apply it to the report row;
    a human moderator decides. Same contract as `explain`: enabled flag,
    throttle, provider, validated structured output, deterministic fallback
    on any failure.
    """
    description = str(report.get("description") or "")

    if not settings.ai_explanations_enabled:
        return _classification_fallback(
            description, "AI suggestions are turned off in this deployment."
        )

    if not get_limiter(settings).allow(client_key):
        return _classification_fallback(description, "AI suggestions are rate-limited right now.")

    if provider is None:
        try:
            provider = create_provider(settings)
        except ProviderConfigError as exc:
            return _classification_fallback(description, f"AI unavailable: {exc}")

    try:
        validated = await _generate_classification(provider, report, list(REPORT_CATEGORIES))
    except (ProviderError, ValidationFailure) as exc:
        return _classification_fallback(description, f"AI unavailable: {exc}")

    return ClassificationResult(
        suggested_category=validated.suggested_category,
        rationale=validated.rationale,
        source="ai",
        provider=getattr(provider, "name", "unknown"),
        model=getattr(provider, "model", None),
        notes=(CLASSIFICATION_NOTE, ENGLISH_NOTE),
    )
