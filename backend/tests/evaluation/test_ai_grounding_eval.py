"""Fixed-set evaluation of grounded AI validation (Phase 8 item 9).

Runs every case from `cases.py` **offline** — no network, no provider — so
the grounding/hallucination/omission/injection contract is enforced on every
test run. This is the CI half of the evaluation; the live half (real model
calls + latency) is `backend/scripts/eval_ai_grounding.py`, run manually.
"""

from __future__ import annotations

import pytest

from app.modules.ai_assistance import (
    validate_classification_output,
    validate_model_output,
)
from app.modules.ai_assistance.validation import ValidationFailure
from app.modules.reports import REPORT_CATEGORIES
from tests.evaluation.cases import EVALUATION_CASES, EvaluationCase

_PASS_COUNT = sum(1 for case in EVALUATION_CASES if case.expected == "accept")
_REJECT_COUNT = len(EVALUATION_CASES) - _PASS_COUNT


def test_evaluation_set_is_nontrivial() -> None:
    """The fixed set exists and covers the four evaluation dimensions."""
    assert len(EVALUATION_CASES) >= 15
    assert _PASS_COUNT >= 3 and _REJECT_COUNT >= 10
    tags = {tag for case in EVALUATION_CASES for tag in case.tags}
    # Item 9 dimensions covered by the fixed set (translation is D-7-gated).
    assert {"grounded", "hallucination", "omission", "injection", "malformed"} <= tags
    kinds = {case.kind for case in EVALUATION_CASES}
    assert kinds == {"explanation", "classification"}
    ids = [case.case_id for case in EVALUATION_CASES]
    assert len(ids) == len(set(ids)), "case IDs must be unique"


def _run_case(case: EvaluationCase) -> None:
    if case.kind == "explanation":
        from tests.evaluation.cases import SCENARIOS

        bundle = SCENARIOS[case.scenario]()
        if case.expected == "accept":
            result = validate_model_output(
                case.model_output, bundle, require_entity_mention=case.require_entity
            )
            assert result.explanation
            return
        with pytest.raises(ValidationFailure) as excinfo:
            validate_model_output(
                case.model_output, bundle, require_entity_mention=case.require_entity
            )
        if case.reason_contains:
            assert case.reason_contains in str(excinfo.value), str(excinfo.value)
        return

    # classification
    if case.expected == "accept":
        result = validate_classification_output(case.model_output, REPORT_CATEGORIES)
        assert result.suggested_category in REPORT_CATEGORIES
        assert 10 <= len(result.rationale) <= 600
        return
    with pytest.raises(ValidationFailure) as excinfo:
        validate_classification_output(case.model_output, REPORT_CATEGORIES)
    if case.reason_contains:
        assert case.reason_contains in str(excinfo.value), str(excinfo.value)


@pytest.mark.parametrize("case", EVALUATION_CASES, ids=[case.case_id for case in EVALUATION_CASES])
def test_grounding_case(case: EvaluationCase) -> None:
    _run_case(case)
