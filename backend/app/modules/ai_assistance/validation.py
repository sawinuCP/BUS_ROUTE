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


def validate_model_output(raw: str, bundle: FactsBundle) -> ValidatedExplanation:
    """Validate one completion against the bundle; raise on any violation."""
    payload = _extract_json_object(raw)
    _check_schema(payload)
    cites = _check_cites(payload, bundle)
    explanation = payload["explanation"].strip()
    _check_forbidden_content(explanation, bundle)
    return ValidatedExplanation(explanation=explanation, cites=cites)
