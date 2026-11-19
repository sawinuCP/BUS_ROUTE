# ADR-0005 — Docker-first local development environment with pinned Python 3.12

**Date:** 2026-11-19
**Status:** Accepted
**Deciders:** Coding agent; ratified by the product owner's approval to proceed with Phase 0.3 (baseline ADR-0002 requires Python 3.12+)
**Phase/task context:** Phase 0.3 (audit finding GAP-007: host default `python` is 3.11.9; `py` launcher offers 3.14.2; no 3.12/3.13 interpreter is installed)

## 1. Context

ADR-0002 pins the backend to Python 3.12+. The development machine has only Python 3.11.9 (default `python`) and 3.14.2 (`py`). Installing a new interpreter on the host would modify machine state outside the repository, and 3.14 is a very new release for the pinned backend dependency set. The Phase 0 exit criteria require a reproducible fresh-clone setup ("fresh clone can follow documented setup without undocumented manual steps") and a running backend skeleton.

## 2. Decision

1. **Docker-first development:** the backend runs inside Docker Compose on the pinned `python:3.12-slim` image (`backend/Dockerfile`). The Compose stack (`infra/docker/compose.yaml`) provides PostgreSQL/PostGIS (`postgis/postgis:16-3.4`), Redis (`redis:7-alpine`) and the backend with hot reload via bind mount.
2. **Version enforcement:** the image tag pins Python 3.12; tooling configuration targets `py312` (Ruff `target-version`, mypy `python_version = "3.12"`). A host-venv path remains documented for machines that have Python 3.12, but Docker is the canonical, tested path.
3. **Single configuration source:** environment configuration lives in the repo-root `.env` (created from `.env.example`, gitignored). Compose injects service-name-based overrides (`db`, `redis`) for `DATABASE_URL`/`REDIS_URL` inside the network, so the same settings file serves host and container usage.

## 3. Options considered

| Option | Summary | Consequences |
|---|---|---|
| **Docker-first with pinned image (chosen)** | Reproducible; no host Python install needed | Image build time; bind-mount reload performance on Windows |
| Install Python 3.12 on the host | Native venv speed | Modifies machine state; divergence risk between machines; contradicts "no undocumented manual steps" |
| Use host Python 3.14 | Zero setup | Depends on the newest CPython for the pinned backend dependency set; deviates from the documented 3.12 pin |

## 4. Rationale

The architecture package's own delivery baseline is "Docker, CI pipeline, environment-based config" for "reproducible local, test, staging and production environments". Docker-first delivers reproducibility immediately and keeps the developer machine untouched.

## 5. Consequences

- Positive: one-command local stack (`docker compose --env-file .env -f infra/docker/compose.yaml up -d --build`); tests/lint/migrations run in the same environment CI will use.
- Negative: container rebuilds are required when `requirements*.txt` change; Windows bind-mount file watching can be slower for `--reload`.
- Migration impact: none; a host 3.12 venv remains compatible because configuration is environment-driven.

## 6. Related documents

`docs/adr/ADR-0002` (Python 3.12+ pin), `docs/architecture/07_TECH_STACK.md` (delivery), `docs/product/11_IMPLEMENTATION_PLAN.md` Phase 0 exit tests, `docs/audits/phase-0-repository-audit.md` §10 (GAP-007).

## 7. Reversal conditions

If container-based development proves impractical for the team (e.g., volume performance or image-update friction), install Python 3.12 on development machines and supersede this ADR; the Docker stack remains the CI/staging baseline regardless.
