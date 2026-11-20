"""Transfers module (canonical boundary per ADR-0001).

Implemented from Phase 3: candidate transfer-connector generation
(`service.py`) — proximity *proposals* routed through the walking engine
(ADR-0008) into honest, unverified `transfer_connections` rows that only the
moderation/publish flow can promote.
"""

from app.modules.transfers.service import (
    DERIVED_SOURCE_NAME,
    CandidateOutcome,
    CandidatePair,
    generate_transfer_candidates,
    get_or_create_derived_source,
    propose_candidate_pairs,
)

__all__ = [
    "CandidateOutcome",
    "CandidatePair",
    "DERIVED_SOURCE_NAME",
    "generate_transfer_candidates",
    "get_or_create_derived_source",
    "propose_candidate_pairs",
]
