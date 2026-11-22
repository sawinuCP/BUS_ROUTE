"""Deterministic multimodal journey planner (canonical module: `planner`).

Phase 4 core: builds an immutable network snapshot from the canonical tables
(`network`), generates direct and multi-leg candidates over exact patterns and
explicit transfers (`service`), and models itineraries with conservative
estimates, Pareto filtering and ranking labels (`itinerary`).

Grounding rules carried into every result:
- rides are tied to a pattern and an ordered sequence span (board before alight);
- transfers need an explicit stored connector or a same-stop re-board;
- walk legs exist only when the walking engine routed them;
- in-vehicle time is a labelled conservative estimate, never a timetable claim;
- every option carries the network version label and honest warnings.
"""

from __future__ import annotations

from app.modules.planner.itinerary import (
    ESTIMATE_BASIS_NOTE,
    STATIC_SERVICE_WARNING,
    Itinerary,
    RideLeg,
    WalkLeg,
    pareto_filter,
    rank_labels,
)
from app.modules.planner.network import TransitNetwork, load_network
from app.modules.planner.service import (
    PRIORITIES,
    PRIORITY_DEFAULT,
    Endpoint,
    JourneyPlanner,
    PlanningConstraints,
    PlanningResult,
)

__all__ = [
    "ESTIMATE_BASIS_NOTE",
    "PRIORITIES",
    "PRIORITY_DEFAULT",
    "STATIC_SERVICE_WARNING",
    "Endpoint",
    "Itinerary",
    "JourneyPlanner",
    "PlanningConstraints",
    "PlanningResult",
    "RideLeg",
    "TransitNetwork",
    "WalkLeg",
    "load_network",
    "pareto_filter",
    "rank_labels",
]
