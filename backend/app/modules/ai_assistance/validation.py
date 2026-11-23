"""Response validation (Phase 8 item 6: schema + allowed-facts checks).

Every provider completion is validated before it reaches the traveller:

1. strict-JSON schema (`explanation` + `cites`);
2. every cited fact ID must exist in the bundle;
3. forbidden-content scan: fares/prices, clock times, service frequencies
   and route codes not present in the supplied facts are rejected — the
   model cannot add a route number, fare or service time (verification test);
4. anything invalid → `ValidationFailure` → deterministic fallback (item 7).
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.modules.ai_assistance.facts import FactsBundle

_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["explanation", "cites"],
    "additionalProperties": False,
    "properties": {
        "explanation": {"type": "string", "minLength": 10, "maxLength": 1200},
        "cites": {
            "type": "array",
            "maxItems": 10,
            "items": {"type": "string", "minLength": 1, "maxLength": 32},
        },
    },
}


class ValidationFailure(ValueError):
    """The model's output violated the grounding contract."""


@dataclass(frozen=True)
class ValidatedExplanation:
    explanation: str
    cites: tuple[str, ...]


_ROUTE_MENTION = re.compile(r"\broute\s+#?([A-Za-z0-9][A-Za-z0-9\-/]{0,11})\b", re.IGNORECASE)
_CURRENCY = re.compile(r"\b(?:rs\.?|lkr|slr|rupee?s?|cents?)\b", re.IGNORECASE)
_CLOCK_TIME = re.compile(r"\b\d{1,2}[:.]\d{2}\s*(?:am|pm|hrs?)?\b", re.IGNORECASE)
_FREQUENCY = re.compile(r"\b(?:every|each)\s+\d+\s*(?:min(?:ute)?s?|hours?)\b", re.IGNORECASE)


def _extract_json_object(raw: str) -> dict[str, Any]:
    """Pull the first JSON object out of the completion (fences tolerated)."""
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end <= start:
        raise ValidationFailure("no JSON object in the model output")
    try:
        parsed = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValidationFailure("model output is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValidationFailure("model output is not a JSON object")
    return parsed


def _check_schema(payload: dict[str, Any]) -> None:
    explanation = payload.get("explanation")
    cites = payload.get("cites")
    if not isinstance(explanation, str) or not 10 <= len(explanation.strip()) <= 1200:
        raise ValidationFailure("explanation missing or outside 10-1200 characters")
    if not isinstance(cites, list) or not all(isinstance(c, str) for c in cites):
        raise ValidationFailure("cites missing or not a list of fact IDs")
    if len(cites) > 10:
        raise ValidationFailure("too many citations")
    unexpected = set(payload) - {"explanation", "cites"}
    if unexpected:
        raise ValidationFailure(f"unexpected fields in the output: {sorted(unexpected)}")


def _check_cites(payload: dict[str, Any], bundle: FactsBundle) -> tuple[str, ...]:
    allowed = set(bundle.fact_ids)
    unknown = [c for c in payload["cites"] if c not in allowed]
    if unknown:
        raise ValidationFailure(f"citation of unknown fact ID(s): {unknown}")
    return tuple(dict.fromkeys(payload["cites"]))


def _check_forbidden_content(explanation: str, bundle: FactsBundle) -> None:
    if _CURRENCY.search(explanation):
        raise ValidationFailure("explanation claims a fare/price not present in the facts")
    if _CLOCK_TIME.search(explanation):
        raise ValidationFailure("explanation claims a clock time not present in the facts")
    if _FREQUENCY.search(explanation):
        raise ValidationFailure("explanation claims a service frequency not present in the facts")
    for match in _ROUTE_MENTION.finditer(explanation):
        code = match.group(1).strip().rstrip(".,;:")
        if code and code not in bundle.allowed_route_codes:
            raise ValidationFailure(f"explanation mentions route '{code}' absent from the facts")


def _check_entity_mention(explanation: str, bundle: FactsBundle) -> None:
    """Omission guard: an explanation must engage with the facts it explains.

    When the bundle contains route codes or stop names, the explanation must
    mention at least one of them — a purely generic answer ("this is a step
    in your journey") is treated as an omission and falls back.
    """
    if not (bundle.allowed_route_codes or bundle.allowed_stop_names):
        return
    lowered = explanation.lower()
    for code in bundle.allowed_route_codes:
        if re.search(rf"\b{re.escape(code.lower())}\b", lowered):
            return
    for name in bundle.allowed_stop_names:
        if name.lower() in lowered:
            return
    raise ValidationFailure("explanation is too generic: it names no route or stop from the facts")


def validate_model_output(
    raw: str, bundle: FactsBundle, *, require_entity_mention: bool = False
) -> ValidatedExplanation:
    """Validate one completion against the bundle; raise on any violation.

    `require_entity_mention` turns on the omission guard (used for
    explain-step responses when the bundle contains route/stop entities).
    """
    payload = _extract_json_object(raw)
    _check_schema(payload)
    cites = _check_cites(payload, bundle)
    explanation = payload["explanation"].strip()
    _check_forbidden_content(explanation, bundle)
    if require_entity_mention:
        _check_entity_mention(explanation, bundle)
    return ValidatedExplanation(explanation=explanation, cites=cites)


# --------------------------------------------------------------------------- #
# Report classification (item 5)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ValidatedClassification:
    suggested_category: str
    rationale: str


def validate_classification_output(
    raw: str, allowed_categories: Sequence[str]
) -> ValidatedClassification:
    """Validate one classification completion (item 6 contract).

    Strict JSON with exactly `suggested_category` (one of the allowed
    categories) and `rationale` (10–600 chars); the rationale must not
    contain fares/prices, clock times or service frequencies.
    """
    payload = _extract_json_object(raw)
    unexpected = set(payload) - {"suggested_category", "rationale"}
    if unexpected:
        raise ValidationFailure(f"unexpected fields in the output: {sorted(unexpected)}")
    category = payload.get("suggested_category")
    rationale = payload.get("rationale")
    if not isinstance(category, str) or category not in allowed_categories:
        raise ValidationFailure("suggested_category is missing or not an allowed category")
    if not isinstance(rationale, str) or not 10 <= len(rationale.strip()) <= 600:
        raise ValidationFailure("rationale missing or outside 10-600 characters")
    rationale = rationale.strip()
    if _CURRENCY.search(rationale):
        raise ValidationFailure("rationale claims a fare/price")
    if _CLOCK_TIME.search(rationale):
        raise ValidationFailure("rationale claims a clock time")
    if _FREQUENCY.search(rationale):
        raise ValidationFailure("rationale claims a service frequency")
    return ValidatedClassification(suggested_category=category, rationale=rationale)
