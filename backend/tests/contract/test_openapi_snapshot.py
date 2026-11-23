"""Contract tests: the OpenAPI surface stays consciously versioned.

The path inventory is frozen — adding or removing an endpoint must update
`EXPECTED_PATHS` in the same change, keeping the mobile client and the docs
honest about the contract (implementation plan §4.2; API design doc).
"""

from __future__ import annotations

from app.main import app

EXPECTED_PATHS: set[tuple[str, str]] = {
    ("api/v1/health", "GET"),
    ("api/v1/ready", "GET"),
    # places/search/stops
    ("api/v1/places/search", "GET"),
    ("api/v1/places/reverse-geocode", "POST"),
    ("api/v1/stops", "GET"),
    ("api/v1/walking/route", "GET"),
    # planning + saved journeys
    ("api/v1/journeys/plan", "POST"),
    ("api/v1/journeys/{journey_id}", "GET"),
    ("api/v1/journeys/{journey_id}", "DELETE"),
    ("api/v1/journeys/{journey_id}/refresh", "POST"),
    # active journey sessions
    ("api/v1/journey-sessions", "POST"),
    ("api/v1/journey-sessions/{session_id}", "GET"),
    ("api/v1/journey-sessions/{session_id}/events", "POST"),
    ("api/v1/journey-sessions/{session_id}/replan", "POST"),
    # reports + grounded AI
    ("api/v1/reports", "POST"),
    ("api/v1/ai/explain-step", "POST"),
    ("api/v1/ai/why-route", "POST"),
    # ops (Phase 9 item 5)
    ("api/v1/metrics", "GET"),
    ("api/v1/ops/dashboard", "GET"),
    # admin (mounted only outside production; auth per Phase 9)
    ("api/v1/admin/sources", "GET"),
    ("api/v1/admin/sources", "POST"),
    ("api/v1/admin/sources/{source_id}/sync", "POST"),
    ("api/v1/admin/sync-runs/{run_id}", "GET"),
    ("api/v1/admin/dataset-versions", "GET"),
    ("api/v1/admin/dataset-versions/active", "GET"),
    ("api/v1/admin/dataset-versions/{version_id}/publish", "POST"),
    ("api/v1/admin/dataset-versions/{version_id}/rollback", "POST"),
    ("api/v1/admin/dataset-versions/{version_id}/quality-report", "GET"),
    ("api/v1/admin/dataset-versions/{version_id}/quality-report/write", "POST"),
    ("api/v1/admin/coverage-scorecard", "GET"),
    ("api/v1/admin/qa-queue", "GET"),
    ("api/v1/admin/verifications", "GET"),
    ("api/v1/admin/verifications", "POST"),
    ("api/v1/admin/reports", "GET"),
    ("api/v1/admin/reports/{report_id}/review", "POST"),
    ("api/v1/admin/reports/{report_id}/classification-suggestion", "GET"),
}


def _actual_paths() -> set[tuple[str, str]]:
    schema = app.openapi()
    actual: set[tuple[str, str]] = set()
    for path, operations in schema["paths"].items():
        clean = path.lstrip("/")
        for method in operations:
            if method in {"get", "post", "put", "patch", "delete"}:
                actual.add((clean, method.upper()))
    return actual


def test_openapi_path_inventory_matches_the_contract() -> None:
    actual = _actual_paths()
    missing = EXPECTED_PATHS - actual
    unexpected = actual - EXPECTED_PATHS
    assert not missing, f"contract paths missing from the API: {sorted(missing)}"
    assert not unexpected, (
        "new/renamed API endpoints must be added to EXPECTED_PATHS"
        f" (tests/contract) and the API design doc: {sorted(unexpected)}"
    )


def test_openapi_documents_stable_metadata_and_error_responses() -> None:
    schema = app.openapi()
    assert schema["info"]["title"] == "Sri Lanka Journey Planner API"
    documented_errors = {
        (path, status)
        for path, operations in schema["paths"].items()
        for status in operations.get("post", {}).get("responses", {})
        if status.startswith(("4", "5"))
    }
    # Mutating endpoints document their failure modes (stable envelope codes).
    assert documented_errors, "mutating endpoints must document error responses"
