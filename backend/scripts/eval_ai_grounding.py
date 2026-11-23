"""Live grounding evaluation (Phase 8 item 9, manual run).

Replays a fixed subset of the evaluation scenarios against the **configured
provider** (from the environment: `AI_PROVIDER`/`AI_BASE_URL`/`AI_MODEL`),
validates every completion with the same validators the endpoints use, and
writes a human-reviewable Markdown report (grounding outcomes + latency) to
`backend/data/validation_reports/ai-grounding-<timestamp>.md`.

Run manually from `backend/`:

    python scripts/eval_ai_grounding.py

This is the live half of the fixed evaluation set (`tests/evaluation/` runs
the same validators offline on every gate). No report is auto-published and
no dataset changes — the output is evidence for the status report only.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules.ai_assistance import (  # noqa: E402
    create_provider,
    validate_classification_output,
    validate_model_output,
)
from app.modules.reports import REPORT_CATEGORIES  # noqa: E402
from app.modules.ai_assistance.prompts import (  # noqa: E402
    CLASSIFICATION_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_classification_user_message,
    build_user_message,
)
from app.modules.ai_assistance.providers import (  # noqa: E402
    ProviderConfigError,
    ProviderError,
)
from app.modules.ai_assistance.validation import ValidationFailure  # noqa: E402
from app.platform.config import get_settings  # noqa: E402
from tests.evaluation.cases import (  # noqa: E402
    CLASSIFICATION_REPORTS,
    EVALUATION_CASES,
    SCENARIOS,
)

LIVE_SUBSET_IDS: tuple[str, ...] = (
    "explain-g001",
    "explain-h001-route",
    "explain-h002-fare",
    "explain-o001-generic",
    "explain-i001-obedient",
    "classify-g001",
    "classify-h001-unknown-category",
)


async def main() -> int:
    settings = get_settings()
    lines: list[str] = [
        "# Live AI grounding evaluation (Phase 8 item 9)",
        "",
        f"- Run: {datetime.now(UTC).isoformat()}",
        f"- Provider: `{settings.ai_provider}` · Model: `{settings.ai_model}`"
        " · base URL from environment (key never printed)",
        "- Validators: the exact `validate_model_output` /"
        " `validate_classification_output` used by the endpoints.",
        "- Fixed live subset; the full offline set runs in CI"
        " (`tests/evaluation/`).",
        "",
        "| Case | Expected | Outcome | Latency (s) |",
        "|---|---|---|---|",
    ]
    latencies: list[float] = []
    failures = 0
    accepted = 0
    rejected = 0

    try:
        provider = create_provider(settings)
    except ProviderConfigError as exc:
        print(f"LIVE EVAL NOT POSSIBLE: {exc}", file=sys.stderr)
        return 2
    print(f"evaluating with provider={provider.name} model={provider.model}")

    cases_by_id = {case.case_id: case for case in EVALUATION_CASES}

    async def run_one(
        case_id: str,
        kind: str,
        system: str,
        user: str,
        expect: str,
        bundle: Any = None,
    ) -> str:
        """Live outcome rules (item 9):
        - benign cases (expect=accept): validation MUST pass — a rejection is
          an over-strict-validator failure (a real, reportable problem);
        - trap cases (expect=reject): both good outcomes are recorded — the
          validator rejecting the trap, or the model avoiding it entirely;
        - provider errors are recorded, never counted as grounding failures.
        """
        nonlocal accepted, rejected, failures
        start = time.monotonic()
        try:
            completion = await provider.complete(system, user)
        except ProviderError as exc:
            latency = time.monotonic() - start
            latencies.append(latency)
            lines.append(f"| {case_id} | {expect} | provider error (`{exc}`) | {latency:.2f} |")
            return "provider-error"
        latency = time.monotonic() - start
        latencies.append(latency)
        try:
            if kind == "explanation":
                assert bundle is not None
                validate_model_output(
                    completion.text, bundle, require_entity_mention=True
                )
            else:
                validate_classification_output(
                    completion.text, list(REPORT_CATEGORIES)
                )
        except ValidationFailure as exc:
            if expect == "reject":
                rejected += 1
                lines.append(
                    f"| {case_id} | reject | REJECTED as designed (`{exc}`) | {latency:.2f} |"
                )
                return "reject-ok"
            failures += 1
            lines.append(
                f"| {case_id} | accept | FAILED validation (`{exc}`) | {latency:.2f} |"
            )
            return "accept-failed"
        if expect == "accept":
            accepted += 1
            lines.append(f"| {case_id} | accept | PASSED validation | {latency:.2f} |")
            return "accept-ok"
        lines.append(
            f"| {case_id} | reject | model avoided the trap (grounded answer"
            f" accepted) | {latency:.2f} |"
        )
        return "reject-avoided"

    for case_id in LIVE_SUBSET_IDS:
        case = cases_by_id[case_id]
        if case.kind == "explanation":
            bundle = SCENARIOS[case.scenario]()
            outcome = await run_one(
                case.case_id,
                case.kind,
                SYSTEM_PROMPT,
                build_user_message(bundle, "explain_step"),
                case.expected,
                bundle=bundle,
            )
        else:
            report = CLASSIFICATION_REPORTS["injection_stop_report"]
            outcome = await run_one(
                case.case_id,
                case.kind,
                CLASSIFICATION_SYSTEM_PROMPT,
                build_classification_user_message(list(REPORT_CATEGORIES), report),
                case.expected,
            )
        print(f"  {case_id}: {outcome}")

    if latencies:
        lines += [
            "",
            f"- Cases: {len(LIVE_SUBSET_IDS)} · grounded answers accepted:"
            f" {accepted} · traps rejected as designed: {rejected} ·"
            f" **failures: {failures}**",
            f"- Latency: min {min(latencies):.2f}s · median"
            f" {sorted(latencies)[len(latencies) // 2]:.2f}s · max"
            f" {max(latencies):.2f}s",
            "- Translation/latency beyond this subset: deferred with D-7"
            " (English-only today).",
            "",
        ]
    else:
        lines += ["", "- No provider calls completed."]

    out_dir = Path("data/validation_reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"ai-grounding-{stamp}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"report written: {path}")
    print(json.dumps({"accepted": accepted, "rejected": rejected, "failures": failures}))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
