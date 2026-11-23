"""Facts bundle builder (Phase 8 item 2: only selected itinerary facts).

Everything the model may see comes from here. Rules:

- **Coordinates are stripped** (privacy filter, item 8): `target_lat/lon`,
  `stop_lat/lon` and any origin/destination coordinates never reach the
  provider. Stop/route *names* stay (they are needed to explain the plan)
  but no precise location is sent.
- Each fact gets a stable ID (`f_summary`, `s3`, …); the model must cite
  only those IDs and `validation.py` rejects anything else.
- The bundle is self-contained JSON — no database, no tools, no free-form
  access (architecture doc 12 tool boundary).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Facts that encode precise location or device context — never sent.
_COORDINATE_FACT_KEYS = frozenset(
    {"target_lat", "target_lon", "stop_lat", "stop_lon", "lat", "lon", "latitude", "longitude"}
)


def _strip_coordinates(facts: dict[str, Any]) -> dict[str, Any]:
    """Remove coordinate/PII facts (privacy filter, item 8)."""
    return {key: value for key, value in facts.items() if key not in _COORDINATE_FACT_KEYS}


@dataclass(frozen=True)
class FactsBundle:
    """The complete, self-contained fact set the provider may see."""

    fact_ids: tuple[str, ...]
    facts: dict[str, dict[str, Any]]
    # Entities the explanation may name; validation rejects anything else.
    allowed_route_codes: frozenset[str] = field(default_factory=frozenset)
    allowed_stop_names: frozenset[str] = field(default_factory=frozenset)
    dataset_version: str | None = None


def _compact_step(step: dict[str, Any], index: int) -> dict[str, Any]:
    """One step's explainable content, coordinates removed."""
    return {
        "index": index,
        "action": step.get("action"),
        "text": step.get("text"),
        "confidence": step.get("confidence"),
        "details": _strip_coordinates(step.get("facts") or {}),
    }


def _collect_entities(option: dict[str, Any]) -> tuple[frozenset[str], frozenset[str]]:
    """Route codes and stop names present in the selected option (facts only)."""
    route_codes: set[str] = set()
    stop_names: set[str] = set()
    for label in option.get("labels") or []:
        text = str(label)
        if text.strip():
            route_codes.add(text.strip())
    for leg in option.get("legs") or []:
        for key in ("route_code", "pattern_code"):
            if leg.get(key):
                route_codes.add(str(leg[key]))
        for key in ("board_stop_name", "alight_stop_name"):
            if leg.get(key):
                stop_names.add(str(leg[key]))
    for step in option.get("steps") or []:
        details = step.get("facts") or {}
        for key in ("route_code", "variant", "headsign"):
            value = details.get(key)
            if value and str(value) != "not confirmed":
                route_codes.add(str(value))
        for key in ("stop_name", "alight_stop_name", "to_stop_name", "next_boarding_point"):
            value = details.get(key)
            if value and str(value) != "not confirmed":
                stop_names.add(str(value))
    return frozenset(route_codes), frozenset(stop_names)


def build_facts_bundle(
    payload: dict[str, Any], option_index: int, step_index: int | None
) -> FactsBundle:
    """Build the fact set for explaining `options[option_index]`.

    `step_index` selects "explain this step" (the step plus journey context);
    `None` means "why this route?" (summary plus the whole step list).
    """
    options = payload.get("options") or []
    if option_index < 0 or option_index >= len(options):
        raise ValueError(f"option_index {option_index} is outside 0..{len(options) - 1}")
    option = options[option_index]

    route_codes, stop_names = _collect_entities(option)
    summary = {
        "estimated_duration_minutes": (option.get("summary") or {}).get(
            "estimated_duration_minutes"
        ),
        "walking_distance_m": (option.get("summary") or {}).get("walking_distance_m"),
        "transfer_count": (option.get("summary") or {}).get("transfer_count"),
        "confidence": (option.get("summary") or {}).get("confidence"),
    }
    context = {
        "dataset_version": payload.get("dataset_version"),
        "availability_scope": payload.get("availability_scope"),
        "labels": option.get("labels") or [],
        "warnings": option.get("warnings") or [],
        "notes": [
            note for note in payload.get("notes") or [] if isinstance(note, str) and note.strip()
        ],
        "language": payload.get("language", "en"),
    }
    steps = [_compact_step(step, i) for i, step in enumerate(option.get("steps") or [])]

    facts: dict[str, dict[str, Any]] = {"f_summary": summary, "f_context": context}
    fact_ids: list[str] = ["f_summary", "f_context"]
    if step_index is None:
        facts["f_steps"] = {"steps": steps}
        fact_ids.append("f_steps")
    else:
        if step_index < 0 or step_index >= len(steps):
            raise ValueError(f"step_index {step_index} is outside 0..{len(steps) - 1}")
        facts["f_step"] = steps[step_index]
        fact_ids.append("f_step")
        others = [step for step in steps if step["index"] != step_index]
        facts["f_other_steps"] = {"steps": others}
        fact_ids.append("f_other_steps")

    return FactsBundle(
        fact_ids=tuple(fact_ids),
        facts=facts,
        allowed_route_codes=route_codes,
        allowed_stop_names=stop_names,
        dataset_version=payload.get("dataset_version"),
    )
