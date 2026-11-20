"""Source-adapter framework (canonical module: `data_ingestion`).

An adapter encapsulates everything source-specific: how to fetch a snapshot
and how to parse it into normalised, typed records. The ingestion framework
(`service.py`) is source-agnostic: it archives, validates, upserts and records
diffs. Adding a new transport source in Phase 1.3 means implementing this
interface — never modifying the framework.

Domain rule (implementation plan §5.2): adapters are idempotent — re-running
the same source version must not create duplicate canonical records.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RawRecord:
    """One normalised record parsed from a source snapshot.

    `payload` is a plain dict whose shape is agreed between the adapter and the
    entity upsert handler registered for `entity_hint` (see `service.py`).
    """

    external_id: str
    entity_hint: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FetchResult:
    """Raw snapshot bytes plus non-sensitive fetch metadata."""

    content: bytes
    content_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SourceAdapter(ABC):
    """Contract for one transport data source."""

    @property
    @abstractmethod
    def adapter_version(self) -> str:
        """Bumped whenever parsing behaviour changes (recorded on sync runs)."""

    @abstractmethod
    def fetch(self) -> FetchResult:
        """Retrieve the current snapshot payload (raw, untrusted)."""

    @abstractmethod
    def parse(self, content: bytes, metadata: dict[str, Any]) -> list[RawRecord]:
        """Parse raw snapshot content into normalised records (pure function)."""
