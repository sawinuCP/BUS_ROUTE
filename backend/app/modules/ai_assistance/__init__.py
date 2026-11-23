"""Grounded AI assistance (Phase 8, plan items 1–3, 6–8).

Provider-neutral AI interface with a strict grounding contract:

- The domain code here depends on **no LLM SDK** — adapters talk HTTP
  (`providers.py`); the rest of the module works on plain facts.
- Only a **selected itinerary's facts** (no coordinates, no PII) are sent to
  the provider (`facts.py`).
- Every response is validated against a structured schema and the supplied
  fact IDs/entities (`validation.py`); anything invalid falls back to the
  deterministic templates (`service.py`). AI is optional and never required.
"""

from __future__ import annotations

from app.modules.ai_assistance.facts import FactsBundle, build_facts_bundle
from app.modules.ai_assistance.providers import (
    AIProvider,
    DisabledProvider,
    OpenAICompatibleProvider,
    ProviderCompletion,
    ProviderConfigError,
    ProviderError,
    create_provider,
)
from app.modules.ai_assistance.service import (
    CLASSIFICATION_NOTE,
    KEYWORD_NOTE,
    ClassificationResult,
    ExplanationResult,
    SlidingWindowLimiter,
    explain,
    get_limiter,
    reset_limiter,
    suggest_classification,
)
from app.modules.ai_assistance.validation import (
    ValidatedClassification,
    ValidatedExplanation,
    ValidationFailure,
    validate_classification_output,
    validate_model_output,
)

__all__ = [
    "AIProvider",
    "CLASSIFICATION_NOTE",
    "ClassificationResult",
    "DisabledProvider",
    "ExplanationResult",
    "FactsBundle",
    "KEYWORD_NOTE",
    "OpenAICompatibleProvider",
    "ProviderCompletion",
    "ProviderConfigError",
    "ProviderError",
    "SlidingWindowLimiter",
    "ValidatedClassification",
    "ValidatedExplanation",
    "ValidationFailure",
    "build_facts_bundle",
    "create_provider",
    "explain",
    "get_limiter",
    "reset_limiter",
    "suggest_classification",
    "validate_classification_output",
    "validate_model_output",
]
