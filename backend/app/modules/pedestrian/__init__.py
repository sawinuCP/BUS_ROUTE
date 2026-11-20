"""Pedestrian module (canonical boundary per ADR-0001).

Implemented from Phase 3: walking-router adapter (`router.py`) turning the
Valhalla PoC (evidence: `docs/evidence/valhalla-poc-2026-11-20.md`, ADR-0008)
into a vendor-agnostic `WalkPlan` contract for the deterministic planner.
"""

from __future__ import annotations

from app.modules.pedestrian.router import (
    ValhallaWalkingRouter,
    WalkingRouter,
    WalkPlan,
    WalkStep,
    get_walking_router,
    route_walk_between,
)

__all__ = [
    "WalkPlan",
    "WalkStep",
    "WalkingRouter",
    "ValhallaWalkingRouter",
    "get_walking_router",
    "route_walk_between",
]
