"""Immutable raw-snapshot archiving (ADR-0007).

Snapshots are content-addressed by sha256 and stored verbatim. The interface
exists so local-disk development can move to S3-compatible object storage in
staging/production without touching ingestion logic (plan §3.1 "Raw source
archive: S3-compatible object storage or equivalent").
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path

from app.modules.data_ingestion.adapters.base import FetchResult


def sha256_hex(content: bytes) -> str:
    """Lowercase hex sha256 — the snapshot identity/fingerprint."""
    return hashlib.sha256(content).hexdigest()


class SnapshotArchive(ABC):
    """Stores and retrieves immutable raw snapshots."""

    @abstractmethod
    def store(self, source_name: str, checksum: str, result: FetchResult) -> str:
        """Persist the payload and return its storage URI."""

    @abstractmethod
    def exists(self, source_name: str, checksum: str) -> bool:
        """Whether this exact payload is already archived for the source."""


class LocalFilesystemArchive(SnapshotArchive):
    """Development archive: `data/raw/<safe_source>/<checksum>.<ext>`."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)

    def _path_for(self, source_name: str, checksum: str, result: FetchResult) -> Path:
        safe_source = "".join(c if c.isalnum() or c in "-_" else "_" for c in source_name)
        extension = _extension_for(result.content_type)
        return self._root / safe_source / f"{checksum}{extension}"

    def store(self, source_name: str, checksum: str, result: FetchResult) -> str:
        path = self._path_for(source_name, checksum, result)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(result.content)
        return str(path)

    def exists(self, source_name: str, checksum: str) -> bool:
        return any(
            p.stem == checksum for p in (self._root / _safe(source_name)).glob(f"{checksum}*")
        )


def _safe(source_name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in source_name)


def _extension_for(content_type: str | None) -> str:
    if content_type and "json" in content_type:
        return ".json"
    if content_type and "xml" in content_type:
        return ".xml"
    if content_type and "zip" in content_type:
        return ".zip"
    return ".bin"
