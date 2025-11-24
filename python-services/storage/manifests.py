"""Stub for artifact manifests and embedding storage."""

from typing import Any, Dict


def persist_manifest(payload: Dict[str, Any]) -> None:
    raise NotImplementedError("Write manifest to disk/DB with checksum + policy tags.")
